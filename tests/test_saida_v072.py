"""Testes inteiramente sintéticos para a planilha de entrega v0.7.2."""
import sys
import shutil
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
from saida_xlsx import situacao_final, comparacao_procedimento, CAMPOS_FINAIS
from planilha import SessaoPlanilha, Registro
from sisreg_hospital import ResultadoHospital
from app_info import APP_VERSION
from openpyxl import load_workbook

FIXTURE=Path(__file__).resolve().parent/'fixtures'/'hospital_sintetico.xlsx'

def reg(st):
    return Registro('POA CIRURGICO',2,'PESSOA FICTICIA','9000000000123','0408050063',
                    '11144477735','900000000000001','','',situacao=st)

class TesteSituacoes(unittest.TestCase):
    def test_versao(self): self.assertEqual(APP_VERSION,'0.7.13')
    def test_nao_encontrado_no_pdf(self):
        self.assertEqual(situacao_final(reg('AIH_AUSENTE_NO_PDF')),'Não encontrado no espelho de AIH')
    def test_dados_divergentes_pdf(self):
        self.assertEqual(situacao_final(reg('NOME_DIVERGENTE_ESPELHO')),'Dados divergentes do espelho de AIH')
    def test_cadastro_ausente(self):
        self.assertEqual(situacao_final(reg('PENDENTE_FICHA_CADASTRO_NAO_IDENTIFICADA')),'Cadastro não confirmado no SISREG — revisar')
    def test_cadastro_divergente(self):
        self.assertEqual(situacao_final(reg('PENDENTE_CPF_DIVERGENTE_CADASTRO')),'Dados divergentes na consulta SISREG')
    def test_aih_nao_confirmada(self):
        self.assertEqual(situacao_final(reg('PENDENTE_AIH_NAO_COMPROVADA_FICHA')),'AIH não confirmada na consulta — revisar')
    def test_dados_divergentes_sisreg(self):
        self.assertEqual(situacao_final(reg('PENDENTE_PROCEDIMENTO_DIVERGENTE')),'Procedimento divergente — revisão fiscal')
    def test_conferido_nao_equivale_atesto(self):
        self.assertEqual(situacao_final(reg('DADOS_COLETADOS_SEM_DIVERGENCIA')),'Consulta sem divergências')
    def test_timeout_nao_finge_aih_inexistente(self):
        self.assertEqual(situacao_final(reg('PENDENTE_FALHA_NAVEGACAO')),'Falha ou dados incompletos — repetir consulta')
    def test_cns_confirmado_ainda_nao_e_aih_conferida(self):
        self.assertIn('Aguardando',situacao_final(reg('CNS_CONFIRMADO_SISREG')))
    def test_procedimento_normalizado(self):
        r=reg('DADOS_COLETADOS_SEM_DIVERGENCIA');r.procedimento_sisreg='0408050063'
        self.assertEqual(comparacao_procedimento(r),'Compatível')
        r.procedimento_sisreg='0409040193'
        self.assertEqual(comparacao_procedimento(r),'Divergente')
        r.procedimento_sisreg=''
        self.assertEqual(comparacao_procedimento(r),'Não conferido')

