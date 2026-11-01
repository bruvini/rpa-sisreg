"""Comportamento da retomada sem acesso a pacientes ou ao SISREG real."""
import sys
import queue
import multiprocessing
import os
import time
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from controle_sessao import desafio_visivel
from sisreg_hospital import ResultadoHospital
from sisreg_login import Aplicativo, consultar_hospital_com_retentativa, _executar_navegador_isolado
from sisreg_navigation import NavegacaoInesperada
from estatisticas import Estatisticas

class PaginaFicticia:
    url='https://sisregiii.saude.gov.br/cgi-bin/index'
    def is_closed(self): return False
    def goto(self,*args,**kwargs): pass

class BrowserFicticio:
    def __init__(self):
        p=PaginaFicticia();self.context=SimpleNamespace(pages=[p],new_page=lambda:p)
    def new_context(self,**kwargs): return self.context
    def is_connected(self): return True
    def close(self): pass

class PlaywrightFicticio:
    def __enter__(self):
        return SimpleNamespace(chromium=SimpleNamespace(launch=lambda **kw:BrowserFicticio()))
    def __exit__(self,*args): pass

def processo_ficticio(eventos,comandos,parar,pausa,reiniciar,confirmacao):
    with patch('sisreg_login.sync_playwright',return_value=PlaywrightFicticio()), \
         patch('sisreg_login.submeter_login'), \
         patch('sisreg_login.autenticao_ativa',return_value=True), \
         patch('sisreg_login.desafio_visivel',return_value=False), \
         patch('sisreg_login.servidor_indisponivel',return_value=False), \
         patch('sisreg_login.consultar_solicitacao_hospitalar',
               return_value=ResultadoHospital('FICHA_CONFERIDA')):
        _executar_navegador_isolado(eventos,comandos,parar,pausa,reiniciar,
                                    confirmacao,'usuario-ficticio','senha-ficticia','chrome')

def processo_com_captcha(eventos,comandos,parar,pausa,reiniciar,confirmacao,estado):
    def consultar(p,cns,aih,proc,**kwargs):
        if aih=='9000000000999' and estado.value==0:
            estado.value=1
        return ResultadoHospital('FICHA_CONFERIDA')
    with patch('sisreg_login.sync_playwright',return_value=PlaywrightFicticio()), \
         patch('sisreg_login.submeter_login'), \
         patch('sisreg_login.autenticao_ativa',return_value=True), \
         patch('sisreg_login.desafio_visivel',side_effect=lambda contexto:estado.value==1), \
         patch('sisreg_login.servidor_indisponivel',return_value=False), \
         patch('sisreg_login.consultar_solicitacao_hospitalar',side_effect=consultar):
        _executar_navegador_isolado(eventos,comandos,parar,pausa,reiniciar,
                                    confirmacao,'usuario-ficticio','senha-ficticia','chrome')

