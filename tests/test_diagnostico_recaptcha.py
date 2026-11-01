"""Navegador real com recursos fictícios; sem conexão ao Google ou ao SISREG."""
import os
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from playwright.sync_api import sync_playwright

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from diagnostico_recaptcha import MonitorRecaptcha, ROTULOS, _tipo_recurso, _categoria_rede

HOST='https://sisregiii.saude.gov.br'
API='https://www.google.com/recaptcha/api.js'
ANCHOR='https://www.google.com/recaptcha/api2/anchor?teste=ficticio'
SCRIPT="""window.grecaptcha={render:function(){}};
var f=document.createElement('iframe');f.width=304;f.height=78;
f.src='https://www.google.com/recaptcha/api2/anchor?teste=ficticio';
document.querySelector('.g-recaptcha').appendChild(f);"""
HTML='<!doctype html><h1>Verificação humana CAPTCHA</h1><div class="g-recaptcha"></div><script src="'+API+'"></script>'


class TesteClassificacao(unittest.TestCase):
    def test_enderecos_e_mensagens_livres_nao_vazam_para_categorias(self):
        for url in ('https://www.google.com.exemplo/recaptcha/api.js',
                    'http://www.google.com/recaptcha/api.js',
                    'https://www.google.com:8080/recaptcha/api.js',
                    'https://segredo@www.google.com/recaptcha/api.js'):
            self.assertEqual(_tipo_recurso(url),'')
        self.assertEqual(_tipo_recurso(API+'?segredo=NAO_GRAVAR'),'API')
        self.assertEqual(_tipo_recurso(HOST+'/cgi-bin/recaptcha?cod=0'),'PAGINA')
        self.assertEqual(_tipo_recurso('https://www.gstatic.com/recaptcha/releases/ficticio.js'),'SCRIPT')
        for falha,codigo in (('net::ERR_TIMED_OUT','CAPTCHA_REDE_TIMEOUT'),
                             ('net::ERR_NAME_NOT_RESOLVED','CAPTCHA_REDE_DNS'),
                             ('net::ERR_CERT_AUTHORITY_INVALID','CAPTCHA_REDE_TLS'),
                             ('net::ERR_BLOCKED_BY_CLIENT','CAPTCHA_REDE_BLOQUEADA'),
                             ('MENSAGEM_LIVRE_NAO_GRAVAR','CAPTCHA_REDE_FALHOU')):
            self.assertEqual(_categoria_rede(falha),codigo)

    def test_novo_documento_de_verificacao_limpa_falhas_antigas(self):
        m=MonitorRecaptcha(SimpleNamespace());m.falhas.add('CAPTCHA_REDE_FALHOU')
        m._pedido(SimpleNamespace(url=HOST+'/cgi-bin/recaptcha?cod=0',resource_type='document'))
        self.assertFalse(m.falhas)


