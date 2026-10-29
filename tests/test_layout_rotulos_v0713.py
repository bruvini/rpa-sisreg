"""Teste dos pares titulo/valor em diferentes estruturas de ficha (sintetico)."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from sisreg_hospital import _extrair_campos_de_linhas

SOLIC=['Código Solicitação: 670478410','Número AIH: 900000000012-3']
HEAD_C=['Caráter','Classificação de Risco']
DATA_C=['10 - Eletivo','Prioridade 2 - Prioridade não urgente']
HEAD_P=['Procedimento Solicitado:','Código:']
DATA_P=['TRATAMENTO SINTETICO','0408050063']
CERTO=('10','670478410','0408050063')

class TesteRotulos(unittest.TestCase):
    def verificar(self, inicio, intervalo):
        linhas=[SOLIC]+[['Seção','Outras informações']]*inicio
        linhas+=[HEAD_C,DATA_C]+[['Outro campo','Outro valor']]*intervalo
        linhas+=[HEAD_P,DATA_P]
        self.assertEqual(_extrair_campos_de_linhas(linhas),CERTO)

    def test_primeira_ficha_linhas_46_50(self):
        self.verificar(43,2)

    def test_segunda_ficha_linha_40(self):
        self.verificar(37,0)

    def test_terceira_ficha_linhas_44_48(self):
        self.verificar(41,2)

    def test_carater_e_prioridade_mesma_linha(self):
        self.assertEqual(_extrair_campos_de_linhas(
            [SOLIC,HEAD_C,DATA_C,HEAD_P,DATA_P]),CERTO)

    def test_duplicidade_de_procedimentos_nao_e_aceita(self):
        self.assertEqual(_extrair_campos_de_linhas(
            [SOLIC,HEAD_C,DATA_C,HEAD_P,DATA_P,HEAD_P,['OUTRO','0409040193']])[2],'')

    def test_sem_cabecalho_nao_inventa_campos(self):
        self.assertEqual(_extrair_campos_de_linhas(
            [SOLIC,DATA_C,DATA_P]),('','670478410',''))

    def test_codigo_em_coluna_errada_nao_e_procedimento(self):
        self.assertEqual(_extrair_campos_de_linhas(
            [SOLIC,HEAD_C,DATA_C,HEAD_P,['0408050063','DESCRICAO']])[2],'')

if __name__=='__main__': unittest.main()
