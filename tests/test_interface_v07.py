"""Fluxo de interface da versão 0.7, somente com arquivos sintéticos."""
import os
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))

@unittest.skipUnless(os.getenv('SISREG_GUI_TEST')=='1','Requer Xvfb/display')
class TestesVisuais(unittest.TestCase):
    def setUp(self):
        import tkinter as tk
        from sisreg_login import Aplicativo
        self.tk=tk.Tk()
        self.app=Aplicativo(self.tk)
        self.tk.update()
    def tearDown(self):
        self.tk.destroy()
    def test_abas_e_tabela_hospitalar(self):
        a=self.app
        self.assertEqual(a.abas.index('end'),4)
        self.assertEqual(str(a.abas.tab(3,'state')),'disabled')
        cols=list(a.tabela_hospital['columns'])
        self.assertEqual(cols,['aih','paciente','cns','carater','procedimento','solicitacao','situacao'])
        self.assertTrue(a.resultado_geral.get().startswith('Aguardando'))
    def test_atualizacao_tabela_hospitalar_sem_inferir_solicitacao(self):
        from planilha import Registro
        a=self.app
        r=Registro(aba='PT6',linha=2,aih='9000000000123',nome='PACIENTE FICTICIO',procedimento='0408050063',
            cpf='11144477735',cns='900000000000001',carater='10',autorizador='00099')
        a.sessao.registros=[r]
        a._atualizar_linha_hospital(0)
        self.assertEqual(a.tabela_hospital.item('0','values')[5],'—')
        r.consulta_hospitalar='FICHA_CONFERIDA';r.procedimento_sisreg='0408050063';r.situacao='DADOS_COLETADOS_SEM_DIVERGENCIA'
        a._atualizar_linha_hospital(0)
        self.assertEqual(a.tabela_hospital.item('0','values')[5],'—')
        r.solicitacao='670478410';a._atualizar_linha_hospital(0)
        self.assertEqual(a.tabela_hospital.item('0','values')[5],'670478410')
    def test_tab_estatistica_somente_apos_finalizar(self):
        self.assertEqual(self.app.abas.tab(3,'state'),'disabled')

if __name__=='__main__':unittest.main()

@unittest.skipUnless(os.getenv('SISREG_GUI_TEST')=='1','Requer Xvfb/display')
class TesteFechamentoComLog(unittest.TestCase):
    def test_gera_log_ao_concluir_fases_sem_PII(self):
        import tempfile, shutil, time, tkinter as tk
        from sisreg_login import Aplicativo
        from governanca import HistoricoExecucao
        with tempfile.TemporaryDirectory() as d:
            pasta=Path(d)
            origem=Path(__file__).resolve().parent/'fixtures'/'hospital_sintetico.xlsx'
            arquivo=pasta/'modelo_ficticio.xlsx'
            shutil.copyfile(origem,arquivo)
            root=tk.Tk()
            try:
                app=Aplicativo(root)
                app.sessao.carregar(arquivo)
                app.preparo_concluido=True
                app.inicio_ciclo=time.perf_counter()-6.0
                app.historico=HistoricoExecucao(pasta=pasta/'historico')
                app.historico.fonte(arquivo,tipo='xlsx')
                app.estatisticas.registrar_total('preparo',1)
                app.estatisticas.concluir('preparo',1,consultados=1,encontrados=1)
                app.estatisticas.registrar_total('cadastro',1)
                app.estatisticas.concluir('cadastro',2,consultados=1,encontrados=1)
                app.estatisticas.registrar_total('hospital',1)
                app.estatisticas.concluir('hospital',1,consultados=1,encontrados=1)
                app._finalizar_relatorio()
                app._finalizar_relatorio() # idempotente
                arquivos=list(pasta.glob('RELATORIO_TECNICO_RPA_*.txt'))
                self.assertEqual(len(arquivos),1)
                self.assertEqual(app.abas.tab(3,'state'),'normal')
                self.assertIn('Tempo total',app.resultado_tempos.get())
                conteudo=arquivos[0].read_text(encoding='utf-8')
                self.assertNotIn('ANA MARIA',conteudo)
                self.assertNotIn('11144477735',conteudo)
                self.assertEqual(app.estatisticas.situacao,'CONCLUIDA')
            finally:
                root.destroy()
