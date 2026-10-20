"""Testes locais. Nenhum acesso ao SISREG real ou a dados de pacientes."""
import os
import sys
import tempfile
import time
import shutil
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from sisreg_navigation import (avaliar_cadastro_com_cns_em_negrito, ler_cns_negrito_pagina)
from sisreg_login import Aplicativo, MANUAL_SEGUNDOS_POR_AIH

CPF = '11144477735'
NOME = 'ANA MARIA EXEMPLO'
CNS = '900000000000001'  # apenas formato ilustrativo; não é dado de paciente de teste real.


class TestesCapturaCNS(unittest.TestCase):
    def test_td_destacado_nome_cpf_pesquisado_sem_input(self):
        cns, motivo = avaliar_cadastro_com_cns_em_negrito(
            'Resultado da busca\nPaciente: ANA MARIA EXEMPLO', [CNS], NOME, CPF, '', True)
        self.assertEqual(cns, CNS)
        self.assertEqual(motivo, 'CNS_CONFIRMADO_NOME_E_PESQUISA_CPF')

    def test_td_com_cpf_confirmado(self):
        cns, motivo = avaliar_cadastro_com_cns_em_negrito(
            'Paciente: ANA MARIA EXEMPLO\nCPF: 111.444.777-35', [CNS], NOME, CPF, CPF)
        self.assertEqual(cns, CNS)
        self.assertEqual(motivo, 'CNS_CONFIRMADO_TD_NEGRITO')

    def test_nome_de_outro_paciente_nao_grava(self):
        cns, motivo = avaliar_cadastro_com_cns_em_negrito(
            'Paciente: JOAO EXEMPLO', [CNS], NOME, CPF, '', True)
        self.assertIsNone(cns)

    def test_cpf_divergente_na_pagina_nao_grava(self):
        cns, motivo = avaliar_cadastro_com_cns_em_negrito(
            'Paciente: ANA MARIA EXEMPLO\nCPF: 529.982.247-25', [CNS], NOME, CPF, '', True)
        self.assertIsNone(cns)
        self.assertEqual(motivo, 'CPF_DIVERGENTE_CADASTRO')

    def test_multiplos_cns_nao_grava(self):
        cns, motivo = avaliar_cadastro_com_cns_em_negrito(
            'Paciente: ANA MARIA EXEMPLO', [CNS, '900000000000002'], NOME, CPF, '', True)
        self.assertIsNone(cns)
        self.assertEqual(motivo, 'CNS_DESTACADO_AMBIGUO_OU_AUSENTE')

    def test_sem_confirmacao_de_busca_nao_grava(self):
        cns, motivo = avaliar_cadastro_com_cns_em_negrito(
            'Paciente: ANA MARIA EXEMPLO', [CNS], NOME, CPF, '', False)
        self.assertIsNone(cns)

    def test_cpf_consultado_incorreto_nao_grava(self):
        cns, motivo = avaliar_cadastro_com_cns_em_negrito(
            'Paciente: ANA MARIA EXEMPLO', [CNS], NOME, CPF, '52998224725', True)
        self.assertIsNone(cns)

    def test_premissa_manual_fixa_15_segundos(self):
        self.assertEqual(MANUAL_SEGUNDOS_POR_AIH, 15)
        self.assertEqual(784 * MANUAL_SEGUNDOS_POR_AIH, 11760)

    def test_leitura_dom_cns_sem_cpf_exibido(self):
        class Locator:
            def count(self): return 0
        class FakeFrame:
            url = 'https://sisregiii.saude.gov.br/cgi-bin/index'
            def evaluate(self, *_):
                return {'texto': 'Paciente: ANA MARIA EXEMPLO',
                        'numeros': [CNS], 'cpfPesquisa': ''}
            def locator(self, *_): return Locator()
        class FakePage:
            frames = [FakeFrame()]
            url = 'https://sisregiii.saude.gov.br/cgi-bin/index'
        cns, motivo = ler_cns_negrito_pagina(FakePage(), NOME, CPF, espera=50)
        self.assertEqual(cns, CNS)
        self.assertEqual(motivo, 'CNS_CONFIRMADO_NOME_E_PESQUISA_CPF')


