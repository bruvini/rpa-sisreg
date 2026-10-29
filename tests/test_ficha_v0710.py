"""Testes de regressão sem uso de dados reais do SISREG."""
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from sisreg_hospital import CARATER, CODIGO_SOLICITACAO, PROCEDIMENTO, FICHA, obter_detalhes
from sisreg_navigation import NavegacaoInesperada
from saida_xlsx import situacao_final, comparacao_procedimento
from planilha import Registro, SessaoPlanilha

AIH = '9000000000123'
PROC = '0408050063'

class Pagina:
    url = 'https://sisregiii.saude.gov.br/cgi-bin/index'
    def __init__(self): self.context = None
    def is_closed(self): return False

class Campo:
    def __init__(self, t): self.t = t
    def inner_text(self, **kwargs): return self.t

class TesteFichaV0710(unittest.TestCase):
    def test_seletores_confirmados(self):
        self.assertIn('nth-child(1)', CODIGO_SOLICITACAO)
        self.assertIn('nth-child(46)', CARATER)
        self.assertIn('nth-child(50)', PROCEDIMENTO)

    def consultar_ficha_simulada(self, texto, proc=PROC, popup=True):
        principal = Pagina()
        ficha = Pagina() if popup else principal
        principal.context = SimpleNamespace(pages=[principal, ficha] if popup else [principal])
        ficha.context = principal.context
        dados = {FICHA:texto, CARATER:'10 - ELETIVO',
                 CODIGO_SOLICITACAO:'670478410', PROCEDIMENTO:PROC+' - PROCEDIMENTO'}
        def localizar(pg, seletor, **kwargs):
            if pg is not ficha or seletor not in dados:
                raise NavegacaoInesperada('Não encontrado')
            return ficha, Campo(dados[seletor])
        with patch('sisreg_hospital._encontrar', side_effect=localizar):
            return obter_detalhes(principal, AIH, proc, espera_ficha_ms=25)

    def test_popup_aih_exata(self):
        resultado = self.consultar_ficha_simulada('AIH 900000000012-3')
        self.assertEqual(resultado.situacao, 'FICHA_CONFERIDA')
        self.assertEqual(resultado.solicitacao, '670478410')

    def test_nao_aceita_ficha_anterior(self):
        resultado = self.consultar_ficha_simulada('AIH 900000000011-1')
        self.assertEqual(resultado.situacao, 'AIH_NAO_COMPROVADA_FICHA')

    def test_procedimento_hospitalar_vazio_nao_e_sucesso(self):
        resultado = self.consultar_ficha_simulada('AIH 900000000012-3', proc='')
        self.assertEqual(resultado.situacao, 'PROCEDIMENTO_NAO_CONFIRMADO')
        registro = Registro('PT6', 2, 'PACIENTE TESTE', AIH, '',
                            '52998224725','700000000000001','','')
        SessaoPlanilha().registrar_hospital(registro, resultado, 1.0)
        self.assertEqual(situacao_final(registro), 'Procedimento não confirmado — consultar ficha')
        self.assertEqual(comparacao_procedimento(registro), 'Não conferido')

if __name__=='__main__': unittest.main()
