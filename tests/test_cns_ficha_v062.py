"""Ficha cadastral SISREG com dados fictícios, sem acesso a serviço externo."""
import os
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from sisreg_navigation import (
    avaliar_ficha_cadastro_estruturada, ler_resultado_cadastro,
    ler_ficha_cadastro_estruturada, CNS_CADASTRO_RESULTADO
)
from apresentacao import rotulo_situacao
from app_info import APP_VERSION

NOME='ANA MARIA EXEMPLO'
CPF='11144477735'
CNS='900000000000001'

HTML='''<!doctype html><html><body><div id="main_div"><form>
<center><table><tbody>
<tr><td colspan="2">DADOS PESSOAIS</td></tr>
<tr><td>CNS:</td></tr>
<tr><td colspan="2"><font size="3"><b>900000000000001</b></font></td></tr>
<tr><td>Nome:</td><td>Nome Social / Apelido:</td></tr>
<tr><td>ANA MARIA EXEMPLO</td><td>---</td></tr>
<tr><td>Data de Nascimento:</td><td>Sexo:</td></tr>
<tr><td>01/01/1980</td><td>FEMININO</td></tr>
<tr><td>DOCUMENTOS:</td></tr>
<tr><td>CPF:</td></tr><tr><td>111.444.777-35</td></tr>
</tbody></table></center></form></div></body></html>'''

class TestesEstruturados(unittest.TestCase):
    def test_seletor_cns_conforme_tela(self):
        self.assertEqual(CNS_CADASTRO_RESULTADO,
          'xpath=//*[@id="main_div"]/form/center[1]/table/tbody/tr[3]/td')
    def test_dados_com_identidade_exata(self):
        n,m=avaliar_ficha_cadastro_estruturada(
          {'fichaEncontrada':True,'cns':CNS,'nome':NOME,'cpf':'111.444.777-35'},NOME,CPF)
        self.assertEqual((n,m),(CNS,'CNS_CONFIRMADO_FICHA_IDENTIDADE'))
    def test_nome_divergente(self):
        n,m=avaliar_ficha_cadastro_estruturada(
          {'fichaEncontrada':True,'cns':CNS,'nome':'OUTRA PESSOA','cpf':CPF},NOME,CPF)
        self.assertIsNone(n)
        self.assertEqual(m,'NOME_DIVERGENTE_RESULTADO')
    def test_cpf_divergente(self):
        n,m=avaliar_ficha_cadastro_estruturada(
          {'fichaEncontrada':True,'cns':CNS,'nome':NOME,'cpf':'52998224725'},NOME,CPF)
        self.assertIsNone(n)
        self.assertEqual(m,'CPF_DIVERGENTE_CADASTRO')
    def test_cpf_ausente_impede_vinculo(self):
        n,m=avaliar_ficha_cadastro_estruturada(
          {'fichaEncontrada':True,'cns':CNS,'nome':NOME,'cpf':''},NOME,CPF)
        self.assertIsNone(n)
        self.assertEqual(m,'CPF_NAO_CONFIRMADO_RESULTADO')
    def test_cns_invalido_impede_vinculo(self):
        n,m=avaliar_ficha_cadastro_estruturada(
          {'fichaEncontrada':True,'cns':'000','nome':NOME,'cpf':CPF},NOME,CPF)
        self.assertIsNone(n)
    def test_status_pendencia_humanizado(self):
        self.assertEqual(rotulo_situacao('CPF_NAO_CONFIRMADO_RESULTADO'),
                         'CPF não identificado na ficha cadastral')
    def test_versao(self):
        self.assertEqual(APP_VERSION,'0.7.8')

@unittest.skipUnless(os.environ.get('SISREG_DOM_TEST')=='1',
                     'Requer Chromium Playwright local; sem acesso externo')
class TesteBrowserOffline(unittest.TestCase):
    def setUp(self):
        from playwright.sync_api import sync_playwright
        self.p=sync_playwright().start()
        self.b=self.p.chromium.launch(headless=True, executable_path='/usr/bin/chromium', args=['--no-sandbox'])
        self.page=self.b.new_page()
        self.page.set_content(HTML,wait_until='domcontentloaded')  # conteúdo offline
    def tearDown(self):
        self.b.close();self.p.stop()
    def test_nome_cpf_cns_rótulos_em_linhas_separadas(self):
        dados=ler_ficha_cadastro_estruturada(self.page)
        self.assertEqual(dados['cns'],CNS)
        self.assertEqual(dados['nome'],NOME)
        self.assertEqual(dados['cpf'],'111.444.777-35')
        self.assertTrue(dados['fichaEncontrada'])
        self.assertEqual(ler_resultado_cadastro(self.page,NOME,CPF,espera=1000),
                         (CNS,'CNS_CONFIRMADO_FICHA_IDENTIDADE'))
    def test_rejeita_identidade_diferente(self):
        self.assertEqual(ler_resultado_cadastro(self.page,'OUTRO NOME',CPF,espera=1000),
                         (None,'NOME_DIVERGENTE_RESULTADO'))
    def test_rejeita_cpf_diferente(self):
        self.assertEqual(ler_resultado_cadastro(self.page,NOME,'52998224725',espera=1000),
                         (None,'CPF_DIVERGENTE_CADASTRO'))
