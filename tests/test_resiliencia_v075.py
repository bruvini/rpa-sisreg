"""Testes inteiramente sintéticos para resiliência e retomada."""
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from retomada import candidato_cadastro, selecionar_cadastros, SaudeLote
from saida_xlsx import situacao_final
from planilha import SessaoPlanilha
from app_info import APP_VERSION

# Identificadores inventados para testes de fluxo; sem dados de pacientes.
CPF='52998224725'
CNS='700000000000001'

def r(**kw):
    d=dict(cpf=CPF,cns='',aih='9000000000123',nome='PACIENTE FICTICIO',
           situacao='DOCUMENTO_PDF_LOCALIZADO',situacao_anterior='')
    d.update(kw)
    return SimpleNamespace(**d)

class Retomada(unittest.TestCase):
    def test_versao(self): self.assertGreaterEqual(tuple(map(int,APP_VERSION.split('.'))),(0,7,5))
    def test_cns_existente_nao_reconsultado(self):
        self.assertFalse(candidato_cadastro(r(cns=CNS)))
    def test_pendente_ainda_nao_consultado(self):
        self.assertTrue(candidato_cadastro(r(situacao_anterior='Aguardando consulta SISREG')))
    def test_pendente_por_timeout_retentado(self):
        self.assertTrue(candidato_cadastro(r(situacao_anterior='Consulta não concluída — revisão necessária')))
    def test_revisao_humana_nao_reconsultada_automaticamente(self):
        self.assertFalse(candidato_cadastro(r(situacao_anterior='Dados divergentes na consulta SISREG')))
        self.assertFalse(candidato_cadastro(r(situacao_anterior='Não encontrado na consulta SISREG')))
    def test_reautenticacao_preserva_pendencia_humana_do_mesmo_lote(self):
        self.assertFalse(candidato_cadastro(r(situacao='PENDENTE_NOME_NAO_CONFIRMADO_RESULTADO')))
        self.assertTrue(candidato_cadastro(r(situacao='PENDENTE_FALHA_DE_NAVEGACAO_OU_TEMPO')))
    def test_conflito_pdf_excluido(self):
        self.assertFalse(candidato_cadastro(r(situacao='CPF_CONFLITANTE_PDF')))
    def test_prioriza_pendentes_preserva_ordem(self):
        registros=[r(cns=CNS),r(situacao_anterior='Não encontrado na consulta SISREG'),
                   r(situacao_anterior='Aguardando consulta SISREG'),r(situacao_anterior='Consulta não concluída — revisão necessária')]
        self.assertEqual(selecionar_cadastros(registros),([2,3],1))
    def test_suspende_antes_de_marcar_quarta_identidade_como_ausente(self):
        saude=SaudeLote()
        self.assertEqual([saude.registrar(None,erro_tecnico=False) for _ in range(4)],
            ['PENDENCIA_IDENTIDADE']*3+['SUSPENDER_IDENTIDADE'])
    def test_erro_tecnico_consecutivo_suspende(self):
        saude=SaudeLote()
        self.assertEqual([saude.registrar(None,erro_tecnico=True) for _ in range(3)],
            ['PENDENCIA_TECNICA']*2+['SUSPENDER_ERRO'])
    def test_sucesso_zera_degradacao(self):
        s=SaudeLote()
        s.registrar(None,erro_tecnico=False)
        s.registrar(CNS,erro_tecnico=False)
        self.assertEqual(s.registrar(None,erro_tecnico=False),'PENDENCIA_IDENTIDADE')
    def test_arquivo_reimportado_preserva_situacao_de_revisao(self):
        reg=r(situacao_anterior='Não encontrado na consulta SISREG')
        self.assertEqual(situacao_final(reg),'Cadastro não confirmado no SISREG — revisar')
    def test_codigo_nao_grava_identificadores_em_metadados(self):
        import retomada
        self.assertNotIn('localStorage',Path(retomada.__file__).read_text(encoding='utf-8'))
    def test_etapa_hospitalar_automatica_apos_conclusao(self):
        s=(ROOT/'src'/'sisreg_login.py').read_text(encoding='utf-8')
        self.assertIn('self.root.after(250, self._iniciar_hospital)',s)
        self.assertIn('self.root.after(200, self._iniciar_hospital)',s)

if __name__=='__main__':unittest.main()

class TesteLoteComNavegacaoInconsistente(unittest.TestCase):
    def test_quatro_identidades_inconclusivas_nao_viram_pendencias_falsas(self):
        import queue
        from unittest.mock import patch
        from sisreg_login import Aplicativo
        class Stop:
            def is_set(self): return False
            def wait(self, t): return False
        class Page:
            url='https://sisregiii.saude.gov.br/cgi-bin/index'
            def is_closed(self): return False
            def goto(self,*args,**kwargs): pass
        class Context:
            def __init__(self): self.pages=[]
            def new_page(self):
                page=Page();self.pages.append(page);return page
        class Browser:
            def __init__(self):self.context=Context()
            def new_context(self,**kwargs):return self.context
            def is_connected(self):return True
            def close(self):pass
        class Playwright:
            def __enter__(self):
                from types import SimpleNamespace
                return SimpleNamespace(chromium=SimpleNamespace(launch=lambda **kw: Browser()))
            def __exit__(self,*args):pass
        app=Aplicativo.__new__(Aplicativo)
        app.parar=Stop()
        app.pausa=Stop()
        from threading import Event
        from controle_sessao import AguardarHumano
        app.reiniciar_navegador=Event()
        app.aguardar_humano=AguardarHumano()
        app.eventos=queue.Queue()
        app.comandos=queue.Queue()
        app.comandos.put(('lote',list(range(4))))
        app.sessao=type('Session', (), {'registros':[r() for _ in range(4)]})()
        with patch('sisreg_login.Aplicativo._esperar_intervencao',return_value=False), \
             patch('sisreg_login.sync_playwright',return_value=Playwright()), \
             patch('sisreg_login.submeter_login'), \
             patch('sisreg_login.autenticao_ativa',return_value=True), \
             patch('sisreg_login.consultar_cadastro'), \
             patch('sisreg_login.ler_cadastro_contexto',return_value=(None,'NOME_NAO_CONFIRMADO_RESULTADO')):
            app._navegador_worker('demo','senha-ficticia','chrome')
        eventos=[]
        while not app.eventos.empty():eventos.append(app.eventos.get_nowait())
        self.assertNotIn('lote_item',[e[0] for e in eventos])
        self.assertIn('lote_alerta',[e[0] for e in eventos])
        self.assertIn('navegador_parou',[e[0] for e in eventos])
        self.assertNotIn('senha-ficticia',repr(eventos))
