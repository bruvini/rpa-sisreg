"""Regressão sintética: CAPTCHA não fecha a etapa hospitalar nem o relatório."""
import queue
import sys
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from sisreg_login import Aplicativo
from saida_xlsx import situacao_final, orientacao_fiscal
from app_info import APP_VERSION

class FakePagina:
    url='https://sisregiii.saude.gov.br/cgi-bin/index'
    def is_closed(self):return False
    def goto(self,*a,**k):return None

class FakeBrowser:
    def __init__(self):self.pg=FakePagina();self.context=SimpleNamespace(pages=[self.pg],new_page=lambda:self.pg)
    def new_context(self,**kw):return self.context
    def is_connected(self):return True
    def close(self):pass

class FakePlaywright:
    def __enter__(self):return SimpleNamespace(chromium=SimpleNamespace(launch=lambda **kw:FakeBrowser()))
    def __exit__(self,*a):return False

class TesteRetomadaHospitalar(unittest.TestCase):
    def test_versao(self):self.assertEqual(APP_VERSION,'0.7.11')
    def test_tres_erros_pausam_sem_finalizar_a_etapa(self):
        app=Aplicativo.__new__(Aplicativo)
        app.parar=threading.Event();app.pausa=threading.Event();app.reiniciar_navegador=threading.Event()
        app.eventos=queue.Queue();app.comandos=queue.Queue()
        app.comandos.put(('hospital',[0,1,2]))
        fila_real=app.comandos
        class FilaDeTeste:
            def __init__(self):self.primeiro=True
            def get(self,timeout=None):
                if self.primeiro:
                    self.primeiro=False
                    return fila_real.get_nowait()
                app.parar.set()
                raise queue.Empty()
        app.comandos=FilaDeTeste()
        r=SimpleNamespace(cns='700000000000001',aih='9000000000123',procedimento='0401010010')
        app.sessao=SimpleNamespace(registros=[r,r,r])
        with patch('sisreg_login.sync_playwright',return_value=FakePlaywright()), \
             patch('sisreg_login.submeter_login'), \
             patch('sisreg_login.autenticao_ativa',return_value=True), \
             patch('sisreg_login.desafio_visivel',return_value=False), \
             patch('sisreg_login.consultar_solicitacao_hospitalar',side_effect=RuntimeError('Falha ficticia')), \
             patch('sisreg_login.Aplicativo._esperar_intervencao',return_value=False):
            app._navegador_worker('operador-ficticio','segredo-ficticio','chrome')
        ev=[]
        while not app.eventos.empty():ev.append(app.eventos.get_nowait()[0])
        self.assertIn('hospital_pausa',ev)
        self.assertNotIn('hospital_suspenso',ev)
        self.assertNotIn('verificacao_pendente',ev)
        self.assertNotIn('hospital_fim',ev)
        self.assertLess(ev.index('hospital_pausa'),ev.index('navegador_parou'))
        self.assertNotIn('segredo-ficticio',str(ev))

    def test_cadastro_inconclusivo_nao_alega_inexistencia(self):
        reg=SimpleNamespace(situacao='PENDENTE_FICHA_CADASTRO_NAO_IDENTIFICADA',situacao_anterior='',cpf='52998224725',cns='')
        situacao=situacao_final(reg)
        self.assertEqual(situacao,'Cadastro não confirmado no SISREG — revisar')
        self.assertIn('NÃO comprovou inexistência',orientacao_fiscal(situacao))

    def test_aih_nao_confirmada_requer_consulta_humana(self):
        reg=SimpleNamespace(situacao='PENDENTE_AIH_NAO_COMPROVADA_FICHA',situacao_anterior='',cpf='52998224725',cns='700000000000001')
        situacao=situacao_final(reg)
        self.assertEqual(situacao,'AIH não confirmada na consulta — revisar')
        self.assertIn('Não equivale a AIH inexistente',orientacao_fiscal(situacao))

if __name__=='__main__':unittest.main()
