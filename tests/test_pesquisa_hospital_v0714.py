"""Regressoes da pesquisa hospitalar com HTML de estrutura sintetica."""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from sisreg_hospital import (
    MENU_HOSP, OPCAO_HOSP, CAMPO_CNS, BTN_PESQUISAR,
    PAGINADOR_PROXIMO, LINHAS_RESULTADOS, _formulario_hospitalar,
    abrir_pesquisa_hospitalar, pesquisar_por_cns, _ler_tabela_de_resultados)
from sisreg_navigation import NavegacaoInesperada

class Controle:
    def __init__(self,attrs=None):
        self.attrs=attrs or {};self.valor=None;self.cliques=0;self.hovers=0
    def get_attribute(self,k):return self.attrs.get(k)
    def fill(self,x,**kw):self.valor=x
    def click(self,**kw):self.cliques+=1
    def hover(self,**kw):self.hovers+=1

class Quadro:
    url='https://sisregiii.saude.gov.br/cgi-bin/cons_aih'

class TestesPesquisaHospitalar(unittest.TestCase):
    def test_selectors_correspondem_ao_html_fornecido(self):
        self.assertIn('name="cns"',CAMPO_CNS)
        self.assertIn('maxlength="15"',CAMPO_CNS)
        self.assertIn('name="enviar"',BTN_PESQUISAR)
        self.assertIn('cons_aih',OPCAO_HOSP)
        self.assertIn('consulta hosp',MENU_HOSP)
        self.assertIn('table_listagem',LINHAS_RESULTADOS)
        self.assertIn('seta_direita.png',PAGINADOR_PROXIMO)

    def test_pesquisa_prepara_cns_e_clica_botao(self):
        pg=Quadro()
        cns=Controle({'name':'cns'})
        enviar=Controle({'name':'enviar','type':'button'})
        def achar(p,sel,**kw):
            if sel==CAMPO_CNS:return pg,cns
            if sel==BTN_PESQUISAR:return pg,enviar
            raise AssertionError(sel)
        with patch('sisreg_hospital._encontrar',side_effect=achar):
            pesquisar_por_cns(pg,'700000000000001')
        self.assertEqual(cns.valor,'700000000000001')
        self.assertEqual(enviar.cliques,1)

    def test_nao_pesquisa_em_frames_diferentes(self):
        pg=Quadro()
        cns=Controle({'name':'cns'})
        enviar=Controle({'name':'enviar','type':'button'})
        def achar(p,sel,**kw):
            return (pg,cns) if sel==CAMPO_CNS else (Quadro(),enviar)
        with patch('sisreg_hospital._encontrar',side_effect=achar):
            with self.assertRaises(NavegacaoInesperada):
                _formulario_hospitalar(pg,tempo=10)
        self.assertEqual(enviar.cliques,0)

    def test_abrir_menu_consulta_hosp_solicitacoes(self):
        pg=Quadro()
        menu=Controle()
        opcao=Controle()
        with patch('sisreg_hospital._formulario_hospitalar',
                   side_effect=[NavegacaoInesperada('ainda nao abriu'),(pg,None,None)]), \
             patch('sisreg_hospital._encontrar',
                   side_effect=lambda p,sel,**kw:(pg,menu if sel==MENU_HOSP else opcao)):
            abrir_pesquisa_hospitalar(pg)
        self.assertEqual(menu.hovers,1)
        self.assertEqual(opcao.cliques,1)

    def test_cns_invalido_nao_interage(self):
        with patch('sisreg_hospital.abrir_pesquisa_hospitalar') as menu:
            with self.assertRaises(NavegacaoInesperada):
                pesquisar_por_cns(Quadro(),'123')
            menu.assert_not_called()

class ListaDOM:
    def __init__(self,linhas):self.linhas=linhas
    def evaluate_all(self,*args,**kw):return [
        {'indice':i,'textos':linha[0],'acao':linha[1]}
        for i,linha in enumerate(self.linhas)]
    def nth(self,i):return self.linhas[i]

class QuadroResultados(Quadro):
    def __init__(self,linhas):self.frames=[self];self.linhas=linhas
    def locator(self,selector):
        if selector==LINHAS_RESULTADOS:return ListaDOM(self.linhas)
        raise AssertionError(selector)

class TestesListaHospitalar(unittest.TestCase):
    def test_aih_da_coluna_seis_e_acao_mostrar_ficha(self):
        from sisreg_hospital import _ler_tabela_de_resultados
        dados=([
            '11.05.2026','PACIENTE SINTETICO','PROCEDIMENTO','CLINICA',
            'Eletiva','900000000012-3','APROVADA'],"mostrarFicha('123456')")
        frame,linhas,hash_pagina=_ler_tabela_de_resultados(QuadroResultados([dados]))
        self.assertEqual(len(linhas),1)
        self.assertEqual(linhas[0][1][5],'900000000012-3')
        self.assertTrue(hash_pagina)

    def test_ignora_aih_em_coluna_errada(self):
        dados=([
            '11.05.2026','900000000012-3','PROCEDIMENTO','CLINICA',
            'Eletiva','SEM AIH','APROVADA'],"mostrarFicha('123456')")
        _,linhas,_=_ler_tabela_de_resultados(QuadroResultados([dados]))
        self.assertFalse(linhas)

    def test_ignora_linhas_sem_acao_confirmada(self):
        dados=([
            '11.05.2026','PACIENTE SINTETICO','PROCEDIMENTO','CLINICA',
            'Eletiva','900000000012-3','APROVADA'],"excluir('123456')")
        _,linhas,_=_ler_tabela_de_resultados(QuadroResultados([dados]))
        self.assertFalse(linhas)

if __name__=='__main__': unittest.main()
