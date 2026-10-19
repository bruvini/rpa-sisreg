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
COLUNAS_ADICIONAIS = ('rpaSituacao', 'rpaDetalhe', 'rpaOrigemPDF',
                      'rpaConsultaAmbulatorial', 'rpaAtualizadoEm')


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


class SessaoPlanilha:
    def __init__(self) -> None:
        self.origem: Path | None = None
        self.registros: list[Registro] = []
        self.diagnosticos: list[str] = []
        self.hash_planilha = ''
        self.hash_pdf = ''

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
                for n, linha in enumerate(ws.iter_rows(min_row=2, max_col=7, values_only=True), 2):
                    if not any(v is not None and valor_texto(v) for v in linha):
                        continue
                    campos = [valor_texto(v) for v in linha]
                    aih = normalizar_aih(campos[1])
                    r = Registro(aba, n, campos[0], aih, campos[2], campos[3],
                                 campos[4], campos[5], campos[6],
                                 cpf_origem=campos[3], cns_origem=campos[4])
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
                    self.registros.append(r)
        finally:
            wb.close()
        self.origem = p
        self.hash_planilha = hashlib.sha256(p.read_bytes()).hexdigest()
        self.hash_pdf = ''
        return len(self.registros)

    def complementar_pdf(self, index: dict[str, list[Espelho]], caminho_pdf: str | Path) -> dict[str, int]:
        if not self.origem:
            raise ValueError('Carregue primeiro a planilha.')
        caminho_pdf = Path(caminho_pdf)
        self.hash_pdf = hashlib.sha256(caminho_pdf.read_bytes()).hexdigest()
        contagem: dict[str, int] = {}
        for r in self.registros:
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
        wb = load_workbook(self.origem, keep_links=False)
        try:
            for aba in ABAS:
                ws = wb[aba]
                for i, cab in enumerate(COLUNAS_ADICIONAIS, 8):
                    ws.cell(1, i, cab)
                ws.freeze_panes = 'A2'
                ws.auto_filter.ref = f'A1:L{max(ws.max_row, 2)}'
            for r in self.registros:
                ws = wb[r.aba]
                # Sobrescritas SOMENTE de campos vazios já confirmados.
                if not r.cpf_origem and r.cpf:
                    ws.cell(r.linha, 4, r.cpf).number_format = '@'
                if not r.cns_origem and r.cns:
                    ws.cell(r.linha, 5, r.cns).number_format = '@'
                campos = (r.situacao, r.detalhe, r.origem_pdf,
                          r.consulta_ambulatorial, r.atualizado_em)
                for c, texto in enumerate(campos, 8):
                    celula = ws.cell(r.linha, c)
                    # Escrever como texto, nunca fórmula proveniente dos dados.
                    celula.value = "'" + texto if texto.startswith(('=', '+', '-', '@')) else texto
            destino.parent.mkdir(parents=True, exist_ok=True)
            wb.save(destino)
        finally:
            wb.close()
        return destino
