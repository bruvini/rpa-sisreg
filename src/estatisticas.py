"""Estatísticas agregadas e log técnico sanitizado, sem dados de pacientes.

O TXT usa uma lista fechada de campos; nunca recebe mensagens, nomes,
identificadores ou páginas extraídas do SISREG.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from datetime import timezone
import os
import platform
import sys
import tempfile
from app_info import APP_VERSION

MANUAL_SEGUNDOS = {'preparo': 15, 'cadastro': 10, 'hospital': 10}
ACOES_SEGURAS = frozenset({'INICIO_EXECUCAO', 'PDF_INDEXACAO', 'CPF_CRUZAMENTO',
    'SALVAMENTO_XLSX', 'LOGIN_SUBMETIDO', 'MENU_AUTENTICADO', 'SESSAO_ENCERRADA',
    'CADASTRO_CPF', 'BUSCA_HOSPITALAR', 'AIH_EXATA', 'LEITURA_FICHA',
    'FICHA_HOSPITALAR', 'FIM_EXECUCAO',
    'SESSAO_FORA_DOMINIO', 'SESSAO_HTTPS_OFICIAL', 'INTERRUPCAO'})
RESULTADOS_SEGUROS = frozenset({'INICIO', 'OK', 'PENDENCIA', 'TIMEOUT', 'ERRO',
    'BLOQUEADO', 'SEM_RESULTADO', 'INTERRUPCAO'})
CATEGORIAS_SEGURAS = frozenset({'NENHUM', 'TIMEOUT_SELETOR', 'TIMEOUT_NAVEGADOR',
    'SELETOR_NAO_ENCONTRADO', 'SESSAO_NAO_AUTORIZADA', 'IDENTIDADE_NAO_CONFIRMADA',
    'RESULTADO_AMBIGUO', 'FICHA_NAO_ABERTA', 'AIH_NAO_CONFIRMADA',
    'PROCEDIMENTO_DIVERGENTE', 'CAMPOS_FICHA_INCOMPLETOS', 'PLANILHA_BLOQUEADA',
    'PERSISTENCIA_FALHOU', 'FALHA_NAVEGACAO', 'ERRO_NAO_CLASSIFICADO',
    'CAPTURA_SEM_RESULTADO', 'INTERRUPCAO_SOLICITADA'})


def categoria_excecao(tipo: str) -> str:
    # Apenas tipo de exceção conhecido. NÃO inclui str(exception) nem traceback.
    return {'TimeoutError': 'TIMEOUT_NAVEGADOR', 'PlaywrightTimeout': 'TIMEOUT_NAVEGADOR',
            'NavegacaoInesperada': 'SELETOR_NAO_ENCONTRADO',
            'FormularioInesperado': 'SESSAO_NAO_AUTORIZADA',
            'AlteracaoExterna': 'PLANILHA_BLOQUEADA',
            'PermissionError': 'PLANILHA_BLOQUEADA'}.get(tipo, 'ERRO_NAO_CLASSIFICADO')


ROTULOS = {'preparo':'PDF e CPF', 'cadastro':'Cadastro e CNS', 'hospital':'Solicitação hospitalar'}


def duracao(segundos: float) -> str:
    t=max(0, int(round(segundos)))
    h,r=divmod(t,3600)
    m,s=divmod(r,60)
    return f'{h:02d}:{m:02d}:{s:02d}'


def percentual(parte: int, total: int) -> str:
    return f'{100*parte/total:.1f}%' if total else '—'


@dataclass
class ContadorEtapa:
    total: int = 0                 # registros do universo da etapa
    consultados: int = 0           # pesquisas tentadas (ou documentos tratados)
    encontrados: int = 0           # campo obtido / ficha encontrada
    pendencias: int = 0
    falhas_tecnicas: int = 0
    segundos: float = 0.0
    concluida: bool = False
    fases: dict[str, float] = field(default_factory=dict)

    @property
    def manual(self) -> int:
        # Etapa 1 estima localizar TODOS os registros; etapas 2/3 apenas
        # o universo de consultas elegíveis daquela etapa.
        return 0  # Use Estatisticas.total_manual, que considera apenas consultas tentadas.


class Estatisticas:
    def __init__(self):
        self.inicio = datetime.now().astimezone()
        self.inicio_monotonic: float | None = None
        self.termino: datetime | None = None
        self.total_segundos: float = 0.0
        self.etapas = {nome: ContadorEtapa() for nome in MANUAL_SEGUNDOS}
        self.situacao = 'EM_ANDAMENTO'
        self.relatorio = ''
        self.diagnosticos: list[dict] = []

    def diagnosticar(self, acao: str, resultado: str, *, ordinal: int | None = None,
                    segundos: float | None = None, categoria: str = 'NENHUM') -> None:
        # Não aceitar texto livre fornecido por DOM, campos do hospital ou exceções.
        if acao not in ACOES_SEGURAS or resultado not in RESULTADOS_SEGUROS:
            raise ValueError('Operação diagnóstica desconhecida')
        if categoria not in CATEGORIAS_SEGURAS:
            categoria = 'ERRO_NAO_CLASSIFICADO'
        if ordinal is not None and (type(ordinal) is not int or not 1 <= ordinal <= 10000000):
            raise ValueError('Índice ordinal inválido')
        if segundos is not None and not 0 <= float(segundos) <= 86400:
            raise ValueError('Tempo inválido')
        self.diagnosticos.append({
            'utc': datetime.now(timezone.utc).isoformat(timespec='milliseconds'),
            'acao': acao, 'resultado': resultado, 'ordinal': ordinal,
            'segundos': round(float(segundos), 3) if segundos is not None else None,
            'categoria': categoria,
        })

    def registrar_total(self, chave, total):
        if chave not in self.etapas or not isinstance(total,int) or total < 0:
            raise ValueError('Etapa ou quantidade inválida')
        self.etapas[chave].total = total

    def concluir(self, chave, segundos, *, consultados, encontrados, pendencias=0, falhas=0, fases=None, completa=True):
        e=self.etapas[chave]
        e.segundos=max(0.0,float(segundos))
        e.consultados=int(consultados)
        e.encontrados=int(encontrados)
        e.pendencias=int(pendencias)
        e.falhas_tecnicas=int(falhas)
        e.fases=dict(fases or {})
        e.concluida=bool(completa)

    def encerrar(self, *, segundos: float, situacao: str):
        if situacao not in ('CONCLUIDA','PARCIAL','INTERROMPIDA'):
            raise ValueError('Situação inválida')
        self.termino = datetime.now().astimezone()
        self.total_segundos=max(0.0,segundos)
        self.situacao=situacao

    def total_manual(self):
        return sum((e.total if k=='preparo' else e.consultados)*MANUAL_SEGUNDOS[k] for k,e in self.etapas.items())

    def comparativo(self, chave):
        e=self.etapas[chave]
        manual=(e.total if chave=='preparo' else e.consultados) * MANUAL_SEGUNDOS[chave]
        delta=manual-e.segundos
        return f'{duracao(manual)} manual (hipótese de {MANUAL_SEGUNDOS[chave]}s por registro) · RPA {duracao(e.segundos)} · diferença {"+" if delta>=0 else "−"}{duracao(abs(delta))}'


def relatorio_tecnico(estat: Estatisticas, historico, destino: Path) -> Path:
    """Gera TXT sem PII na pasta da planilha, usando somente dados de lista fechada.

    Identificadores de execução e hashes são permitidos; caminhos/nome original
    não são incluídos. Os detalhes de erro são apenas códigos permitidos.
    """
    destino = Path(destino)
    if destino.suffix.lower() != '.txt':
        raise ValueError('Somente TXT')
    if destino.exists():
        raise FileExistsError('Relatório já existe; não sobrescrever')
    eventos = []
    if historico:
        import json
        from governanca import EVENTOS, ETAPAS
        caminho=historico.pasta/'eventos_seguros.jsonl'
        if caminho.is_file():
            for linha in caminho.read_text(encoding='utf-8').splitlines():
                try:
                    item=json.loads(linha)
                    if item.get('execucao') != historico.id: continue
                    evento=item.get('evento')
                    etapa=item.get('etapa')
                    if evento not in EVENTOS or etapa not in ETAPAS: continue
                    indice=item.get('registro_ordinal')
                    referencia=f' · registro ordinal {indice}' if type(indice) is int and 1<=indice<=10000000 else ''
                    eventos.append(f'{evento} · etapa {etapa}{referencia}')
                except (ValueError,TypeError,KeyError):
                    continue
    inicio=estat.inicio.strftime('%d/%m/%Y %H:%M:%S')
    fim=estat.termino.strftime('%d/%m/%Y %H:%M:%S') if estat.termino else 'Não finalizada'
    linhas=['RPA SISREG — RELATÓRIO TÉCNICO DE EXECUÇÃO', '='*51,
            'Documento administrativo, sem dados identificáveis dos pacientes.',
            'A coleta automatizada não constitui decisão ou atesto fiscal.', '',
            f'Versão: {APP_VERSION}',
            f'Ambiente: {platform.system()} | Python {sys.version_info.major}.{sys.version_info.minor} | empacotado={bool(getattr(sys, "frozen", False))}',
            f'Execução: {historico.id if historico else "Não disponível"}',
            f'Início: {inicio}',f'Término: {fim}',f'Situação: {estat.situacao}',
            f'Tempo total decorrido (inclui intervalos entre etapas): {duracao(estat.total_segundos)}',
            f'Tempo manual hipotético acumulado: {duracao(estat.total_manual())}',
            'Premissas hipotéticas: CPF 15s/registro; CNS 10s/consulta; internação 10s/consulta.',
            'Não constitui medição de produtividade manual ou economia comprovada.','',
            'FONTES (somente hashes SHA-256)']
    if historico:
        for fonte in historico.origens:
            tipo=fonte.get('tipo','')
            sha=fonte.get('sha256','')
            if tipo in ('xlsx','pdf') and len(sha)==64 and all(c in '0123456789abcdef' for c in sha.lower()):
                linhas.append(f'{tipo.upper()}: {sha}')
    linhas.extend(['','ETAPAS'])
    for chave,e in estat.etapas.items():
        linhas.extend([f'{ROTULOS[chave]} [{"concluída" if e.concluida else "parcial/não iniciada"}]',
            f'  Universo elegível: {e.total}; tentados: {e.consultados}; encontrados: {e.encontrados}; pendências: {e.pendencias}; erros técnicos: {e.falhas_tecnicas}',
            f'  Completude: {percentual(e.encontrados,e.total)}; tempo medido: {duracao(e.segundos)}',
            f'  Manual hipotético: {duracao((e.total if chave=="preparo" else e.consultados)*MANUAL_SEGUNDOS[chave])} ({MANUAL_SEGUNDOS[chave]}s por registro efetivamente tratado)'])
        for fase, segundos in e.fases.items():
            # Fases são nomes controlados, e jamais mensagens de exceção.
            if fase in ('planilha','indexacao_pdf','cruzamento','gravacao'):
                linhas.append(f'  {fase}: {duracao(segundos)}')
    linhas.extend(['', 'DIAGNÓSTICO DE AUTOMAÇÃO (SEM IDENTIFICADORES)',
        'Formato: UTC | operação | resultado | ordinal (quando aplicável) | duração (s) | categoria.',
        'Categorias codificadas, sem argumentos de navegação, valores do DOM, credenciais ou stack trace.',
        'Ambiente: navegador institucional em sessão HTTPS oficial; validação de origem por operação.',
        'A interpretação do resultado depende dos seletores oficiais disponíveis na sessão.'])
    if estat.diagnosticos:
        from collections import Counter
        falhas = Counter(d['categoria'] for d in estat.diagnosticos if d['resultado'] in ('ERRO','TIMEOUT','PENDENCIA') and d['categoria'] != 'NENHUM')
        linhas.append('Resumo de ocorrências técnicas por categoria (pode haver várias por registro):')
        for categoria, total in sorted(falhas.items()):
            linhas.append(f'  {categoria}: {total}')
        linhas.append('Trilha cronológica das operações:')
        for evento in estat.diagnosticos:
            ord_txt = str(evento['ordinal']) if evento['ordinal'] is not None else '-'
            segundos_txt = f"{evento['segundos']:.3f}" if evento['segundos'] is not None else '-'
            linhas.append(f"{evento['utc']} | {evento['acao']} | {evento['resultado']} | "
                         f"ordinal={ord_txt} | duracao={segundos_txt} | {evento['categoria']}")
    else:
        linhas.append('Nenhum diagnóstico adicional disponível para esta execução.')
    linhas.extend(['', 'EVENTOS TÉCNICOS (SEM PII)', *(eventos or ['Nenhum evento local disponível']),
                   '', 'EXCEÇÕES DEVEM SER TRATADAS PELO FISCAL. NÃO HÁ ATESTO AUTOMÁTICO.',''])
    destino.parent.mkdir(parents=True,exist_ok=True)
    fd,tmp=tempfile.mkstemp(prefix='.rpa_sisreg_',suffix='.tmp',dir=destino.parent)
    try:
        if os.name!='nt':os.fchmod(fd,0o600)
        with os.fdopen(fd,'w',encoding='utf-8') as f:
            f.write('\n'.join(linhas))
            f.flush();os.fsync(f.fileno())
        os.replace(tmp,destino)
    finally:
        Path(tmp).unlink(missing_ok=True)
    return destino
