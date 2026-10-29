"""Regressão sem acesso à rede e sem identificadores reais."""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from sisreg_hospital import (selecionar_linha_aih, AIHNaoEncontrada,
    PAGINADOR_PROXIMO, consultar_solicitacao_hospitalar)
from sisreg_navigation import NavegacaoInesperada

AIH_ALVO='9000000000123'

class Celula:
    def __init__(self, parent, index): self.parent=parent;self.index=index
    def is_visible(self):return True
    def click(self,**kw):self.parent.cliques.append(self.index)
class Celulas:
    def __init__(self, valores):self.valores=valores;self.cliques=[]
    def count(self):return len(self.valores)
    def all_inner_texts(self):return self.valores
    def nth(self,i):return Celula(self,i)
class Linha:
    def __init__(self,aih):self.celulas=Celulas(['11.05.2026','PACIENTE SINTETICO','PROC','APROVADO',aih,''])
    def locator(self,selector):
        assert selector=='td',selector
        return self.celulas
class Lista:
    def __init__(self,rows):self.rows=rows
    def count(self):return len(self.rows)
    def nth(self,i):return self.rows[i]
class Link:
    def __init__(self,pagina):self.pagina=pagina
    def is_visible(self):return True
    def is_enabled(self):return True
    def get_attribute(self,attr):return {'title':'Próxima página','href':'javascript:paginar()'}.get(attr)
    def click(self,**kw):
        if self.pagina.nao_avanca:return
        self.pagina.pagina+=1
class Imagem:
    def __init__(self,pagina):self.pagina=pagina
    def is_visible(self):return True
    def get_attribute(self,attr):return {'title':'Próxima página','alt':'Próxima','src':'next.gif'}.get(attr)
    def locator(self,selector):
        assert selector=='xpath=..'
        return Link(self.pagina)
class Pagina:
    url='https://sisregiii.saude.gov.br/cgi-bin/index'
    def __init__(self,grupos,nao_avanca=False):
        self.frames=[self];self.grupos=grupos;self.pagina=0;self.nao_avanca=nao_avanca
    def locator(self,selector):
        if selector=='#main_page table tr':return Lista(self.grupos[self.pagina])
        if selector==PAGINADOR_PROXIMO:
            return Lista([Imagem(self)] if self.pagina<len(self.grupos)-1 else [])
        raise AssertionError(selector)

class Paginacao(unittest.TestCase):
    def test_encontra_aih_apenas_na_segunda_pagina(self):
        anterior=Linha('9000000000001');alvo=Linha('900000000012-3')
        pg=Pagina([[anterior],[alvo]])
        seen=[]
        selecionar_linha_aih(pg,AIH_ALVO,espera_ms=500,observador=lambda *v:seen.append(v))
        self.assertEqual(pg.pagina,1)
        self.assertEqual(anterior.celulas.cliques,[])
        self.assertEqual(alvo.celulas.cliques,[4])
        self.assertTrue(any(v[0]=='PAGINA_RESULTADOS' for v in seen))
    def test_aih_ausente_somente_apos_ultima_pagina(self):
        pg=Pagina([[Linha('9000000000001')],[Linha('9000000000002')],[Linha('9000000000003')]])
        with self.assertRaises(AIHNaoEncontrada):
            selecionar_linha_aih(pg,AIH_ALVO,espera_ms=300)
        self.assertEqual(pg.pagina,2)
    def test_paginacao_sem_avanco_nao_e_ausencia(self):
        pg=Pagina([[Linha('9000000000001')],[Linha(AIH_ALVO)]],nao_avanca=True)
        # Aguardar somente algumas dezenas de ms por teste, sem consulta real.
        with patch('sisreg_hospital.time.monotonic', side_effect=[0,0,0,20]):
            with self.assertRaises(NavegacaoInesperada):
                selecionar_linha_aih(pg,AIH_ALVO,espera_ms=500)
        self.assertEqual(pg.pagina,0)
    def test_um_unico_resultado_sem_flecha_abre_sem_paginacao(self):
        alvo=Linha(AIH_ALVO)
        pg=Pagina([[alvo]])
        selecionar_linha_aih(pg,AIH_ALVO,espera_ms=500)
        self.assertEqual(alvo.celulas.cliques,[4])
    def test_busca_exaurida_nao_se_repete_automaticamente(self):
        from types import SimpleNamespace
        from progresso import candidato_hospitalar
        reg=SimpleNamespace(cns='700000000000000',aih=AIH_ALVO,nome='PACIENTE TESTE',
            situacao='PENDENTE_AIH_NAO_LOCALIZADA_PAGINAS',situacao_anterior='',
            consulta_hospitalar='AIH_NAO_LOCALIZADA_PAGINAS')
        self.assertFalse(candidato_hospitalar(reg))
        reg.consulta_hospitalar=''
        reg.situacao_anterior='AIH não encontrada após pesquisar todas as páginas — revisar'
        self.assertFalse(candidato_hospitalar(reg))

    def test_falha_de_paginacao_permanece_recuperavel(self):
        from types import SimpleNamespace
        from progresso import candidato_hospitalar
        reg=SimpleNamespace(cns='700000000000000',aih=AIH_ALVO,nome='PACIENTE TESTE',
            situacao='PENDENTE_FALHA_NAVEGACAO',situacao_anterior='',consulta_hospitalar='FALHA_NAVEGACAO',carater='',autorizador='',comparacao_anterior='')
        self.assertTrue(candidato_hospitalar(reg))

    def test_ausencia_nao_e_erro_tecnico_ao_consultar(self):
        pg=Pagina([[Linha('9000000000001')]])
        events=[]
        with patch('sisreg_hospital.pesquisar_por_cns'):
            result=consultar_solicitacao_hospitalar(pg,'700000000000000',AIH_ALVO,observador=lambda *v:events.append(v))
        self.assertEqual(result.situacao,'AIH_NAO_LOCALIZADA_PAGINAS')
        self.assertEqual(events[-1][1],'PENDENCIA')

if __name__=='__main__':unittest.main()
