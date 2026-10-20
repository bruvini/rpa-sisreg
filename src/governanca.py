"""Rastreabilidade *administrativa*, sem dados de pacientes e sem credenciais.

Só registra eventos enumerados e contagens inteiras. Nunca registra exceções,
identificadores clínicos, páginas, cookies, CPF, CNS nem valores livres.
"""
from __future__ import annotations
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
import time
import uuid
from app_info import APP_VERSION

EVENTOS = frozenset({'INICIO', 'PREPARO_OK', 'PREPARO_ERRO', 'CADASTRO_OK',
                     'CADASTRO_PENDENCIA', 'HOSPITAL_OK', 'HOSPITAL_PENDENCIA',
                     'ERRO_TECNICO', 'FALHA_SALVAMENTO', 'INTERRUPCAO', 'FIM'})
ETAPAS = frozenset({'preparo', 'cadastro', 'hospital', 'geral'})


def agora() -> str:
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def sha256_arquivo(caminho: Path) -> str:
    digest = hashlib.sha256()
    with Path(caminho).open('rb') as arquivo:
        for trecho in iter(lambda: arquivo.read(1024 * 1024), b''):
            digest.update(trecho)
    return digest.hexdigest()


def pasta_local() -> Path:
    if os.name == 'nt':
        base = Path(os.environ.get('LOCALAPPDATA') or Path.home() / 'AppData' / 'Local')
    else:
        base = Path(os.environ.get('XDG_STATE_HOME') or Path.home() / '.local' / 'state')
    return base / 'RPA_SISREG'


def nome_fonte_seguro(caminho: Path) -> str:
    """Somente nome de arquivo; rejeita nomes com identificadores longos.

    O nome do arquivo pode carregar dado pessoal. No histórico, substituímos
    trechos semelhantes a CPF, CNS ou AIH; conteúdos não são capturados.
    """
    nome = Path(caminho).name
    nome = re.sub(r'(?<!\d)\d[\d.\- ]{9,18}\d(?!\d)', '[identificador]', nome)
    return nome[:120]


def limpeza_temporarios(caminho: Path, *, agora_epoch: float | None = None,
                        idade_minima_horas: int = 48) -> int:
    """Limpa só XLSX temporários do RPA antigos no diretório indicado.

    Nunca remove o arquivo original, um backup nem o XLSX de trabalho.
    A idade mínima evita interferência entre instâncias simultâneas.
    """
    pasta = Path(caminho)
    if not pasta.is_dir():
        return 0
    limite = (time.time() if agora_epoch is None else agora_epoch) - idade_minima_horas * 3600
    removidos = 0
    for arquivo in pasta.glob('.rpa_sisreg_*.xlsx'):
        try:
            if not arquivo.is_file() or arquivo.is_symlink() or arquivo.stat().st_mtime >= limite:
                continue
            arquivo.unlink()
            removidos += 1
        except (OSError, PermissionError):
            continue
    return removidos