class TesteDiagnosticoBrowser(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pw=sync_playwright().start()
        kwargs={'headless':True}
        if os.environ.get('SISREG_TEST_CHROME'):kwargs['executable_path']=os.environ['SISREG_TEST_CHROME']
        cls.browser=cls.pw.chromium.launch(**kwargs)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close();cls.pw.stop()

    def setUp(self):
        self.context=self.browser.new_context()
        self.monitor=MonitorRecaptcha(self.context)
        self.page=self.context.new_page()

    def tearDown(self):self.context.close()

    def servir(self,api_status=200,frame_status=200,bloquear=False):
        def servidor(route):
            url=route.request.url
            if url==API:
                if bloquear:route.abort('blockedbyclient');return
                route.fulfill(status=api_status,content_type='text/javascript',body=SCRIPT if api_status==200 else '')
            elif url.startswith(ANCHOR):
                route.fulfill(status=frame_status,content_type='text/html',body='<body>Componente fictício, sem desafio</body>')
            else:route.fulfill(status=200,content_type='text/html',body=HTML)
        self.context.route('**/*',servidor)
        self.page.goto(HOST+'/cgi-bin/recaptcha?cod=0',wait_until='networkidle')

    def test_http_200_e_iframe_presentes_nao_sao_resolucao_do_captcha(self):
        self.servir()
        resultado=self.monitor.resumo(self.context)
        for categoria in ('CAPTCHA_API_HTTP_OK','CAPTCHA_FRAME_HTTP_OK','CAPTCHA_API_DISPONIVEL','CAPTCHA_IFRAME_PRESENTE'):
            self.assertIn(categoria,resultado)
        self.assertFalse(self.monitor.pendentes)
        self.assertTrue(set(resultado)<=set(ROTULOS))

    def test_script_bloqueado_fica_ausente_e_nao_gera_falsa_confirmacao(self):
        self.servir(bloquear=True)
        resultado=self.monitor.resumo(self.context)
        self.assertIn('CAPTCHA_REDE_BLOQUEADA',resultado)
        self.assertIn('CAPTCHA_API_AUSENTE',resultado)
        self.assertIn('CAPTCHA_IFRAME_AUSENTE',resultado)

    def test_script_que_permanece_carregando_e_registrado_sem_nova_requisicao(self):
        pendencias=[]
        def servidor(route):
            if route.request.url==API:pendencias.append(route)
            else:route.fulfill(status=200,content_type='text/html',body=HTML)
        self.context.route('**/*',servidor)
        self.page.goto(HOST+'/cgi-bin/recaptcha?cod=0',wait_until='commit')
        self.page.locator('.g-recaptcha').wait_for(state='attached')
        self.page.wait_for_timeout(80)
        resultado=self.monitor.resumo(self.context)
        self.assertIn('CAPTCHA_REDE_PENDENTE',resultado)
        self.assertIn('CAPTCHA_API_AUSENTE',resultado)
        self.assertEqual(len(pendencias),1)
        pendencias[0].fulfill(status=200,content_type='text/javascript',body='')
        self.page.wait_for_load_state('networkidle')

    def test_resposta_http_de_erro_e_distinta_da_api_disponivel(self):
        for codigo,categoria in ((403,'CAPTCHA_HTTP_4XX'),(429,'CAPTCHA_HTTP_429'),(503,'CAPTCHA_HTTP_5XX')):
            with self.subTest(codigo=codigo):
                self.servir(frame_status=codigo)
                self.assertIn(categoria,self.monitor.resumo(self.context))
                self.assertIn('CAPTCHA_API_DISPONIVEL',self.monitor.resumo(self.context))

    def test_barra_sandbox_com_erro_nao_impede_outro_iframe(self):
        self.servir()
        erros=[];self.page.on('pageerror',lambda e:erros.append(type(e).__name__))
        self.page.evaluate("""() => {const f=document.createElement('iframe');
          f.id='barra-ficticia';f.sandbox='';f.src='/barra-ficticia';
          f.onload=()=>{f.contentWindow.document.body};document.body.appendChild(f);} """)
        self.page.wait_for_function("document.querySelector('#barra-ficticia').contentWindow !== null")
        self.page.wait_for_load_state('networkidle')
        self.assertTrue(erros)
        self.assertIn('CAPTCHA_IFRAME_PRESENTE',self.monitor.resumo(self.context))


@unittest.skipUnless(os.environ.get('SISREG_GUI_TEST')=='1','Requer ambiente gráfico')
class TesteDiagnosticoInterface(unittest.TestCase):
    def test_diagnostico_persistido_na_pausa_sem_dados_livres_ou_conclusao(self):
        import tkinter as tk
        from sisreg_login import Aplicativo
        root=tk.Tk();root.withdraw()
        try:
            app=Aplicativo(root);app._exibir_verificacao('hospital')
            app.sessao.registros=[SimpleNamespace(nome='NAO_GRAVAR_NOME',cns='NAO_GRAVAR_CNS')]
            with tempfile.TemporaryDirectory() as pasta:
                pasta=Path(pasta)
                with patch('sisreg_login.pastas_de_saida',return_value=(pasta,pasta)):
                    app._registrar_diagnostico_recaptcha(['CAPTCHA_API_HTTP_OK','CAPTCHA_IFRAME_PRESENTE',
                        'NAO_GRAVAR_TOKEN',{'NAO_GRAVAR':'CONTEUDO'}])
                conteudo=next(pasta.glob('DIAGNOSTICO_RECAPTCHA_*.txt')).read_text(encoding='utf-8')
                self.assertIn('CAPTCHA_IFRAME_PRESENTE',conteudo)
                self.assertNotIn('NAO_GRAVAR',conteudo)
                self.assertNotIn('https://',conteudo)
                self.assertTrue(app.intervencao_pendente)
                self.assertFalse(app.aguardar_humano.confirmacao.is_set())
                self.assertFalse(app.estatisticas.etapas['hospital'].concluida)
                self.assertIn('não comprova',app.detalhe_verificacao.get())
        finally:
            for identificador in root.tk.call('after','info'):root.after_cancel(identificador)
            root.destroy()
