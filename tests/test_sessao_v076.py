"""CAPTCHA: intervenção humana, sem bypass e sem dados pessoais. HTML fictício."""
import sys
import time
import queue
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from app_info import APP_VERSION
from controle_sessao import AguardarHumano, texto_exige_verificacao, desafio_visivel
from sisreg_login import Aplicativo


class FakePagina:
    url='https://sisregiii.saude.gov.br/cgi-bin/index'
    def __init__(self, texto=''):
        self.texto=texto
        self.fechada=False
    def is_closed(self):return self.fechada
    def locator(self, selector):
        return SimpleNamespace(inner_text=lambda **kwargs:self.texto)
    def goto(self,*args,**kwargs):pass

class FakeContexto:
    def __init__(self,pagina):self.pages=[pagina]
    def new_page(self):return self.pages[0]

class FakeBrowser:
    def __init__(self,pagina):self.contexto=FakeContexto(pagina);self.fechado=False
    def new_context(self,**kwargs):return self.contexto
    def close(self):self.fechado=True
    def is_connected(self):return not self.fechado

class FakePlaywright:
    def __init__(self,browser):self.browser=browser
    def __enter__(self):return SimpleNamespace(chromium=SimpleNamespace(launch=lambda **kw:self.browser))
    def __exit__(self,*a):return False

class TesteCAPTCHA(unittest.TestCase):
    def test_versao(self):self.assertEqual(APP_VERSION,'0.7.10')
    def test_texto_sisreg_detectado(self):
        self.assertTrue(texto_exige_verificacao('Devido a grande quantidade de requisições (> 500) ... CAPTCHA'))
        self.assertTrue(texto_exige_verificacao('Teste automatizado para diferenciação entre computadores e humanos'))
        self.assertTrue(texto_exige_verificacao('reCAPTCHA'))
        self.assertFalse(texto_exige_verificacao('Consulta ao cadastro de pacientes SUS'))
    def test_detecta_somente_pagina_institucional(self):
        self.assertTrue(desafio_visivel(FakeContexto(FakePagina('Teste CAPTCHA'))))
        p=FakePagina('Teste CAPTCHA');p.url='https://outro.exemplo.com'
        self.assertFalse(desafio_visivel(FakeContexto(p)))
    def test_espera_sem_timeout_automatico(self):
        aguarda=AguardarHumano()
        parar=threading.Event();resultados=[]
        t=threading.Thread(target=lambda:resultados.append(aguarda.esperar(parar)))
        t.start()
        time.sleep(.3)
        self.assertTrue(t.is_alive())
        aguarda.confirmar();t.join(2)
        self.assertEqual(resultados,[True])
    def test_cancelamento_nao_envia_consulta(self):
        aguarda=AguardarHumano()
        parar=threading.Event();reiniciar=threading.Event();resultados=[]
        t=threading.Thread(target=lambda:resultados.append(aguarda.esperar(parar,reiniciar)))
        t.start();reiniciar.set();t.join(2)
        self.assertEqual(resultados,[False])
    def test_navegador_permanece_aberto_ate_confirmacao_humana(self):
        page=FakePagina('CAPTCHA - necessário verificar humano')
        browser=FakeBrowser(page)
        app=Aplicativo.__new__(Aplicativo)
        app.parar=threading.Event();app.reiniciar_navegador=threading.Event()
        app.aguardar_humano=AguardarHumano();app.eventos=queue.Queue();app.comandos=queue.Queue()
        with patch('sisreg_login.sync_playwright',return_value=FakePlaywright(browser)), \
             patch('sisreg_login.submeter_login') as enviar, \
             patch('sisreg_login.autenticao_ativa',return_value=True) as autenticar:
            t=threading.Thread(target=app._navegador_worker,args=('ficticio','senha-ficticia','chrome'))
            t.start()
            primeiro=app.eventos.get(timeout=2)
            segundo=app.eventos.get(timeout=2)
            self.assertEqual((primeiro[0],segundo[0]),('login_enviado','verificacao_pendente'))
            # O timeout legado de 45 s não existe mais no trecho que aguarda humano.
            # Aqui verificamos que a espera não tenta autenticar nem fecha a página.
            time.sleep(.35)
            self.assertFalse(browser.fechado)
            self.assertTrue(t.is_alive())
            self.assertEqual(autenticar.call_count,0)
            page.texto='Página de navegação autenticada'
            app.aguardar_humano.confirmar()
            sucesso=app.eventos.get(timeout=3)
            self.assertEqual(sucesso[0],'autenticado')
            self.assertEqual(autenticar.call_count,1)
            app.parar.set();t.join(3)
            self.assertTrue(browser.fechado)
    def test_modulo_nao_inclui_scripts_de_bypass(self):
        s=(ROOT/'src'/'controle_sessao.py').read_text(encoding='utf-8')
        self.assertNotIn('captcha.solve',s)
        self.assertNotIn('captcha_bypass',s)
        self.assertNotIn('stealth',s)

if __name__=='__main__':unittest.main()
