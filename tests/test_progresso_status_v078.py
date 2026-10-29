"""Regressão sintética da retomada e dos estados fiscais v0.7.8.
Nenhum dado de pessoa real deve ser utilizado aqui.
"""
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from progresso import resumo_progresso, ficha_hospitalar_completa, candidato_hospitalar
from planilha import Registro, SessaoPlanilha
from sisreg_hospital import ResultadoHospital
from saida_xlsx import situacao_final, comparacao_procedimento, orientacao_fiscal
from controle_sessao import texto_erro_servidor, texto_exige_verificacao
from sisreg_login import Aplicativo
from app_info import APP_VERSION


def reg(**kwargs):
    r=Registro('PT6',2,'PACIENTE DE TESTE','9000000000123','0408050063',
               '52998224725','700000000000001','','')
    for k,v in kwargs.items():setattr(r,k,v)
    return r


class TesteRetomada(unittest.TestCase):
    def test_versao(self):self.assertEqual(APP_VERSION,'0.7.13')
    def test_exemplo_de_cem_registros(self):
        p=resumo_progresso(100,30,70,65)
        self.assertEqual(p.acumulados,95)
        self.assertAlmostEqual(p.taxa_total,95.0)
        self.assertAlmostEqual(p.taxa_lote,92.857142857,places=3)
        self.assertIn('95/100 (95.0%)',p.resumo())
        self.assertIn('65/70 (92.9%)',p.resumo())
    def test_contagem_impossivel_e_bloqueada(self):
        with self.assertRaises(ValueError):resumo_progresso(100,50,70,2)
    def test_aih_completa_somente_com_tres_fontes(self):
        r=reg(carater='10',autorizador='670478410',
              situacao_anterior='Consulta sem divergências',comparacao_anterior='Não conferido')
        self.assertFalse(ficha_hospitalar_completa(r))
        self.assertTrue(candidato_hospitalar(r))
        r.comparacao_anterior='Compatível'
        self.assertTrue(ficha_hospitalar_completa(r))
        self.assertFalse(candidato_hospitalar(r))
    def test_divergencia_fiscal_preservada_sem_reconsulta(self):
        r=reg(carater='10',autorizador='670478410',
              situacao_anterior='Procedimento divergente — revisão fiscal',comparacao_anterior='Divergente')
        self.assertTrue(ficha_hospitalar_completa(r))
        self.assertFalse(candidato_hospitalar(r))
    def test_cpf_existente_nao_e_reprocessado_pelo_pdf(self):
        r=reg(cpf='52998224725',cns='',situacao='PRONTO_PARA_CONFERENCIA')
        s=SessaoPlanilha();s.registros=[r];s.origem=ROOT/'tests'/'fixtures'/'hospital_sintetico.xlsx'
        espelho=SimpleNamespace(pagina=2,cpf='11144477735',cns='',nome='OUTRA PESSOA')
        s.complementar_pdf({r.aih:[espelho]}, s.origem)
        self.assertEqual(r.cpf,'52998224725')
        self.assertEqual(r.situacao,'PRONTO_PARA_CONFERENCIA')
    def test_codigo_solicitacao_preenche_autorizador_quando_vazio(self):
        r=reg(carater='',autorizador='')
        SessaoPlanilha().registrar_hospital(r,ResultadoHospital(
            'FICHA_CONFERIDA','AIH exata','10','','0408050063','670478410'),1.0)
        self.assertEqual(r.autorizador,'670478410')
        self.assertEqual(r.situacao,'DADOS_COLETADOS_SEM_DIVERGENCIA')
    def test_codigo_existente_divergente_eh_pendencia(self):
        r=reg(carater='10',autorizador='999999999')
        SessaoPlanilha().registrar_hospital(r,ResultadoHospital(
            'FICHA_CONFERIDA','AIH exata','10','','0408050063','670478410'),1.0)
        self.assertEqual(r.autorizador,'999999999')
        self.assertEqual(situacao_final(r),'Dados divergentes no SISREG')
    def test_procedimento_divergente_indica_motivo_e_acao(self):
        r=reg()
        SessaoPlanilha().registrar_hospital(r,ResultadoHospital(
            'PROCEDIMENTO_DIVERGENTE','Procedimentos diferentes','10','','0409040193','670478410'),1.0)
        self.assertEqual(comparacao_procedimento(r),'Divergente')
        st=situacao_final(r)
        self.assertEqual(st,'Procedimento divergente — revisão fiscal')
        self.assertIn('troca autorizada',orientacao_fiscal(st))
    def test_ficha_nao_aberta_exibe_campos_coerentes(self):
        r=reg(carater='',autorizador='',solicitacao='',procedimento_sisreg='',
              consulta_hospitalar='FICHA_NAO_ABERTA',situacao='PENDENTE_FICHA_NAO_ABERTA')
        app=Aplicativo.__new__(Aplicativo)
        linha=app._linha_hospital(r)
        self.assertEqual(linha[3:6],('—','—','—'))
        self.assertIn('não aberta',linha[6])
    def test_upstream_nao_e_captcha(self):
        t='upstream connect error or disconnect/reset before headers. retried and the latest reset reason: connection termination'
        self.assertTrue(texto_erro_servidor(t))
        self.assertFalse(texto_exige_verificacao(t))
    def test_captcha_eh_humano(self):
        self.assertTrue(texto_exige_verificacao('O SISREG exige reCAPTCHA'))


if __name__=='__main__':unittest.main()