class TesteRetomada(unittest.TestCase):
    def setUp(self):
        self.r=SimpleNamespace(cns='700000000000001',aih='9000000000123',procedimento='0408050063')
        self.parar=Mock(spec=threading.Event)
        self.parar.is_set.return_value=False
        self.parar.wait.return_value=False

    @patch('sisreg_login.servidor_indisponivel',return_value=False)
    @patch('sisreg_login.desafio_visivel',return_value=False)
    @patch('sisreg_login.consultar_solicitacao_hospitalar')
    def test_uma_nova_tentativa_e_resultado_preservado(self,consulta,desafio,servidor):
        consulta.side_effect=[NavegacaoInesperada('erro fictício'),ResultadoHospital('FICHA_CONFERIDA')]
        with patch('sisreg_login.autenticao_ativa',return_value=True):
            r=consultar_hospital_com_retentativa(Mock(),self.r,Mock(),self.parar,Mock())
        self.assertEqual(r.situacao,'FICHA_CONFERIDA')
        self.assertEqual(consulta.call_count,2)

    @patch('sisreg_login.servidor_indisponivel',return_value=False)
    @patch('sisreg_login.desafio_visivel',return_value=True)
    @patch('sisreg_login.consultar_solicitacao_hospitalar')
    def test_captcha_impede_nova_pesquisa(self,consulta,desafio,servidor):
        with self.assertRaises(NavegacaoInesperada):
            consultar_hospital_com_retentativa(Mock(),self.r,Mock(),self.parar,Mock())
        consulta.assert_not_called()

    @patch('sisreg_login.servidor_indisponivel',return_value=False)
    @patch('sisreg_login.desafio_visivel',return_value=False)
    @patch('sisreg_login.consultar_solicitacao_hospitalar')
    def test_aih_nao_localizada_nao_tem_nova_tentativa(self,consulta,desafio,servidor):
        consulta.return_value=ResultadoHospital('AIH_NAO_LOCALIZADA_PAGINAS')
        consultar_hospital_com_retentativa(Mock(),self.r,Mock(),self.parar,Mock())
        self.assertEqual(consulta.call_count,1)

    def test_captcha_em_frame_oficial(self):
        frame=SimpleNamespace(url='https://sisregiii.saude.gov.br/cgi-bin/cons_aih',
            locator=lambda _:SimpleNamespace(inner_text=lambda **kw:'CAPTCHA'))
        page=SimpleNamespace(url='https://sisregiii.saude.gov.br/cgi-bin/index',
            is_closed=lambda:False,frames=[frame])
        self.assertTrue(desafio_visivel(SimpleNamespace(pages=[page])))

    def test_filtros_preservam_aih_nao_encontrada(self):
        r=SimpleNamespace(consulta_hospitalar='',situacao='',
            situacao_anterior='AIH não encontrada após pesquisar todas as páginas — revisar')
        self.assertEqual(Aplicativo._grupo_hospital(r),'AIHs não encontradas')

    def test_pausa_tecnica_nao_interrompe_ciclo_da_interface(self):
        app=Aplicativo.__new__(Aplicativo)
        app.eventos=queue.Queue()
        app.eventos.put(('hospital_pausa_tecnica','Pausa fictícia'))
        app.status=Mock();app.estatisticas=Estatisticas();app.root=Mock()
        app.parar=threading.Event();app.navegacao_falhou=False
        app._ler_eventos()
        self.assertEqual(app.estatisticas.diagnosticos[-1]['acao'],'HOSPITAL_PAUSA_TECNICA')
        app.root.after.assert_called_once()
        self.assertFalse(app.parar.is_set())

    def test_saida_confirmada_atinge_apenas_processo_criado(self):
        app=Aplicativo.__new__(Aplicativo)
        app.parar=threading.Event();app.pausa=threading.Event()
        app.aguardar_humano=Mock();app.historico=None;app.root=Mock()
        app.thread_navegador=SimpleNamespace(is_alive=lambda:True,pid=12345,terminate=Mock())
        with patch('sisreg_login.sys.platform','win32'),patch('sisreg_login.subprocess.Popen') as executar:
            app._encerrar_confirmado_sem_relatorio()
        self.assertEqual(executar.call_args.args[0],['taskkill','/PID','12345','/T','/F'])
        app.root.destroy.assert_called_once()

    @unittest.skipUnless(sys.platform=='win32','Verifica a árvore de processos no Windows')
    def test_saida_forcada_encerra_processo_isolado_sem_resposta(self):
        ctx=multiprocessing.get_context('spawn')
        processo=ctx.Process(target=time.sleep,args=(30,));processo.start()
        app=Aplicativo.__new__(Aplicativo)
        app.parar=threading.Event();app.pausa=threading.Event()
        app.aguardar_humano=Mock();app.historico=None;app.root=Mock()
        app.thread_navegador=processo
        try:
            app._encerrar_confirmado_sem_relatorio()
            processo.join(10)
            app._processo_encerramento.wait(timeout=5)
            self.assertFalse(processo.is_alive())
            app.root.destroy.assert_called_once()
        finally:
            if processo.is_alive(): processo.terminate();processo.join(5)

    def test_resumo_usa_resultados_desta_execucao(self):
        app=Aplicativo.__new__(Aplicativo)
        app.historico=Mock();app.sessao=SimpleNamespace(registros=[SimpleNamespace(cns='123',situacao='')])
        app.consultas_hospital_execucao=182;app.acertos_hospital_execucao=72
        app.erros_hospital_execucao=7;app.dados_atuais={'falhas':0}
        app._resumir_historico()
        self.assertEqual(app.historico.atualizar.call_args.kwargs,
            {'cns_identificados':1,'consultas_hospitalares':182,
             'sem_divergencia_identificada':72,'pendencias':110,'erros_tecnicos':7})

    def test_comandos_atualizados_no_processo_isolado(self):
        ctx=multiprocessing.get_context('spawn')
        eventos=ctx.Queue();comandos=ctx.Queue()
        parar=ctx.Event();pausa=ctx.Event();reiniciar=ctx.Event();confirmacao=ctx.Event()
        proc=ctx.Process(target=processo_ficticio,args=(eventos,comandos,parar,pausa,reiniciar,confirmacao))
        proc.start()
        try:
            self.assertEqual(eventos.get(timeout=15)[0],'login_enviado')
            self.assertEqual(eventos.get(timeout=15)[0],'autenticado')
            comandos.put(('hospital',{'indices':[0],'registros':[self.r]}))
            vistos=[]
            while 'hospital_fim' not in vistos:
                nome,dado=eventos.get(timeout=15);vistos.append(nome)
            self.assertIn('hospital_item',vistos)
        finally:
            parar.set();proc.join(10)
            if proc.is_alive(): proc.terminate();proc.join(5)
        self.assertEqual(proc.exitcode,0)

    def test_captcha_retorna_indice_interrompido_sem_repetir_concluido(self):
        ctx=multiprocessing.get_context('spawn')
        eventos=ctx.Queue();comandos=ctx.Queue()
        parar=ctx.Event();pausa=ctx.Event();reiniciar=ctx.Event();confirmacao=ctx.Event()
        estado=ctx.Value('i',0)
        segundo=SimpleNamespace(cns=self.r.cns,aih='9000000000999',procedimento=self.r.procedimento)
        proc=ctx.Process(target=processo_com_captcha,args=(eventos,comandos,parar,pausa,reiniciar,confirmacao,estado))
        proc.start()
        try:
            while eventos.get(timeout=15)[0]!='autenticado': pass
            comandos.put(('hospital',{'indices':[0,1],'registros':[self.r,segundo]}))
            concluidos=[]
            while True:
                nome,dado=eventos.get(timeout=15)
                if nome=='hospital_item': concluidos.append(dado[0])
                if nome=='verificacao_pendente': break
            self.assertEqual(concluidos,[0])
            estado.value=2;confirmacao.set()
            while True:
                nome,dado=eventos.get(timeout=15)
                if nome=='sessao_recuperada': break
            self.assertEqual(dado,('hospital',[1]))
            comandos.put(('hospital',{'indices':dado[1],'registros':[self.r,segundo]}))
            while True:
                nome,dado=eventos.get(timeout=15)
                if nome=='hospital_item': concluidos.append(dado[0])
                if nome=='hospital_fim': break
            self.assertEqual(concluidos,[0,1])
        finally:
            parar.set();confirmacao.set();proc.join(10)
            if proc.is_alive(): proc.terminate();proc.join(5)
        self.assertEqual(proc.exitcode,0)

