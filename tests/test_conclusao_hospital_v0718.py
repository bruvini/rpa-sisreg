"""Regressões de conclusão e retomada com registros inteiramente fictícios."""
import os
import queue
import sys
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from sisreg_login import Aplicativo
from planilha import Registro
from governanca import HistoricoExecucao
from sisreg_hospital import ResultadoHospital


@unittest.skipUnless(os.environ.get('SISREG_GUI_TEST')=='1','Requer ambiente gráfico')
class TesteConclusao(unittest.TestCase):
    def setUp(self):
        import tkinter as tk
        self.root=tk.Tk();self.root.withdraw()
        self.app=Aplicativo(self.root)
        self.app.abas.tab(1,state='normal');self.app.abas.tab(2,state='normal')
        self.app.abas.select(2);self.app.preparo_concluido=True
        self.app.cadastro_concluido=True;self.app.processando=False
        self.app.sessao.origem=Path('modelo-ficticio.xlsx')
        self.app.inicio_ciclo=time.perf_counter()-2
        for etapa in ('preparo','cadastro','hospital'):
            self.app.estatisticas.concluir(etapa,1,consultados=0,encontrados=0)

    def tearDown(self):
        self.root.destroy()

    def test_resumo_com_codigos_textuais_e_totais_acumulados(self):
        r=Registro('PT6',2,'PACIENTE FICTICIO','9000000000123','0408050063',
                   '11144477735','700000000000001','10','670478410')
        r.consulta_hospitalar='FICHA_CONFERIDA';r.situacao='DADOS_COLETADOS_SEM_DIVERGENCIA'
        self.app.sessao.registros=[r]
        self.app.consultas_hospital_execucao=191;self.app.acertos_hospital_execucao=85
        self.app.erros_hospital_execucao=1
        self.app.estatisticas.registrar_total('hospital',11)
        self.app.estatisticas.concluir('hospital',1,consultados=11,encontrados=11)
        with tempfile.TemporaryDirectory() as pasta:
            pasta=Path(pasta)
            self.app.historico=HistoricoExecucao(pasta=pasta)
            with patch('sisreg_login.pastas_de_saida',return_value=(pasta,pasta)):
                self.app._finalizar_relatorio_seguro()
            texto=self.app.resultado_geral.get()
            self.assertIn('191',texto);self.assertIn('Último lote: 11/11',texto)
            self.assertEqual(self.app.abas.tab(3,'state'),'normal')
            self.assertEqual(str(self.app.btn_proxima.cget('state')),'normal')
            self.app._proxima_etapa()
            self.assertEqual(self.app.abas.index(self.app.abas.select()),3)
            relatorio=next(pasta.glob('RELATORIO_TECNICO_RPA_*.txt')).read_text(encoding='utf-8')
            self.assertIn('Acumulado na execução: consultas: 191',relatorio)
            self.assertNotIn('PACIENTE FICTICIO',relatorio)

    def test_falha_no_resumo_nao_interrompe_sessao_ou_bloqueia_resultados(self):
        self.app._finalizar_relatorio=Mock(side_effect=TypeError('fictício'))
        self.app.navegacao_falhou=False
        self.app._finalizar_relatorio_seguro()
        self.assertFalse(self.app.navegacao_falhou)
        self.assertFalse(self.app.parar.is_set())
        self.assertEqual(self.app.abas.tab(3,'state'),'normal')
        self.assertIn('coleta foi concluída',self.app.resultado_geral.get())

    def test_evento_final_apos_retomada_abre_etapa_4(self):
        r=Registro('PT6',2,'PACIENTE FICTICIO','9000000000123','0408050063',
                   '11144477735','700000000000001','10','670478410')
        r.consulta_hospitalar='FICHA_CONFERIDA';r.situacao='DADOS_COLETADOS_SEM_DIVERGENCIA'
        self.app.sessao.registros=[r];self.app.consultas_hospital_execucao=191
        self.app.acertos_hospital_execucao=85;self.app.erros_hospital_execucao=1
        self.app.tentativas_hospital=11;self.app.acertos_hospital=11
        self.app.inicio_hospital=time.perf_counter()-1
        self.app.estatisticas.registrar_total('hospital',11)
        self.app.processando=True;self.app._salvar_checkpoint=Mock(return_value=True)
        self.app.eventos=queue.Queue();self.app.eventos.put(('hospital_fim',11))
        with tempfile.TemporaryDirectory() as pasta:
            pasta=Path(pasta);self.app.historico=HistoricoExecucao(pasta=pasta)
            with patch('sisreg_login.pastas_de_saida',return_value=(pasta,pasta)):
                self.app._ler_eventos()
            self.assertEqual(self.app.abas.tab(3,'state'),'normal')
            self.assertEqual(str(self.app.btn_proxima.cget('state')),'normal')
            self.assertFalse(self.app.navegacao_falhou)
            self.assertFalse(self.app.parar.is_set())
            self.assertIn('191',self.app.resultado_geral.get())
            self.assertIn('Último lote: 11/11',self.app.resultado_geral.get())

    def test_autenticacao_reconsulta_nao_refaz_cadastro(self):
        self.app.eventos=queue.Queue()
        self.app._hospital_apos_login=[0]
        self.app._iniciar_hospital=Mock();self.app._iniciar_lote=Mock()
        self.app.eventos.put(('autenticado',None))
        self.app._ler_eventos()
        self.app._iniciar_hospital.assert_called_once_with([0])
        self.app._iniciar_lote.assert_not_called()
        self.assertIsNone(self.app._hospital_apos_login)

    def test_reconsulta_sem_navegador_pede_login_e_preserva_selecao(self):
        r=Registro('PT6',2,'PACIENTE FICTICIO','9000000000123','0408050063',
                   '11144477735','700000000000001','','')
        r.situacao_anterior='AIH não encontrada após pesquisar todas as páginas — revisar'
        self.app.sessao.registros=[r];self.app._atualizar_tabela()
        self.app.filtro_hospital.set('AIHs não encontradas');self.app._aplicar_filtro_hospital()
        self.app.tabela_hospital.selection_set('0')
        self.app.thread_navegador=None;self.app.browser_ready=False
        self.app._repetir_hospital_selecionados()
        self.assertEqual(self.app._hospital_apos_login,[0])
        self.assertEqual(self.app.abas.index(self.app.abas.select()),1)
        self.assertTrue(self.app.cadastro_concluido)

    def test_falha_em_reconsulta_preserva_divergencia_confirmada(self):
        r=Registro('PT6',2,'PACIENTE FICTICIO','9000000000123','0408050063',
                   '11144477735','700000000000001','10','670478410')
        r.consulta_hospitalar='PROCEDIMENTO_DIVERGENTE';r.procedimento_sisreg='0408050064'
        r.situacao='PENDENTE_PROCEDIMENTO_DIVERGENTE';r.solicitacao='670478410'
        self.app.sessao.registros=[r];self.app._indices_concluidos_reconsulta={0}
        self.app.hospital_previstos=1;self.app.inicio_hospital=time.perf_counter()
        self.app.eventos=queue.Queue()
        self.app.eventos.put(('hospital_item',(0,ResultadoHospital('FALHA_NAVEGACAO'),1.0,1,1)))
        self.app._ler_eventos()
        self.assertEqual(r.consulta_hospitalar,'PROCEDIMENTO_DIVERGENTE')
        self.assertEqual(r.procedimento_sisreg,'0408050064')
        self.assertEqual(r.solicitacao,'670478410')
        self.assertEqual(self.app.consultas_hospital_execucao,1)
        self.assertEqual(self.app.acertos_hospital_execucao,0)
        self.assertIn('resultado anterior foi preservado',self.app.status.get())

    def test_reconsulta_apos_relatorio_inicia_historico_proprio(self):
        r=Registro('PT6',2,'PACIENTE FICTICIO','9000000000123','0408050063',
                   '11144477735','700000000000001','10','670478410')
        r.situacao_anterior='Procedimento divergente — revisão fiscal';r.comparacao_anterior='Divergente'
        self.app.sessao.registros=[r];self.app.sessao.hash_planilha='a'*64
        self.app.thread_navegador=SimpleNamespace(is_alive=lambda:True);self.app.browser_ready=True
        self.app.relatorio_finalizado=True;self.app.comandos=queue.Queue()
        self.app.consultas_hospital_execucao=191
        with tempfile.TemporaryDirectory() as pasta:
            pasta=Path(pasta)
            with patch('sisreg_login.pastas_de_saida',return_value=(pasta,pasta)):
                self.app._iniciar_hospital([0])
            comando,payload=self.app.comandos.get_nowait()
            self.assertEqual(comando,'hospital');self.assertEqual(payload['indices'],[0])
            self.assertEqual(self.app.consultas_hospital_execucao,0)
            self.assertIsNotNone(self.app.historico)
            self.assertFalse(self.app.relatorio_finalizado)
            self.assertIn(0,self.app._indices_concluidos_reconsulta)

    def test_filtros_padrao_e_grupos_de_revisao(self):
        def registro(n):
            return Registro('PT6',n,'PACIENTE FICTICIO','9000000000123','0408050063',
                            '11144477735','700000000000001','','')
        aguardando,erro,nao_encontrada,divergente,concluida=[registro(i) for i in range(2,7)]
        erro.consulta_hospitalar='FALHA_NAVEGACAO'
        nao_encontrada.consulta_hospitalar='AIH_NAO_LOCALIZADA_PAGINAS'
        divergente.consulta_hospitalar='PROCEDIMENTO_DIVERGENTE'
        concluida.consulta_hospitalar='FICHA_CONFERIDA'
        self.app.sessao.registros=[aguardando,erro,nao_encontrada,divergente,concluida]
        self.app._atualizar_tabela()
        self.assertEqual(set(self.app.tabela_hospital.get_children()),{'0','1'})
        self.app.filtro_hospital.set('AIHs não encontradas');self.app._aplicar_filtro_hospital()
        self.assertEqual(self.app.tabela_hospital.get_children(),('2',))
        self.app.filtro_hospital.set('Divergências');self.app._aplicar_filtro_hospital()
        self.assertEqual(self.app.tabela_hospital.get_children(),('3',))