class HistoricoExecucao:
    def __init__(self, pasta: Path | None = None, *, version: str = APP_VERSION):
        self.pasta = Path(pasta) if pasta is not None else pasta_local()
        self.versao = version
        self.id = uuid.uuid4().hex
        self.inicio = agora()
        self.inicio_monotonic = time.monotonic()
        self.termino = ''
        self.origens: list[dict[str, str]] = []
        self.contagens = {'registros': 0, 'preparados': 0, 'cns_identificados': 0,
                          'consultas_hospitalares': 0, 'sem_divergencia_identificada': 0,
                          'pendencias': 0, 'erros_tecnicos': 0}
        self.ultima_etapa = 'geral'
        self.situacao = 'EM_ANDAMENTO'
        self._preparar_pasta()
        self._limpar_snapshots_temporarios()
        self.evento('INICIO')
        self.salvar()

    def _preparar_pasta(self):
        self.pasta.mkdir(parents=True, exist_ok=True)
        if os.name != 'nt':
            try: os.chmod(self.pasta, 0o700)
            except OSError: pass

    def _limpar_snapshots_temporarios(self):
        limite = time.time() - 48 * 3600
        for arq in self.pasta.glob('.historico_*.tmp'):
            try:
                if arq.is_file() and not arq.is_symlink() and arq.stat().st_mtime < limite:
                    arq.unlink()
            except OSError:
                continue

    def fonte(self, caminho: Path, sha: str | None = None, tipo: str = 'xlsx'):
        if tipo not in ('xlsx', 'pdf'):
            raise ValueError('Tipo de origem inválido')
        arquivo = Path(caminho)
        self.origens = [v for v in self.origens if v['tipo'] != tipo]
        self.origens.append({'nome': nome_fonte_seguro(arquivo),
                             'sha256': sha or sha256_arquivo(arquivo), 'tipo': tipo})
        self.salvar()

    def atualizar(self, **totais: int):
        for chave, valor in totais.items():
            if chave not in self.contagens or type(valor) is not int or valor < 0:
                raise ValueError('Somente contagens administrativas não negativas são permitidas')
            self.contagens[chave] = valor
        self.salvar()

    def evento(self, nome: str, etapa: str = 'geral', indice: int | None = None):
        if nome not in EVENTOS or etapa not in ETAPAS:
            raise ValueError('Evento técnico não reconhecido')
        if indice is not None and (type(indice) is not int or indice < 1):
            raise ValueError('Índice de evento inválido')
        objeto = {'instante': agora(), 'execucao': self.id, 'evento': nome, 'etapa': etapa}
        if indice is not None: objeto['registro_ordinal'] = indice
        # SEM mensagens, paths, tracebacks ou conteúdo livre.
        caminho = self.pasta / 'eventos_seguros.jsonl'
        fd = os.open(caminho, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
        with os.fdopen(fd, 'a', encoding='utf-8') as arq:
            arq.write(json.dumps(objeto, ensure_ascii=False, sort_keys=True) + '\n')

    def payload(self):
        return {'execucao': self.id, 'versao': self.versao, 'iniciado_em_utc': self.inicio,
                'encerrado_em_utc': self.termino, 'situacao': self.situacao,
                'duracao_segundos': round(time.monotonic() - self.inicio_monotonic, 2),
                'fontes': list(self.origens), 'contagens': dict(self.contagens)}

    def salvar(self):
        """Snapshot atômico; permanece disponível em caso de encerramento abrupto."""
        caminho = self.pasta / f'execucao_{self.id}.json'
        fd, temporario = tempfile.mkstemp(prefix='.historico_', suffix='.tmp', dir=self.pasta)
        try:
            if os.name != 'nt': os.fchmod(fd, 0o600)
            with os.fdopen(fd, 'w', encoding='utf-8') as arq:
                json.dump(self.payload(), arq, indent=2, ensure_ascii=False)
                arq.flush()
                os.fsync(arq.fileno())
            os.replace(temporario, caminho)
            if os.name != 'nt': os.chmod(caminho, 0o600)
        finally:
            Path(temporario).unlink(missing_ok=True)

    def encerrar(self, situacao: str = 'CONCLUIDA'):
        if situacao not in ('CONCLUIDA', 'INTERROMPIDA', 'FALHA_TECNICA'):
            raise ValueError('Situação de execução inválida')
        if self.termino:
            return
        self.situacao = situacao
        self.termino = agora()
        self.evento('FIM')
        self.salvar()


def exportar_pendencias(sessao, destino: Path) -> int:
    """XLSX mínimo com localização pela aba/linha/AIH e motivo técnico.

    Não inclui CPF, CNS, nome, procedimento, login nem URL SISREG.
    """
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill
    from aih_extract import normalizar_aih
    ws_name = 'Pendências'
    wb = Workbook()
    ws = wb.active
    ws.title = ws_name
    ws.append(['Aba', 'Linha na planilha', 'AIH', 'Motivo técnico', 'Análise fiscal'])
    for cel in ws[1]:
        cel.font = Font(bold=True, color='FFFFFF')
        cel.fill = PatternFill('solid', fgColor='073B66')
    total = 0
    for r in sessao.registros:
        estado = str(r.situacao or '')
        # Estado de dados coletados não constitui atesto/decisão fiscal.
        sem_pendencia = estado in ('SOLICITACAO_HOSPITALAR_CONFERIDA', 'DADOS_COLETADOS_SEM_DIVERGENCIA')
        if sem_pendencia:
            continue
        chave = re.sub('[^A-Z0-9_]', '', estado.upper())[:90] or 'DADOS_INSUFICIENTES'
        ws.append([r.aba, r.linha, normalizar_aih(r.aih), chave, 'REVISÃO PENDENTE'])
        ws.cell(ws.max_row, 3).number_format = '@'
        total += 1
    ws.freeze_panes = 'A2'
    ws.auto_filter.ref = f'A1:E{ws.max_row}'
    for letra, largura in {'A':22,'B':19,'C':19,'D':49,'E':22}.items():
        ws.column_dimensions[letra].width = largura
    destino = Path(destino)
    if destino.exists():
        raise FileExistsError('Escolha um nome diferente para o relatório de pendências')
    wb.save(destino)
    wb.close()
    return total
