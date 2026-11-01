"""Persistência e elegibilidade com dados fictícios, sem acesso ao SISREG."""
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from planilha import Registro, SessaoPlanilha
from saida_xlsx import comparacao_procedimento, situacao_final
from progresso import candidato_hospitalar, ficha_hospitalar_completa
from sisreg_hospital import ResultadoHospital, _extrair_trocas_aprovadas
from sisreg_login import Aplicativo


def registro():
    return Registro('PT6',2,'PACIENTE FICTICIO','9000000000123','0409040193',
                    '11144477735','700000000000001','','')


class TestePersistenciaTroca(unittest.TestCase):
    def salvar_e_reabrir(self,carater='',autorizador='',resultado=None):
        from openpyxl import load_workbook
        with tempfile.TemporaryDirectory() as pasta:
            caminho=Path(pasta)/'teste.xlsx'
            shutil.copy2(Path(__file__).parent/'fixtures'/'hospital_sintetico.xlsx',caminho)
            s=SessaoPlanilha();s.carregar(caminho);r=s.registros[0]
            wb=load_workbook(caminho);ws=wb[r.aba]
            for col,valor in ((3,'0409040193'),(5,'700000000000001'),(6,carater),(7,autorizador)):
                ws.cell(r.linha,col).value=valor or None
            wb.save(caminho);wb.close()
            s.carregar(caminho);r=s.registros[0]
            if resultado is None:
                resultado=ResultadoHospital('FICHA_CONFERIDA','Troca aprovada','10','','0409040193',
                    '670478410','0408050063','troca_aprovada')
            s.registrar_hospital(r,resultado,1.0)
            s.salvar_na_planilha(motivo='teste')
            wb=load_workbook(caminho);ws=wb[r.aba]
            gravados=(ws.cell(r.linha,8).value,ws.cell(r.linha,10).value)
            wb.close()
            nova=SessaoPlanilha();nova.carregar(caminho)
            return r,nova.registros[0],gravados

    def test_troca_aprovada_persiste_e_nao_repete_automaticamente(self):
        r,reaberto,gravados=self.salvar_e_reabrir()
        self.assertEqual(gravados,('Compatível por troca aprovada',)*2)
        self.assertEqual(r.procedimento_original,'0408050063')
        self.assertEqual(r.procedimento_sisreg,'0409040193')
        self.assertEqual(reaberto.origem_procedimento,'troca_aprovada')
        self.assertEqual(situacao_final(reaberto),'Compatível por troca aprovada')
        self.assertEqual(comparacao_procedimento(reaberto),'Compatível por troca aprovada')
        self.assertTrue(ficha_hospitalar_completa(reaberto))
        self.assertFalse(candidato_hospitalar(reaberto))

    def test_troca_compativel_preserva_conflitos_dos_outros_campos_ao_reabrir(self):
        for carater,autorizador in (('20','670478410'),('10','999999999')):
            with self.subTest(carater=carater):
                r,reaberto,gravados=self.salvar_e_reabrir(carater,autorizador)
                self.assertTrue(r.situacao.startswith('PENDENTE_'))
                self.assertEqual(gravados,('Dados divergentes no SISREG','Compatível por troca aprovada'))
                self.assertEqual(situacao_final(reaberto),'Dados divergentes no SISREG')
                self.assertEqual(Aplicativo._grupo_hospital(reaberto),'Divergências')

    def test_troca_ambigua_limpa_comparacao_anterior(self):
        r=registro();r.comparacao_anterior='Compatível por troca aprovada'
        SessaoPlanilha().registrar_hospital(r,ResultadoHospital('PROCEDIMENTO_NAO_CONFIRMADO_TROCAS'),1)
        self.assertEqual(comparacao_procedimento(r),'Não conferido')
        self.assertEqual(situacao_final(r),'Trocas de procedimento ambíguas — revisar')
        self.assertFalse(candidato_hospitalar(r))

    def test_aih_nao_confirmada_persiste_e_permite_apenas_revisao_selecionada(self):
        r,reaberto,gravados=self.salvar_e_reabrir(resultado=ResultadoHospital('AIH_NAO_COMPROVADA_RESULTADOS'))
        self.assertEqual(gravados[0],'AIH não confirmada — revisão necessária')
        self.assertEqual(Aplicativo._grupo_hospital(r),'AIHs não confirmadas')
        self.assertEqual(Aplicativo._grupo_hospital(reaberto),'AIHs não confirmadas')
        self.assertFalse(candidato_hospitalar(reaberto))
        self.assertEqual(Aplicativo.__new__(Aplicativo)._motivo_bloqueio_hospital(reaberto),'')

    def test_cabecalhos_ausentes_e_multiplos_codigos_na_celula_sao_ambiguos(self):
        titulo={'secao':True,'celulas':['Troca de Procedimentos']}
        fim={'secao':True,'celulas':['Observações gerais']}
        cab={'celulas':['CID','Procedimento','Solicitante','Status']}
        self.assertEqual(_extrair_trocas_aprovadas([titulo,{'celulas':['0409040193','Aprovada']},fim]),('',True))
        self.assertEqual(_extrair_trocas_aprovadas([titulo,cab,{'celulas':['CID','0409040193 e 0408050063','TESTE','Aprovada']},fim]),('',True))
        # A seção pode ser a última da ficha, sem delimitador posterior.
        self.assertEqual(_extrair_trocas_aprovadas([titulo,cab,{'celulas':['CID','0409040193','TESTE','Aprovada']}]),('0409040193',False))


