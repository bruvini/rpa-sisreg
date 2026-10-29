"""Retomada segura do RPA SISREG, sem armazenar identificadores de pacientes.

Decisões são tomadas em memória usando apenas campos do XLSX institucional.
Não tenta contornar expiração de sessão, CAPTCHA, bloqueio ou suspensão do Windows.
"""
from __future__ import annotations
from dataclasses import dataclass
from aih_extract import cpf_valido, cns_formato

REVISAO_MANUAL = frozenset({
    'Não encontrado na consulta SISREG',
    'Cadastro não confirmado no SISREG — revisar',
    'AIH não confirmada na consulta — revisar',
    'Dados divergentes na consulta SISREG',
    'Dados divergentes do espelho de AIH',
    'Não encontrado no espelho de AIH',
    'Dados divergentes no SISREG',
    'Não encontrado AIH no SISREG',
})
IMPEDIMENTOS_PDF = frozenset({
    'CPF_CONFLITANTE_PDF', 'CNS_CONFLITANTE_PDF',
    'ESPELHOS_CONFLITANTES', 'NOME_DIVERGENTE_ESPELHO',
    'AIH_FORMATO_INVALIDO', 'CPF_HOSPITAL_INVALIDO',
    'CNS_HOSPITAL_INVALIDO', 'NOME_NAO_INFORMADO',
})

def candidato_cadastro(registro) -> bool:
    """Retoma apenas cadastros ainda não resolvidos ou com falha técnica.

    Não recorre automaticamente casos que já demandam revisão da fiscalização.
    Um CNS existente (mesmo inválido) nunca é substituído silenciosamente.
    """
    if (not cpf_valido(registro.cpf) or registro.cns or not registro.aih
            or not registro.nome or registro.situacao in IMPEDIMENTOS_PDF):
        return False
    atual = str(registro.situacao or '').upper()
    # Numa segunda autenticação da MESMA execução, não repesquisar
    # automaticamente um paciente que já ficou para revisão de identidade.
    if atual.startswith('PENDENTE_') and not any(
            x in atual for x in ('FALHA_', 'TIMEOUT', 'NAVEGACAO', 'SELETOR')):
        return False
    return (getattr(registro, 'situacao_anterior', '') or '').strip() not in REVISAO_MANUAL


def selecionar_cadastros(registros) -> tuple[list[int], int]:
    pendentes = [i for i, registro in enumerate(registros) if candidato_cadastro(registro)]
    revisao = sum(bool(r.cpf) and not r.cns and
                 (getattr(r, 'situacao_anterior', '') or '').strip() in REVISAO_MANUAL
                 for r in registros)
    # A ordem original da planilha é preservada.
    return pendentes, revisao


@dataclass
class SaudeLote:
    """Evita transformar uma sequência inesperada em falsas pendências."""
    nao_confirmados_consecutivos: int = 0
    erros_consecutivos: int = 0
    max_nao_confirmados: int = 4
    max_erros: int = 3

    def registrar(self, cns: str | None, *, erro_tecnico: bool) -> str:
        if cns:
            self.nao_confirmados_consecutivos = 0
            self.erros_consecutivos = 0
            return 'OK'
        if erro_tecnico:
            self.erros_consecutivos += 1
            if self.erros_consecutivos >= self.max_erros:
                return 'SUSPENDER_ERRO'
            return 'PENDENCIA_TECNICA'
        self.erros_consecutivos = 0
        self.nao_confirmados_consecutivos += 1
        if self.nao_confirmados_consecutivos >= self.max_nao_confirmados:
            return 'SUSPENDER_IDENTIDADE'
        return 'PENDENCIA_IDENTIDADE'