@unittest.skipUnless(os.environ.get('SISREG_GUI_TEST')=='1','Requer ambiente gráfico')
class TesteFiltrosInterface(unittest.TestCase):
    def test_filtrar_e_selecionar_pendencia_historica(self):
        import tkinter as tk
        from planilha import Registro
        root=tk.Tk();root.withdraw()
        try:
            app=Aplicativo(root)
            a=Registro('PT6',2,'PACIENTE FICTICIO','9000000000123','0408050063',
                       '11144477735','700000000000001','','')
            b=Registro('PT6',3,'PACIENTE FICTICIO','9000000000999','0408050063',
                       '11144477735','700000000000001','','')
            a.situacao_anterior='AIH não encontrada após pesquisar todas as páginas — revisar'
            b.situacao_anterior='Falha ou dados incompletos — repetir consulta'
            app.sessao.registros=[a,b]
            app._atualizar_tabela()
            app.filtro_hospital.set('AIHs não encontradas');app._aplicar_filtro_hospital()
            self.assertEqual(app.tabela_hospital.get_children(),('0',))
            app.tabela_hospital.selection_set('0');app._iniciar_hospital=Mock()
            app.thread_navegador=SimpleNamespace(is_alive=lambda:True);app.browser_ready=True
            app._repetir_hospital_selecionados()
            app._iniciar_hospital.assert_called_once_with([0])
            app.filtro_hospital.set('Todos');app._aplicar_filtro_hospital()
            self.assertEqual(set(app.tabela_hospital.get_children()),{'0','1'})
            a.consulta_hospitalar='FICHA_CONFERIDA'
            app.filtro_hospital.set('AIHs não encontradas');app._aplicar_filtro_hospital()
            self.assertEqual(app.tabela_hospital.get_children(),())
        finally:
            root.destroy()

    def test_encerramento_salva_sem_bloquear_loop(self):
        import time
        import tkinter as tk
        root=tk.Tk();root.withdraw()
        app=Aplicativo(root)
        app.preparo_concluido=True
        app.sessao.origem=Path('ficticio.xlsx')
        app.sessao.salvar_na_planilha=Mock(return_value={})
        app.encerrar()
        limite=time.monotonic()+5
        while time.monotonic()<limite:
            try:
                root.update()
                if not root.winfo_exists(): break
            except tk.TclError:
                break
            time.sleep(.02)
        else:
            root.destroy()
            self.fail('A janela não encerrou após o salvamento.')
        app.sessao.salvar_na_planilha.assert_called_once()