@unittest.skipUnless(os.environ.get('SISREG_GUI_TEST')=='1','Requer ambiente gráfico')
class TesteSelecaoAptos(unittest.TestCase):
    def setUp(self):
        import tkinter as tk
        self.root=tk.Tk();self.root.withdraw()
        self.app=Aplicativo(self.root)

    def tearDown(self):
        self.root.destroy()

    def test_selecao_e_inicio_compartilham_regra_com_motivos_visiveis(self):
        registros=[registro() for _ in range(7)]
        for r in registros: r.consulta_hospitalar='PROCEDIMENTO_DIVERGENTE'
        registros[1].cns='';registros[2].cns='123'
        registros[3].aih='';registros[4].aih='123'
        registros[5].nome=' '
        self.app.sessao.registros=registros
        self.app.filtro_hospital.set('Divergências');self.app._atualizar_tabela()
        self.app._selecionar_filtro_hospital()
        self.assertEqual(set(self.app.tabela_hospital.selection()),{'0','6'})
        resumo=self.app.resumo_selecao.get()
        self.assertIn('2 de 7 registros selecionados',resumo)
        for motivo in ('CNS ausente','CNS inválido','AIH ausente','AIH inválida','Nome ausente'):
            self.assertIn(motivo+': 1',resumo)
        self.app.thread_navegador=SimpleNamespace(is_alive=lambda:True)
        self.app.browser_ready=True;self.app._iniciar_hospital=Mock()
        self.app._repetir_hospital_selecionados()
        self.app._iniciar_hospital.assert_called_once_with([0,6])
        # Mesmo uma seleção manual inválida não chega ao início da pesquisa.
        self.app.tabela_hospital.selection_set('0','1','2','3','4','5','6')
        self.app._repetir_hospital_selecionados()
        self.app._iniciar_hospital.assert_called_with([0,6])

    def test_inicio_real_tambem_descarta_selecao_inapta(self):
        import queue
        a,b=registro(),registro();b.cns='123'
        a.consulta_hospitalar=b.consulta_hospitalar='PROCEDIMENTO_DIVERGENTE'
        self.app.sessao.registros=[a,b]
        self.app.preparo_concluido=self.app.cadastro_concluido=True
        self.app.thread_navegador=SimpleNamespace(is_alive=lambda:True)
        self.app.browser_ready=True;self.app.comandos=queue.Queue()
        self.app._iniciar_hospital([0,1])
        comando,payload=self.app.comandos.get_nowait()
        self.assertEqual(comando,'hospital')
        self.assertEqual(payload['indices'],[0])
        self.assertEqual(self.app.hospital_previstos,1)

    def test_contagem_acompanha_filtro_selecao_manual_e_resultado_novo(self):
        a,b=registro(),registro()
        a.consulta_hospitalar='AIH_NAO_COMPROVADA_RESULTADOS'
        b.consulta_hospitalar='PROCEDIMENTO_DIVERGENTE'
        self.app.sessao.registros=[a,b];self.app._atualizar_tabela()
        self.app.filtro_hospital.set('AIHs não confirmadas');self.app._aplicar_filtro_hospital()
        self.app._selecionar_filtro_hospital()
        self.assertEqual(self.app.tabela_hospital.selection(),('0',))
        self.assertIn('1 de 1',self.app.resumo_selecao.get())
        self.app.filtro_hospital.set('Divergências');self.app._aplicar_filtro_hospital()
        self.assertIn('0 de 1',self.app.resumo_selecao.get())
        self.app.tabela_hospital.selection_set('1');self.root.update()
        self.assertIn('1 de 1',self.app.resumo_selecao.get())
        b.consulta_hospitalar='FICHA_CONFERIDA'
        self.app._aplicar_filtro_hospital()
        self.assertEqual(self.app.tabela_hospital.get_children(),())
        self.assertIn('0 de 0',self.app.resumo_selecao.get())
