"""Indicadores por universo e por retomada, sem identificadores pessoais."""
from dataclasses import dataclass

@dataclass(frozen=True)
class Progresso:
    total: int
    aproveitados: int
    previstos: int
    concluidos_agora: int

    @property
    def acumulados(self) -> int:
        return min(self.total, self.aproveitados + self.concluidos_agora)

    @property
    def taxa_total(self) -> float:
        return 100 * self.acumulados / self.total if self.total else 100.0

    @property
    def taxa_lote(self) -> float:
        return 100 * self.concluidos_agora / self.previstos if self.previstos else 0.0

    def resumo(self) -> str:
        return (f'Total: {self.acumulados}/{self.total} ({self.taxa_total:.1f}%) · '
                f'Nesta execução: {self.concluidos_agora}/{self.previstos} '
                f'({self.taxa_lote:.1f}%' + ('' if self.previstos else ' — sem consultas necessárias') + ') · '
                f'Já aproveitados: {self.aproveitados}')


def resumo_progresso(total: int, aproveitados: int, previstos: int, concluidos_agora: int) -> Progresso:
    if any(v < 0 for v in (total, aproveitados, previstos, concluidos_agora)):
        raise ValueError('Contagens negativas não são válidas')
    if aproveitados > total or previstos > total - aproveitados or concluidos_agora > previstos:
        raise ValueError('Contagem incompatível com o universo')
    return Progresso(total, aproveitados, previstos, concluidos_agora)


def ficha_hospitalar_completa(registro) -> bool:
    """Três campos coletados + classificação anterior coerente. Não é atesto."""
    from aih_extract import cns_formato
    anterior=(getattr(registro,'situacao_anterior','') or '').strip()
    procedimento=(getattr(registro,'comparacao_anterior','') or '').strip()
    return (cns_formato(registro.cns) and bool(registro.carater) and bool(registro.autorizador)
            and procedimento in ('Compatível','Divergente')
            and anterior in ('Consulta sem divergências', 'Dados divergentes no SISREG',
                             'Procedimento divergente — revisão fiscal'))


def candidato_hospitalar(registro) -> bool:
    from aih_extract import cns_formato
    if not (cns_formato(registro.cns) and registro.aih and registro.nome):
        return False
    if registro.situacao.startswith(('CNS_CONFLITO','CPF_CONFLITANTE','ESPELHOS_CONFLITANTES')):
        return False
    if getattr(registro, 'consulta_hospitalar', '') in ('FICHA_CONFERIDA','PROCEDIMENTO_DIVERGENTE'):
        return False
    return not ficha_hospitalar_completa(registro)