@unittest.skipUnless(os.environ.get('SISREG_GUI_TEST') == '1', 'GUI exige Xvfb e SISREG_GUI_TEST=1')
class TesteFluxoTk(unittest.TestCase):
    def setUp(self):
        import tkinter as tk
        self.tk=tk.Tk()
        self.app=Aplicativo(self.tk)
        self.tk.update()

    def tearDown(self):
        self.tk.destroy()

    def test_etapas_bloqueadas_antes_da_preparacao(self):
        self.assertEqual(str(self.app.abas.tab(1,'state')), 'disabled')
        self.assertEqual(str(self.app.abas.tab(2,'state')), 'disabled')
        self.assertEqual(str(self.app.btn_lote.cget('state')), 'disabled')

    def test_preparacao_abre_etapa2_e_mostra_resultado(self):
        from tkinter import TclError
        from pathlib import Path
        with tempfile.TemporaryDirectory() as d:
            modelo=Path(__file__).parent/'fixtures'/'hospital_sintetico.xlsx'
            amostra=Path(d)/'dados.xlsx'
            shutil.copy2(modelo,amostra)
            self.app.arquivo_planilha=amostra
            self.app.arquivo_pdf=Path(__file__).parent/'fixtures'/'espelho_sintetico.pdf'
            self.app._preparar()
            fim=time.monotonic()+14
            while self.app.carregando and time.monotonic()<fim:
                self.tk.update()
                time.sleep(.06)
            self.assertFalse(self.app.carregando, self.app.status.get())
            self.assertTrue(self.app.preparo_concluido, self.app.status.get())
            self.assertEqual(str(self.app.abas.tab(1,'state')),'normal')
            self.assertEqual(str(self.app.abas.tab(2,'state')),'disabled')
            self.assertIn('15 s/AIH',self.app.resultado_descritivo.get())
            self.assertIn('Extração automática concluída',self.app.resultado_titulo.get())
            self.assertTrue(any(x.name.startswith('Planilha_RPA_') and x.suffix=='.xlsx' for x in amostra.parent.iterdir()))


if __name__ == '__main__':
    unittest.main()

@unittest.skipUnless(os.environ.get('SISREG_DOM_TEST') == '1',
                     'Teste HTML offline opcional: definir SISREG_DOM_TEST=1')
class TesteDomRealOffline(unittest.TestCase):
    def test_extrai_cns_de_td_font_b_html_sintetico(self):
        """Executa somente HTML local; não transmite CPF ou acessa SISREG."""
        from playwright.sync_api import sync_playwright
        from sisreg_navigation import ler_cns_negrito_pagina
        html = ('<!doctype html><html><body><p>Paciente: ANA MARIA EXEMPLO</p>'
                '<table><tr><td colspan="2"><font size="3">'
                '<b>900000000000001</b></font></td></tr></table></body></html>')

        class PaginaOffline:
            url = 'https://sisregiii.saude.gov.br/cgi-bin/index'
            def __init__(self, pagina):
                self.pagina = pagina
                self.frames = [self]
            def evaluate(self, *args, **kwargs):
                return self.pagina.evaluate(*args, **kwargs)
            def locator(self, *args, **kwargs):
                return self.pagina.locator(*args, **kwargs)

        with sync_playwright() as pw:
            # Cromium do ambiente de testes; não há navegação de rede.
            exe = os.environ.get('SISREG_CHROME_TEST', '/usr/bin/chromium')
            browser = pw.chromium.launch(executable_path=exe, headless=True,
                                         args=['--no-sandbox'])
            try:
                pg=browser.new_page()
                pg.set_content(html)
                cns, motivo = ler_cns_negrito_pagina(
                    PaginaOffline(pg), NOME, CPF, espera=800)
                self.assertEqual(cns, '900000000000001')
                self.assertEqual(motivo, 'CNS_CONFIRMADO_NOME_E_PESQUISA_CPF')
            finally:
                browser.close()
