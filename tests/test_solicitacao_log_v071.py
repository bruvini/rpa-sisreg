"""Regressão v0.7.1 — somente registros sintéticos, sem dados reais."""
import sys, unittest, tempfile
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from sisreg_hospital import ResultadoHospital, obter_detalhes
from planilha import SessaoPlanilha
from estatisticas import Estatisticas, relatorio_tecnico
from persistencia import COLUNAS_AUDITORIA
from app_info import APP_VERSION

FIXTURES=Path(__file__).resolve().parent/'fixtures'

class Texto:
    def __init__(self,texto):self.texto=texto
    def inner_text(self,**kwargs):return self.texto
class Pagina:
    url='https://sisregiii.saude.gov.br/cgi-bin/index'

class TesteSolicitacao(unittest.TestCase):
    def test_versao(self):self.assertEqual(APP_VERSION,'0.7.11')
    def test_ficha_separa_numero_solicitacao_de_autorizador(self):
        valores={
          '#fichaInternacao':'Código Solicitação 670478410; Número AIH 900000000012-3',
          '#fichaInternacao > table > tbody > tr:nth-child(46) > td:nth-child(1)':'10 - ELETIVO',
          '#fichaInternacao > table > tbody > tr:nth-child(1) > td:nth-child(1) > b':'670478410',
          '#fichaInternacao > table > tbody > tr:nth-child(50) > td:nth-child(2)':'0408050063'
        }
        with patch('sisreg_hospital._encontrar',side_effect=lambda p,s,**k:(p,Texto(valores[s]))):
            r=obter_detalhes(Pagina(),'9000000000123','0408050063')
        self.assertEqual(r.situacao,'FICHA_CONFERIDA')
        self.assertEqual(r.solicitacao,'670478410')
        self.assertEqual(r.autorizador,'')
    def test_solicitacao_nao_sobrescreve_autorizador_original(self):
        s=SessaoPlanilha();s.carregar(FIXTURES/'hospital_sintetico.xlsx')
        r=s.registros[0];r.autorizador='AUTORIZADOR_EXISTENTE'
        s.registrar_hospital(r,ResultadoHospital('FICHA_CONFERIDA','AIH específica','10','',r.procedimento,'670478410'),1.0)
        self.assertEqual(r.solicitacao,'670478410')
        self.assertEqual(r.autorizador,'AUTORIZADOR_EXISTENTE')
        self.assertEqual(r.situacao,'PENDENTE_AUTORIZADOR_CONFLITANTE')
    def test_coluna_de_auditoria_exclusiva(self):
        self.assertEqual(COLUNAS_AUDITORIA[-1], 'rpaProcedimentoSISREG')
        self.assertEqual(len(COLUNAS_AUDITORIA),3)

class TesteLogSeguro(unittest.TestCase):
    def test_evento_diagnostico_sem_identificadores_livres(self):
        e=Estatisticas()
        e.diagnosticar('CADASTRO_CPF','OK',ordinal=15,segundos=1.234)
        with self.assertRaises(ValueError):
            e.diagnosticar('CPF_11144477735','ERRO')
        e.diagnosticar('FICHA_HOSPITALAR','PENDENCIA',ordinal=16,
                     categoria='11144477735 NOME TESTE')
        e.encerrar(segundos=3,situacao='PARCIAL')
        with tempfile.TemporaryDirectory() as d:
            arquivo=Path(d)/'log.txt'
            relatorio_tecnico(e,None,arquivo)
            t=arquivo.read_text('utf-8')
            self.assertIn('CADASTRO_CPF | OK | ordinal=15 | duracao=1.234',t)
            self.assertIn('ERRO_NAO_CLASSIFICADO',t)
            self.assertNotIn('11144477735',t)
            self.assertNotIn('NOME TESTE',t)
    def test_diagnostico_invalido_nao_grava(self):
        e=Estatisticas()
        with self.assertRaises(ValueError):e.diagnosticar('LOGIN_SUBMETIDO','SENHA=secreta')
        self.assertEqual(e.diagnosticos,[])

if __name__=='__main__':unittest.main()

class TesteIntegracaoNovaColuna(unittest.TestCase):
    def test_solicitacao_em_xlsx_sem_modificar_autorizador(self):
        import shutil
        from openpyxl import load_workbook
        with tempfile.TemporaryDirectory() as d:
            copia=Path(d)/'hospital_sintetico.xlsx'
            shutil.copyfile(FIXTURES/'hospital_sintetico.xlsx',copia)
            s=SessaoPlanilha();s.carregar(copia)
            r=s.registros[0]
            s.registrar_hospital(r,ResultadoHospital(
                'FICHA_CONFERIDA','AIH exata','10','',r.procedimento,'670478410'),1.0)
            s.salvar_na_planilha(motivo='teste')
            w=load_workbook(copia,read_only=True)
            try:
                ws=w[r.aba]
                self.assertIsNone(ws.cell(1,11).value)
                self.assertEqual(ws.cell(r.linha,7).value,'ABC')
                self.assertNotEqual(ws.cell(r.linha,7).value,'670478410')
            finally:w.close()

class TesteDiagnosticoPorOperacao(unittest.TestCase):
    def test_etapas_navegacao_observador(self):
        from sisreg_hospital import consultar_solicitacao_hospitalar
        with patch('sisreg_hospital.pesquisar_por_cns') as buscar, \
             patch('sisreg_hospital.selecionar_linha_aih') as selecionar, \
             patch('sisreg_hospital.obter_detalhes',return_value=ResultadoHospital(
                 'FICHA_CONFERIDA','', '10','', '0408050063','670478410')):
            observados=[]
            r=consultar_solicitacao_hospitalar(Pagina(),'900000000000001','9000000000123',
                     '0408050063',observador=lambda *args:observados.append(args))
        self.assertEqual(r.solicitacao,'670478410')
        self.assertEqual([x[0] for x in observados],['BUSCA_HOSPITALAR','AIH_EXATA','LEITURA_FICHA'])
        self.assertTrue(all(x[1]=='OK' for x in observados))
