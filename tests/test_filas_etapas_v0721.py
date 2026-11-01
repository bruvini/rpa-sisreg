"""Filas e transição automática de abas, sem SISREG nem dados reais."""
import os
import queue
import sys
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from planilha import Registro
from sisreg_login import Aplicativo
from sisreg_hospital import ResultadoHospital


def registro(**campos):
    valores=dict(aba='PT6',linha=2,nome='PACIENTE FICTICIO',aih='9000000000123',
                 procedimento='0408050063',cpf='11144477735',cns='',carater='',autorizador='')
    valores.update(campos)
    return Registro(**valores)


@unittest.skipUnless(os.environ.get('SISREG_GUI_TEST')=='1','Requer ambiente gráfico')
class TesteFilasEtapas(unittest.TestCase):
    def setUp(self):
        import tkinter as tk
        self.root=tk.Tk();self.root.withdraw();self.app=Aplicativo(self.root)
        self.app.abas.tab(1,state='normal');self.app.abas.tab(2,state='normal')
        self.app.preparo_concluido=self.app.cadastro_concluido=True

    def tearDown(self):
        for identificador in self.root.tk.call('after','info'):
            self.root.after_cancel(identificador)
        self.root.destroy()

    def executar_transicao_agendada(self,acao,atraso):
        # Executa o callback real sem bombear timers de outras instâncias Tk
        # destruídas pelos testes que precedem esta classe na suíte completa.
        with patch.object(self.root,'after') as agendar:
            acao()
        chamadas=[c for c in agendar.call_args_list if c.args[0]==atraso]
        self.assertEqual(len(chamadas),1)
        chamadas[0].args[1]()

    def test_planilha_reaberta_separa_as_tres_filas(self):
        sem_cpf=registro(cpf='',cpf_origem='')
        sem_cns=registro(cpf_origem='11144477735')
        pendente=registro(cpf_origem='11144477735',cns='700000000000001',cns_origem='700000000000001')
        completa=registro(cpf_origem='11144477735',cns='700000000000001',cns_origem='700000000000001',
            carater='10',autorizador='670478410',situacao_anterior='Compatível por troca aprovada',
            comparacao_anterior='Compatível por troca aprovada',consulta_hospitalar='FICHA_CONFERIDA')
        divergente=registro(cpf_origem='11144477735',cns='700000000000001',cns_origem='700000000000001',
            carater='10',autorizador='670478410',situacao_anterior='Procedimento divergente — revisão fiscal',
            comparacao_anterior='Divergente',consulta_hospitalar='PROCEDIMENTO_DIVERGENTE')
        sem_cns_divergente=registro(cpf_origem='11144477735',situacao_anterior='Dados divergentes na consulta SISREG')
        self.app.sessao.registros=[sem_cpf,sem_cns,pendente,completa,divergente,sem_cns_divergente]
        self.app._atualizar_tabela()
        self.assertEqual(self.app.tabela.get_children(),('0',))
        self.assertEqual(set(self.app.tabela_cns.get_children()),{'1','5'})
        self.assertEqual(self.app.tabela_hospital.get_children(),('2',))
        self.app.filtro_hospital.set('Divergências');self.app._aplicar_filtro_hospital()
        self.assertEqual(self.app.tabela_hospital.get_children(),('4',))
        self.app.filtro_hospital.set('Todos');self.app._aplicar_filtro_hospital()
        self.assertEqual(set(self.app.tabela_hospital.get_children()),{'2','4'})

    def test_cns_obtido_no_pdf_nao_entra_na_etapa_2(self):
        r=registro(cpf_origem='',cns='700000000000001',cns_origem='')
        self.app.sessao.registros=[r];self.app._atualizar_tabela()
        self.assertEqual(self.app.tabela.get_children(),('0',))
        self.assertEqual(self.app.tabela_cns.get_children(),())
        self.assertEqual(self.app.tabela_hospital.get_children(),('0',))

    def test_resultado_hospitalar_nao_reinsere_linhas_nas_etapas_anteriores(self):
        r=registro(cpf_origem='11144477735',cns='700000000000001',cns_origem='700000000000001')
        self.app.sessao.registros=[r];self.app._atualizar_tabela()
        self.app.hospital_previstos=1;self.app.inicio_hospital=time.perf_counter()
        self.app.eventos=queue.Queue()
        resultado=ResultadoHospital('FICHA_CONFERIDA','Ficha sintética','10','','0408050063','670478410')
        self.app.eventos.put(('hospital_item',(0,resultado,1,1,1)))
        self.app._ler_eventos()
        self.assertEqual(self.app.tabela.get_children(),())
        self.assertEqual(self.app.tabela_cns.get_children(),())
        self.assertEqual(self.app.acertos_hospital_execucao,1)
        self.assertIn('Sem divergência',self.app.progresso_hospital.get())

    def test_resultado_cadastro_fica_na_etapa_2_sem_inserir_na_etapa_1(self):
        r=registro(cpf_origem='11144477735')
        self.app.sessao.registros=[r];self.app._atualizar_tabela()
        self.app.inicio_cadastro=time.perf_counter();self.app.cns_aproveitados=0;self.app.cns_previstos=1
        self.app.eventos=queue.Queue()
        self.app.eventos.put(('lote_item',(0,'700000000000001','CNS_CONFIRMADO_SISREG',1,1)))
        self.app._ler_eventos()
        self.assertEqual(self.app.tabela.get_children(),())
        self.assertEqual(self.app.tabela_cns.get_children(),('0',))
        self.assertEqual(r.cns,'700000000000001')

    def test_inicio_hospitalar_seleciona_aba_3(self):
        self.app.sessao.registros=[registro(cns='700000000000001')]
        self.app.thread_navegador=SimpleNamespace(is_alive=lambda:True)
        self.app.browser_ready=True;self.app.comandos=queue.Queue()
        self.app.abas.select(1)
        self.app._iniciar_hospital()
        self.assertEqual(self.app.abas.index(self.app.abas.select()),2)
        self.assertTrue(self.app.processando)
        self.assertEqual(self.app.comandos.get_nowait()[0],'hospital')

    def test_conclusao_cadastro_aciona_transicao_para_hospital(self):
        self.app.sessao.registros=[registro(cns='700000000000001')]
        self.app.thread_navegador=SimpleNamespace(is_alive=lambda:True)
        self.app.browser_ready=True;self.app.comandos=queue.Queue()
        self.app.inicio_cadastro=time.perf_counter();self.app.processando=True
        self.app._salvar_checkpoint=Mock(return_value=True)
        self.app.eventos=queue.Queue();self.app.eventos.put(('lote_fim',(1,1)))
        self.app.abas.select(1)
        self.executar_transicao_agendada(self.app._ler_eventos,250)
        self.assertEqual(self.app.abas.index(self.app.abas.select()),2)
        self.assertEqual(self.app.comandos.get_nowait()[0],'hospital')

    def test_sem_consultas_de_cadastro_tambem_abre_etapa_3(self):
        self.app.sessao.registros=[registro(cns='700000000000001')]
        self.app.sessao.origem=Path('ficticio.xlsx')
        self.app.thread_navegador=SimpleNamespace(is_alive=lambda:True)
        self.app.browser_ready=True;self.app.comandos=queue.Queue()
        self.app.abas.select(1)
        self.executar_transicao_agendada(self.app._iniciar_lote,200)
        self.assertEqual(self.app.abas.index(self.app.abas.select()),2)

    def test_sobre_descreve_trocas_filas_e_limites_do_captcha(self):
        import tkinter as tk
        self.app._sobre()
        textos=[]
        def ler(w):
            if isinstance(w,(tk.Label,)) or w.winfo_class()=='TLabel': textos.append(str(w.cget('text')))
            for filho in w.winfo_children():ler(filho)
        ler(self.root)
        texto=' '.join(textos)
        for trecho in ('validação operacional assistida','Troca de Procedimentos','sem exibir o desafio','ainda sem CNS'):
            self.assertIn(trecho,texto)
