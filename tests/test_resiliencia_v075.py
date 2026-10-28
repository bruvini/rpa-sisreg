"""Testes sintéticos de retomada, sessão degradada e continuidade."""
import sys, unittest, queue
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from retomada import candidato_cadastro, selecionar_cadastros, SaudeLote
from saida_xlsx import situacao_final
from app_info import APP_VERSION
CPF='52998224725'
CNS='700000000000001'
def r(**kw):
    d=dict(cpf=CPF,cns='',aih='9000000000123',nome='PACIENTE FICTICIO',
           situacao='DOCUMENTO_PDF_LOCALIZADO',situacao_anterior='')
    d.update(kw)
    return SimpleNamespace(**d)
class TesteRetomada(unittest.TestCase):
    def test_versao(self):self.assertEqual(APP_VERSION,'0.7.5')
    def test_cns_existente(self):self.assertFalse(candidato_cadastro(r(cns=CNS)))
    def test_nao_consultado(self):self.assertTrue(candidato_cadastro(r(situacao_anterior='Aguardando consulta SISREG')))
    def test_timeout(self):self.assertTrue(candidato_cadastro(r(situacao_anterior='Consulta não concluída — revisão necessária')))
    def test_nao_repesquisar_revisao(self):
        self.assertFalse(candidato_cadastro(r(situacao_anterior='Não encontrado na consulta SISREG')))
        self.assertFalse(candidato_cadastro(r(situacao_anterior='Dados divergentes na consulta SISREG')))
    def test_mesma_sessao(self):
        self.assertFalse(candidato_cadastro(r(situacao='PENDENTE_NOME_NAO_CONFIRMADO_RESULTADO')))
        self.assertTrue(candidato_cadastro(r(situacao='PENDENTE_FALHA_DE_NAVEGACAO_OU_TEMPO')))
    def test_conflito_pdf(self):self.assertFalse(candidato_cadastro(r(situacao='CPF_CONFLITANTE_PDF')))
    def test_ordem_retomada(self):
        self.assertEqual(selecionar_cadastros([r(cns=CNS),r(situacao_anterior='Não encontrado na consulta SISREG'),
            r(situacao_anterior='Aguardando consulta SISREG')]),([2],1))
    def test_quatro_inconclusivos(self):
        s=SaudeLote()
        self.assertEqual([s.registrar(None,erro_tecnico=False) for _ in range(4)],
                         ['PENDENCIA_IDENTIDADE']*3+['SUSPENDER_IDENTIDADE'])
    def test_tres_falhas(self):
        s=SaudeLote()
        self.assertEqual([s.registrar(None,erro_tecnico=True) for _ in range(3)],
                         ['PENDENCIA_TECNICA']*2+['SUSPENDER_ERRO'])
    def test_sucesso_recupera(self):
        s=SaudeLote();s.registrar(None,erro_tecnico=False);s.registrar(CNS,erro_tecnico=False)
        self.assertEqual(s.registrar(None,erro_tecnico=False),'PENDENCIA_IDENTIDADE')
    def test_humanizado_persiste(self):
        self.assertEqual(situacao_final(r(situacao_anterior='Não encontrado na consulta SISREG')),
                         'Não encontrado na consulta SISREG')
    def test_autocontinuacao_estatico(self):
        source=(ROOT/'src'/'sisreg_login.py').read_text()
        self.assertIn('self.root.after(250, self._iniciar_hospital)',source)
        self.assertIn('self.root.after(200, self._iniciar_hospital)',source)
class TesteSuspensaoBrowser(unittest.TestCase):
    def test_identidade_em_serie_nao_grava_falsa_pendencia(self):
        from sisreg_login import Aplicativo
        class Stop:
            def is_set(self):return False
            def wait(self,t):return False
        class Page:
            url='https://sisregiii.saude.gov.br/cgi-bin/index'
            def is_closed(self):return False
            def goto(self,*a,**kw):pass
        class Context:
            def __init__(self):self.pages=[]
            def new_page(self):
                p=Page();self.pages.append(p);return p
        class Browser:
            def __init__(self):self.context=Context()
            def new_context(self,**kw):return self.context
            def is_connected(self):return True
            def close(self):pass
        class PW:
            def __enter__(self):return SimpleNamespace(chromium=SimpleNamespace(launch=lambda **kw:Browser()))
            def __exit__(self,*args):pass
        app=Aplicativo.__new__(Aplicativo)
        app.parar=Stop();app.pausa=Stop();app.eventos=queue.Queue();app.comandos=queue.Queue()
        app.comandos.put(('lote',list(range(4))))
        app.sessao=SimpleNamespace(registros=[r() for _ in range(4)])
        with patch('sisreg_login.sync_playwright',return_value=PW()),\
             patch('sisreg_login.submeter_login'),\
             patch('sisreg_login.autenticao_ativa',return_value=True),\
             patch('sisreg_login.consultar_cadastro'),\
             patch('sisreg_login.ler_cadastro_contexto',return_value=(None,'NOME_NAO_CONFIRMADO_RESULTADO')):
            app._navegador_worker('demo','senha-ficticia','chrome')
        events=[]
        while not app.eventos.empty():events.append(app.eventos.get_nowait())
        self.assertNotIn('lote_item',[e[0] for e in events])
        self.assertIn('lote_alerta',[e[0] for e in events])
        self.assertIn('navegador_parou',[e[0] for e in events])
        self.assertNotIn('senha-ficticia',repr(events))