class TesteXlsx(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.p=Path(self.temp.name)/'hospital.xlsx';shutil.copy2(FIXTURE,self.p)
        self.s=SessaoPlanilha();self.s.carregar(self.p)
        self.r=self.s.registros[0]
    def salvar(self):self.s.salvar_na_planilha(motivo='teste')
    def test_colunas_estilo_status_data_e_duplicacao_solicitacao_G(self):
        r=self.r
        w=load_workbook(self.p); w[self.r.aba].cell(self.r.linha,7).value=None; w.save(self.p); w.close()
        self.s.carregar(self.p); r=self.s.registros[0]
        r.procedimento='0408050063'
        r.cns='900000000000001'
        r.registrar=''
        self.s.registrar_hospital(r, ResultadoHospital('FICHA_CONFERIDA','AIH exata','10','','0408050063','670478410'),0.5)
        self.salvar()
        w=load_workbook(self.p)
        try:
            sh=w[r.aba]
            self.assertEqual([sh.cell(1,c).value for c in range(8,11)],list(CAMPOS_FINAIS))
            self.assertIsNone(sh.cell(1,12).value)
            self.assertEqual(sh.cell(r.linha,8).value,'Consulta sem divergências')
            self.assertEqual(sh.cell(r.linha,10).value,'Compatível')
            self.assertEqual(sh.cell(r.linha,7).value,'670478410')
            self.assertEqual(sh.cell(r.linha,7).value,'670478410')
            self.assertEqual(sh.cell(r.linha,9).number_format,'DD/MM/YYYY HH:MM:SS')
            self.assertTrue(sh.cell(r.linha,9).is_date)
            self.assertEqual(sh.freeze_panes,'A2')
            self.assertEqual(sh.auto_filter.ref,f'A1:J{max(2,sh.max_row)}')
            self.assertEqual(sh.cell(1,8).fill.fgColor.rgb[-6:],'083F6C')
            self.assertEqual(sh.cell(1,7).comment.author,'RPA SISREG')
        finally:w.close()
    def test_G_original_nao_e_substituida(self):
        self.r.autorizador='AUT_EXISTENTE'
        self.s.registrar_hospital(self.r,ResultadoHospital('FICHA_CONFERIDA','AIH','10','',self.r.procedimento,'670478410'),1)
        self.salvar()
        w=load_workbook(self.p,read_only=True)
        try:self.assertEqual(w[self.r.aba].cell(self.r.linha,7).value,'ABC')
        finally:w.close()
    def test_regravar_nao_gera_colunas_a_mais(self):
        self.salvar();self.salvar()
        w=load_workbook(self.p,read_only=True)
        try:self.assertEqual([w[self.r.aba].cell(1,c).value for c in range(8,11)],list(CAMPOS_FINAIS))
        finally:w.close()
    def test_migracao_9_colunas_antigas_sem_apagar_A_G(self):
        from saida_xlsx import CABECALHOS_LEGADOS
        w=load_workbook(self.p)
        sh=w[self.r.aba];original=[sh.cell(self.r.linha,c).value for c in range(1,8)]
        for i,h in enumerate(CABECALHOS_LEGADOS,8):sh.cell(1,i,h)
        w.save(self.p);w.close()
        self.s.carregar(self.p)
        self.s.salvar_na_planilha()
        w=load_workbook(self.p,read_only=True)
        try:
            sh=w[self.r.aba]
            self.assertEqual([sh.cell(self.r.linha,c).value for c in range(1,8)],original)
            self.assertEqual([sh.cell(1,c).value for c in range(8,11)],list(CAMPOS_FINAIS))
            self.assertIsNone(sh.cell(1,12).value)
        finally:w.close()
    def test_tabela_excel_se_estende_ate_coluna_k(self):
        from openpyxl.worksheet.table import Table, TableStyleInfo
        w=load_workbook(self.p)
        ws=w[self.r.aba]
        t=Table(displayName='TabelaTesteRPA',ref='A1:G2')
        t.tableStyleInfo=TableStyleInfo(name='TableStyleMedium2',showRowStripes=True)
        ws.add_table(t)
        w.save(self.p);w.close()
        self.s.carregar(self.p);self.s.salvar_na_planilha()
        w=load_workbook(self.p)
        try:
            t=next(iter(w[self.r.aba].tables.values()))
            self.assertEqual(t.ref,f'A1:J{max(2,w[self.r.aba].max_row)}')
            self.assertEqual(t.tableColumns[-1].name,'rpaProcedimentoSISREG')
            self.assertEqual(len(t.tableColumns),10)
        finally:w.close()

    def test_coluna_h_desconhecida_protegida(self):
        w=load_workbook(self.p);w[self.r.aba]['H1']='CampoPrivadoHospital';w.save(self.p);w.close()
        self.s.carregar(self.p)
        with self.assertRaises(Exception):self.s.salvar_na_planilha()
        w=load_workbook(self.p,read_only=True)
        try:self.assertEqual(w[self.r.aba]['H1'].value,'CampoPrivadoHospital')
        finally:w.close()

if __name__=='__main__':unittest.main()
