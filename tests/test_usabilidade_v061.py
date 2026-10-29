"""Regressão de interface e fluxo v0.6.1; somente dados sintéticos."""
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from apresentacao import rotulo_situacao
from planilha import SessaoPlanilha
from sisreg_navigation import ler_cadastro_contexto
from app_info import APP_VERSION

CPF='11144477735'
NOME='ANA MARIA EXEMPLO'
CNS='900000000000001'


class TestesRegressao(unittest.TestCase):
    def test_status_sao_humanizados_sem_alterar_codigo(self):
        self.assertEqual(rotulo_situacao('DOCUMENTO_PDF_LOCALIZADO'), 'Documento encontrado no espelho')
        self.assertEqual(rotulo_situacao('NOME_DIVERGENTE_ESPELHO'), 'Nome diferente no espelho')
        self.assertEqual(rotulo_situacao('PENDENTE_NOME_NAO_CONFIRMADO_RESULTADO'),
                         'Não foi possível confirmar o nome no resultado')

    def test_copia_trabalho_nome_dinamico_e_fonte_preservada(self):
        with tempfile.TemporaryDirectory() as d:
            origem=Path(d)/'entrada_hospitalar.xlsx'
            shutil.copy2(Path(__file__).parent/'fixtures/hospital_sintetico.xlsx',origem)
            hash_original=origem.read_bytes()
            s=SessaoPlanilha();s.carregar(origem)
            saida=s.preparar_copia_de_trabalho()
            self.assertRegex(saida.name,r'^Planilha_RPA_\d{8}_\d{6}(?:_\d+)?\.xlsx$')
            self.assertNotEqual(saida,origem)
            self.assertEqual(origem.read_bytes(),hash_original)
            self.assertEqual(saida.read_bytes(),hash_original)

    def test_nome_dinamico_nao_sobrescreve_outro_xlsx(self):
        with tempfile.TemporaryDirectory() as d:
            original=Path(d)/'origem.xlsx'
            shutil.copy2(Path(__file__).parent/'fixtures/hospital_sintetico.xlsx', original)
            s=SessaoPlanilha();s.carregar(original)
            with patch('planilha.datetime') as dt:
                dt.now.return_value.strftime.return_value='20102026_123456'
                anterior=Path(d)/'Planilha_RPA_20102026_123456.xlsx'
                anterior.write_bytes(b'arquivo anterior intocado')
                result=s.preparar_copia_de_trabalho()
            self.assertEqual(result.name,'Planilha_RPA_20102026_123456_2.xlsx')
            self.assertEqual(anterior.read_bytes(),b'arquivo anterior intocado')

    def test_callback_progressivo_inclui_todas_linhas_e_pendencias(self):
        from aih_extract import extrair_texto_paginas
        with tempfile.TemporaryDirectory() as d:
            origem=Path(d)/'hospital.xlsx'
            shutil.copy2(Path(__file__).parent/'fixtures/hospital_sintetico.xlsx', origem)
            s=SessaoPlanilha();s.carregar(origem)
            ix=extrair_texto_paginas(['Num AIH: 900000000012-3\nPaciente: ANA MARIA\nCNS/CPF: 11144477735'])
            arq_pdf=Path(d)/'espelho.pdf';arq_pdf.write_bytes(b'sintetico')
            eventos=[]
            s.complementar_pdf(ix,arq_pdf,progresso=lambda n,r,total: eventos.append((n,r.situacao,r.cpf)))
            self.assertEqual(len(eventos),len(s.registros))
            self.assertTrue(eventos[0][2]==CPF)

    def test_popup_consulta_cns_eh_considerado(self):
        class FakePage:
            def __init__(self,url):self.url=url
            def is_closed(self):return False
        principal=FakePage('https://sisregiii.saude.gov.br/cgi-bin/index')
        popup=FakePage('https://sisregiii.saude.gov.br/cgi-bin/busca')
        class Contexto:pages=[principal,popup]
        def leitura(page,nome,cpf,espera):
            return (CNS,'CNS_CONFIRMADO_TD_NEGRITO') if page is popup else (None,'NOME_NAO_CONFIRMADO_RESULTADO')
        with patch('sisreg_navigation.ler_resultado_cadastro',side_effect=leitura):
            cns,motivo=ler_cadastro_contexto(Contexto(),principal,NOME,CPF,espera=500)
        self.assertEqual((cns,motivo),(CNS,'CNS_CONFIRMADO_SISREG'))

    def test_popup_de_site_nao_oficial_nao_e_consultado(self):
        class FakePage:
            def __init__(self,url):self.url=url
            def is_closed(self):return False
        p=FakePage('https://sisregiii.saude.gov.br/cgi-bin/index')
        estranho=FakePage('https://example.com/')
        class Contexto:pages=[p,estranho]
        consultados=[]
        def ler(page,*args,**kwargs):
            consultados.append(page.url)
            return None,'NOME_NAO_CONFIRMADO_RESULTADO'
        with patch('sisreg_navigation.ler_resultado_cadastro',side_effect=ler):
            cns,motivo=ler_cadastro_contexto(Contexto(),p,NOME,CPF,espera=100)
        self.assertIsNone(cns)
        self.assertTrue(all(x.startswith('https://sisregiii.saude.gov.br/') for x in consultados))

    def test_cns_de_pacientes_conflitantes_nao_e_aceito(self):
        class FakePage:
            url='https://sisregiii.saude.gov.br/cgi-bin/index'
            def is_closed(self):return False
        principal=FakePage(); popup=FakePage()
        class Contexto:pages=[principal,popup]
        def ler(page,*args,**kwargs):
            return ('900000000000001' if page is principal else '900000000000002'), 'CNS_CONFIRMADO_TD_NEGRITO'
        with patch('sisreg_navigation.ler_resultado_cadastro',side_effect=ler):
            numero,motivo=ler_cadastro_contexto(Contexto(),principal,NOME,CPF,espera=250)
        self.assertIsNone(numero)
        self.assertEqual(motivo,'CNS_DESTACADO_AMBIGUO_OU_AUSENTE')

    def test_versao_central(self):self.assertEqual(APP_VERSION,'0.7.13')


@unittest.skipUnless(os.environ.get('SISREG_GUI_TEST')=='1','Exige display gráfico')
class TestesVisuais(unittest.TestCase):
    def test_rodape_visivel_e_botao_nao_comprimido(self):
        import tkinter as tk
        from sisreg_login import Aplicativo
        root=tk.Tk()
        try:
            app=Aplicativo(root)
            root.update()
            self.assertGreaterEqual(app.btn_proxima.winfo_width(), 90)
            self.assertLessEqual(app.btn_proxima.winfo_rooty()+app.btn_proxima.winfo_height(),
                                 root.winfo_screenheight())
            self.assertGreaterEqual(app.btn_encerrar.winfo_width(), 85)
        finally:root.destroy()

    def test_tabelas_colunas_e_avanco(self):
        import tkinter as tk
        from sisreg_login import Aplicativo
        root=tk.Tk()
        try:
            app=Aplicativo(root);root.update()
            self.assertNotIn('cns',app.tabela['columns'])
            self.assertIn('cns',app.tabela_cns['columns'])
            self.assertEqual(str(app.btn_proxima.cget('state')),'disabled')
            app.preparo_concluido=True
            app.abas.tab(1,state='normal')
            app._atualizar_avanco()
            self.assertEqual(str(app.btn_proxima.cget('state')),'normal')
            app._proxima_etapa()
            self.assertEqual(app.abas.index(app.abas.select()),1)
        finally:root.destroy()


if __name__=='__main__':unittest.main()
