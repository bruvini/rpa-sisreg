"""Preparo dos registros, enriquecimento conservador e cópia XLSX.

Planilha original é mantida intacta. Não grava dados pessoais fora da cópia
explicitamente salva pela operadora. Não executa macros nem fórmulas.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
import math
import hashlib
import re
from typing import Any
from aih_extract import (
    Espelho, cpf_valido, cns_formato, digitos, normalizar_aih, escolher_espelho,
)

ABAS = ('POA CIRURGICO', 'PT6', 'ALTA COMPLEXIDADE')
COLUNAS = ('nomePaciente', 'numeroAIH', 'numeroProcedimento', 'numeroCPF',
           'numeroCNS', 'caraterInternacao', 'codigoAutorizador')
from saida_xlsx import CAMPOS_FINAIS as COLUNAS_ADICIONAIS


def valor_texto(valor: Any) -> str:
    if valor is None:
        return ''
    if isinstance(valor, float) and math.isfinite(valor) and valor.is_integer():
        return str(int(valor))
    return str(valor).strip()


@dataclass
class Registro:
    aba: str
    linha: int
    nome: str
    aih: str
    procedimento: str
    cpf: str
    cns: str
    carater: str
    autorizador: str
    situacao: str = 'AGUARDA_PREPARACAO'
    detalhe: str = ''
    origem_pdf: str = ''
    consulta_ambulatorial: str = ''
    atualizado_em: str = ''
    revisado: bool = False
    cpf_origem: str = ''
    cns_origem: str = ''
    consulta_hospitalar: str = ''
    procedimento_sisreg: str = ''
    tempo_consulta: float = 0.0
    solicitacao: str = ''
    situacao_anterior: str = ''  # Texto de H da planilha anterior, sem persistência extra.


class SessaoPlanilha:
    def __init__(self) -> None:
        self.origem: Path | None = None
        self.fonte_original: Path | None = None
        self.registros: list[Registro] = []
        self.diagnosticos: list[str] = []
        self.hash_planilha = ''
        self.hash_pdf = ''
        self.hash_fonte_original = ''
        self.diretorio_trabalho: Path | None = None

    def carregar(self, caminho: str | Path) -> int:
        from openpyxl import load_workbook  # execução apenas local
        p = Path(caminho)
        wb = load_workbook(p, read_only=True, data_only=True, keep_links=False)
        self.registros = []
        self.diagnosticos = []
        try:
            presentes = set(wb.sheetnames)
            if presentes != set(ABAS):
                raise ValueError('As abas devem ser exatamente: ' + ', '.join(ABAS))
            for aba in ABAS:
                ws = wb[aba]
                cab = tuple(valor_texto(c.value) for c in ws[1][:7])
                if cab != COLUNAS:
                    raise ValueError(f'Cabeçalhos incorretos na aba {aba}. Use o modelo padrão, linha 1.')
                for n, linha in enumerate(ws.iter_rows(min_row=2, max_col=8, values_only=True), 2):
                    if not any(v is not None and valor_texto(v) for v in linha):
                        continue
                    campos = [valor_texto(v) for v in linha[:7]]
                    aih = normalizar_aih(campos[1])
                    r = Registro(aba, n, campos[0], aih, campos[2], campos[3],
                                 campos[4], campos[5], campos[6],
                                 cpf_origem=campos[3], cns_origem=campos[4],
                                 situacao_anterior=valor_texto(linha[7]) if len(linha)>7 else '')
                    if not aih:
                        r.situacao = 'AIH_FORMATO_INVALIDO'
                        r.detalhe = 'AIH deve ter 13 dígitos. Corrigir na origem.'
                    elif not r.nome:
                        r.situacao = 'NOME_NAO_INFORMADO'
                        r.detalhe = 'Nome obrigatório para confirmar identidade.'
                    else:
                        r.situacao = 'PRONTO_PARA_CONFERENCIA'
                    if r.cpf and not cpf_valido(r.cpf):
                        r.situacao = 'CPF_HOSPITAL_INVALIDO'
                        r.detalhe = 'CPF preenchido não passou na validação; não sobrescrito.'
                    if r.cns and not cns_formato(r.cns):
                        r.situacao = 'CNS_HOSPITAL_INVALIDO'
                        r.detalhe = 'CNS deve possuir 15 dígitos; não sobrescrito.'
                    # Reaproveita uma ficha já coletada pelo próprio XLSX anterior:
                    # não precisa repetir consultas hospitalares completas.
                    if (r.situacao_anterior == 'Consulta sem divergências'
                            and cns_formato(r.cns) and r.carater and r.autorizador):
                        r.consulta_hospitalar = 'FICHA_CONFERIDA'
                        r.situacao = 'DADOS_COLETADOS_SEM_DIVERGENCIA'
                    self.registros.append(r)
        finally:
            wb.close()
        self.origem = p
        self.fonte_original = None
        self.hash_planilha = hashlib.sha256(p.read_bytes()).hexdigest()
        self.hash_pdf = ''
        self.hash_fonte_original = ''
        self.diretorio_trabalho = None
        return len(self.registros)

    def validar_layout_para_saida(self) -> None:
        """Pré-validação antes de indexar o PDF ou criar a cópia de trabalho.

        A compatibilidade com layouts antigos não fica dependente de uma
        exceção tardia depois de 15–20 segundos de indexação.
        """
        if not self.origem:
            raise ValueError('Nenhuma planilha carregada.')
        from openpyxl import load_workbook
        from saida_xlsx import identificar_layout
        wb=load_workbook(self.origem, read_only=False, data_only=False, keep_links=False)
        try:
            for aba in ABAS:
                identificar_layout(wb[aba])
        finally:
            wb.close()

    def descartar_copia_nao_gravada(self) -> bool:
        """Descarta apenas uma cópia criada nesta sessão ainda idêntica à fonte.

        Nunca elimina um arquivo que já recebeu dados e nunca toca a fonte.
        """
        if not self.fonte_original or not self.origem:
            return False
        p=Path(self.origem)
        if (self.diretorio_trabalho is None or
                p.parent.resolve() != self.diretorio_trabalho.resolve() or
                not p.name.startswith('Planilha_RPA_') or p.suffix.lower() != '.xlsx'):
            return False
        from persistencia import sha256
        if not p.is_file() or not self.hash_fonte_original or sha256(p) != self.hash_fonte_original:
            return False
        p.unlink()
        self.origem=self.fonte_original
        self.fonte_original=None
        self.hash_fonte_original=''
        self.diretorio_trabalho = None
        return True

    def preparar_copia_de_trabalho(self, diretorio_saida: Path | None = None) -> Path:
        """Não modifica a fonte selecionada; a cópia é automática, sem nova etapa."""
        import shutil
        from persistencia import sha256
        if not self.origem:
            raise ValueError('Nenhum arquivo de origem carregado.')
        if self.fonte_original:
            return self.origem
        entrada = Path(self.origem)
        if sha256(entrada) != self.hash_planilha:
            raise ValueError('A planilha de entrada mudou após sua leitura. Recarregue o arquivo.')
        # Nome padronizado e ordenável no Explorer, sem nomes de pacientes ou AIHs.
        momento = datetime.now().strftime('%d%m%Y_%H%M%S')
        base = f'Planilha_RPA_{momento}'
        # Compatibilidade com chamadas antigas: na aplicação, passar sempre Análises.
        pasta = Path(diretorio_saida) if diretorio_saida is not None else entrada.parent
        pasta.mkdir(parents=True, exist_ok=True)
        destino = pasta / (base + '.xlsx')
        sufixo = 2
        while destino.exists():
            destino = pasta / f'{base}_{sufixo}.xlsx'
            sufixo += 1
        # x = exclusivo: evita sobrescrever arquivos criados concorrentemente.
        try:
            with entrada.open('rb') as origem_arq, destino.open('xb') as nova:
                shutil.copyfileobj(origem_arq, nova)
        except Exception:
            destino.unlink(missing_ok=True)
            raise
        if sha256(destino) != self.hash_planilha:
            destino.unlink(missing_ok=True)
            raise ValueError('Cópia de trabalho inválida; planilha de entrada preservada.')
        self.fonte_original = entrada
        self.hash_fonte_original = self.hash_planilha
        self.origem = destino
        self.diretorio_trabalho = pasta
        return destino

    def complementar_pdf(self, index: dict[str, list[Espelho]], caminho_pdf: str | Path,
                        progresso=None) -> dict[str, int]:
        if not self.origem:
            raise ValueError('Carregue primeiro a planilha.')
        caminho_pdf = Path(caminho_pdf)
        self.hash_pdf = hashlib.sha256(caminho_pdf.read_bytes()).hexdigest()
        contagem: dict[str, int] = {}
        for indice, r in enumerate(self.registros, 1):
            try:
                if not r.aih or not r.nome:
                    continue
                e, resultado = escolher_espelho(index.get(r.aih, []), r.nome)
                contagem[resultado] = contagem.get(resultado, 0) + 1
                r.origem_pdf = f'Página {e.pagina}' if e else ''
                if e is None:
                    if r.situacao in ('AIH_FORMATO_INVALIDO', 'CPF_HOSPITAL_INVALIDO', 'CNS_HOSPITAL_INVALIDO', 'NOME_NAO_INFORMADO'):
                        continue
                    r.situacao = resultado
                    r.detalhe = 'Necessária revisão; nenhum identificador foi alterado.'
                    continue
                if e.cpf and r.cpf and digitos(r.cpf) != e.cpf:
                    r.situacao = 'CPF_CONFLITANTE_PDF'
                    r.detalhe = 'CPF do hospital e CPF do espelho são diferentes; não alterados.'
                    continue
                if e.cns and r.cns and digitos(r.cns) != e.cns:
                    r.situacao = 'CNS_CONFLITANTE_PDF'
                    r.detalhe = 'CNS do hospital e CNS do espelho são diferentes; não alterados.'
                    continue
                if e.cpf and not r.cpf:
                    r.cpf = e.cpf
                if e.cns and not r.cns:
                    r.cns = e.cns
                if r.situacao == 'PRONTO_PARA_CONFERENCIA':
                    r.situacao = 'DOCUMENTO_PDF_LOCALIZADO' if e.cpf or e.cns else 'PDF_SEM_DOCUMENTO_VALIDO'
                    r.detalhe = 'Registro de espelho correspondente pela AIH e nome.'
            finally:
                if progresso:
                    progresso(indice, r, len(self.registros))
        return contagem

    def registrar_cadastro_em_lote(self, registro: Registro, cns: str | None, motivo: str) -> None:
        """Só aceita CNS obtido com paciente inequívoco; não substitui conflito."""
        registro.atualizado_em = datetime.now().isoformat(timespec='seconds')
        if cns:
            numero = digitos(cns)
            if not cns_formato(numero):
                raise ValueError('CNS de resultado fora do padrão.')
            if registro.cns and digitos(registro.cns) != numero:
                registro.situacao = 'CNS_CONFLITO_SISREG'
                registro.detalhe = 'CNS do cadastro diferente da planilha/PDF; análise humana requerida.'
                return
            registro.cns = numero
            registro.situacao = 'CNS_CONFIRMADO_SISREG'
            registro.detalhe = 'CNS recuperado com nome inequívoco na pesquisa do cadastro.'
            registro.revisado = True
        else:
            registro.situacao = 'PENDENTE_' + (motivo[:80] or 'CONSULTA')
            registro.detalhe = 'Cadastro pesquisado, mas identidade/CNS não puderam ser comprovados automaticamente.'

    def registrar_hospital(self, registro: Registro, resultado, duracao: float) -> None:
        """Atualiza campos vazios quando a ficha prova AIH exata; divergência exige revisão."""
        registro.tempo_consulta = round(max(0.0, duracao), 2)
        registro.consulta_hospitalar = resultado.situacao
        registro.atualizado_em = datetime.now().isoformat(timespec='seconds')
        registro.procedimento_sisreg = resultado.procedimento or ''
        # Solicitação é vinculada somente quando há AIH exata e ficha confirmada.
        if resultado.situacao in ('FICHA_CONFERIDA', 'PROCEDIMENTO_DIVERGENTE'):
            registro.solicitacao = resultado.solicitacao or ''
        registro.detalhe = resultado.detalhe
        if resultado.situacao not in ('FICHA_CONFERIDA', 'PROCEDIMENTO_DIVERGENTE'):
            registro.situacao = 'PENDENTE_' + resultado.situacao
            return
        # Não alteramos código produzido. Somente vinculamos campos reais e únicos.
        conflitos = []
        if registro.carater and registro.carater.zfill(2) != resultado.carater:
            conflitos.append('CARATER_CONFLITANTE')
        # Comparar autorizador somente quando as DUAS fontes o informam.
        # O Código Solicitação da ficha é outro campo, não autorização.
        if resultado.autorizador and registro.autorizador and registro.autorizador != resultado.autorizador:
            conflitos.append('AUTORIZADOR_CONFLITANTE')
        if conflitos:
            registro.situacao = 'PENDENTE_' + '_'.join(conflitos)
            registro.detalhe = 'Valores da fonte SISREG diferem dos campos preenchidos no hospital; nenhuma substituição.'
            return
        if not registro.carater:
            registro.carater = resultado.carater
        if not registro.autorizador:
            registro.autorizador = resultado.autorizador
        registro.situacao = ('PENDENTE_PROCEDIMENTO_DIVERGENTE'
                             if resultado.situacao == 'PROCEDIMENTO_DIVERGENTE'
                             else 'DADOS_COLETADOS_SEM_DIVERGENCIA')
        registro.revisado = True

    def confirmar_cns_manual(self, registro: Registro, cns: str, identidade_confirmada: bool) -> None:
        numero = digitos(cns)
        if not identidade_confirmada:
            raise ValueError('Confirmação humana do paciente é obrigatória.')
        if not cns_formato(numero):
            raise ValueError('O CNS precisa ter 15 dígitos. Confira no SISREG.')
        if registro.cns and digitos(registro.cns) != numero:
            raise ValueError('CNS do hospital/PDF diverge. Registre revisão, não substitua.')
        registro.cns = numero
        registro.situacao = 'CNS_CONFIRMADO_OPERADORA'
        registro.detalhe = 'CNS informado pela operadora após verificação no SISREG; não extraído automaticamente.'
        registro.revisado = True
        registro.atualizado_em = datetime.now().isoformat(timespec='seconds')

    def marcar_consulta_aberta(self, registro: Registro) -> None:
        registro.consulta_ambulatorial = 'PESQUISA_ABERTA_NAVEGADOR_SEM_VALIDACAO_DE_RESULTADOS'
        registro.atualizado_em = datetime.now().isoformat(timespec='seconds')

    def salvar_na_planilha(self, motivo='lote'):
        from persistencia import gravar_na_origem
        return gravar_na_origem(self, motivo=motivo)

    def salvar_copia(self, destino: str | Path) -> Path:
        from openpyxl import load_workbook
        if not self.origem:
            raise ValueError('Nenhuma planilha carregada.')
        destino = Path(destino)
        if destino.resolve() == self.origem.resolve():
            raise ValueError('Não é permitido substituir a planilha original.')
        # Usa a mesma política e layout do salvamento periódico.
        from persistencia import gravar_na_origem
        # Exportação explícita preserva fonte; delega à rotina de planilha.
        import shutil
        shutil.copy2(self.origem, destino)
        sessao_aux=type('SessaoDeCopia', (), {})()
        sessao_aux.origem=destino
        sessao_aux.fonte_original=self.fonte_original
        sessao_aux.registros=self.registros
        from persistencia import sha256
        sessao_aux.hash_planilha=sha256(destino)
        gravar_na_origem(sessao_aux, motivo='copia', backup=False)
        return destino
