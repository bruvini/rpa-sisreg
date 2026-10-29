"""Regressoes para HTML institucional da pesquisa de internacao (dados sinteticos)."""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from sisreg_hospital import (selecionar_linha_aih, AIHNaoEncontrada,
    PAGINADOR_PROXIMO, LINHAS_RESULTADOS, consultar_solicitacao_hospitalar)
from sisreg_navigation import NavegacaoInesperada

ALVO='9000000000123'

class Celulas:
    def __init__(self,values):self.values=values
    def all_inner_texts(self):return self.values

class Linha:
    def __init__(self,aih,acao="mostrarFicha('123456')"):
        self.values=['11.05.2026','PACIENTE SINTETICO','PROCEDIMENTO',
                     'CLINICA','Eletiva',aih,'APROVADA']
        self.acao=acao
        self.clicks=0
    def locator(self,sel):
        assert sel=='td'
        return Celulas(self.values)
    def get_attribute(self,attr):
        return self.acao if attr=='onclick' else None
    def is_visible(self):return True
    def click(self,**kw):self.clicks+=1

class Proxima:
    def __init__(self,page):self.page=page
    def is_visible(self):return True
    def is_enabled(self):return True
    def get_attribute(self,attr):
        if attr=='onclick':return "exibirPagina(1,2); return false;"
        return None
    def click(self,**kw):
        if not self.page.parar_paginar:
            self.page.numero+=1

class Lista:
    def __init__(self,rows):self.rows=rows
    def count(self):return len(self.rows)
    def nth(self,i):return self.rows[i]

class Pagina:
    url='https://sisregiii.saude.gov.br/cgi-bin/index'
    def __init__(self,paginas,parar_paginar=False):
        self.frames=[self];self.paginas=paginas
        self.numero=0;self.parar_paginar=parar_paginar
    def locator(self,selector):
        if selector==LINHAS_RESULTADOS:
            return Lista(self.paginas[self.numero])
        if selector==PAGINADOR_PROXIMO:
            return Lista([Proxima(self)] if self.numero<len(self.paginas)-1 else [])
        raise AssertionError(selector)

class TestesPaginacao(unittest.TestCase):
    def test_encontra_aihexata_na_segunda_pagina(self):
        anterior=Linha('9000000000001');alvo=Linha('900000000012-3')
        p=Pagina([[anterior],[alvo]])
        eventos=[]
        selecionar_linha_aih(p,ALVO,espera_ms=500,observador=lambda *v:eventos.append(v))
        self.assertEqual(p.numero,1)
        self.assertEqual(anterior.clicks,0)
        self.assertEqual(alvo.clicks,1)
        self.assertTrue(any(v[0]=='PAGINA_RESULTADOS' for v in eventos))

    def test_ultima_pagina_sem_aih(self):
        p=Pagina([[Linha('9000000000001')],[Linha('9000000000002')]])
        with self.assertRaises(AIHNaoEncontrada):
            selecionar_linha_aih(p,ALVO,espera_ms=500)
        self.assertEqual(p.numero,1)

    def test_nao_avanca_mantem_pendencia_tecnica(self):
        p=Pagina([[Linha('9000000000001')],[Linha(ALVO)]],parar_paginar=True)
        with patch('sisreg_hospital.time.monotonic',side_effect=[0,0,0,20]):
            with self.assertRaises(NavegacaoInesperada):
                selecionar_linha_aih(p,ALVO,espera_ms=500)
        self.assertEqual(p.numero,0)

    def test_aih_ja_na_primeira(self):
        a=Linha(ALVO)
        p=Pagina([[a]])
        selecionar_linha_aih(p,ALVO,espera_ms=100)
        self.assertEqual(a.clicks,1)

    def test_nao_clicar_em_linha_sem_mostrar_ficha(self):
        x=Linha(ALVO,acao="outraFuncao('123456')")
        p=Pagina([[x]])
        with self.assertRaises(NavegacaoInesperada):
            selecionar_linha_aih(p,ALVO,espera_ms=100)
        self.assertEqual(x.clicks,0)

    def test_sem_nova_busca_automaticamente_apos_exaurir(self):
        from types import SimpleNamespace
        from progresso import candidato_hospitalar
        r=SimpleNamespace(cns='700000000000000',aih=ALVO,nome='PACIENTE',
            situacao='PENDENTE_AIH_NAO_LOCALIZADA_PAGINAS',situacao_anterior='',
            consulta_hospitalar='AIH_NAO_LOCALIZADA_PAGINAS')
        self.assertFalse(candidato_hospitalar(r))

    def test_erro_navegacao_permanece_recuperavel(self):
        from types import SimpleNamespace
        from progresso import candidato_hospitalar
        r=SimpleNamespace(cns='700000000000000',aih=ALVO,nome='PACIENTE',
            situacao='PENDENTE_FALHA_NAVEGACAO',situacao_anterior='',
            consulta_hospitalar='FALHA_NAVEGACAO',carater='',autorizador='',
            comparacao_anterior='')
        self.assertTrue(candidato_hospitalar(r))

    def test_aih_ausente_nao_e_falha_tecnica(self):
        p=Pagina([[Linha('9000000000001')]])
        eventos=[]
        with patch('sisreg_hospital.pesquisar_por_cns'):
            result=consultar_solicitacao_hospitalar(p,'700000000000000',ALVO,
                    observador=lambda *v:eventos.append(v))
        self.assertEqual(result.situacao,'AIH_NAO_LOCALIZADA_PAGINAS')
        self.assertEqual(eventos[-1][1],'PENDENCIA')

if __name__=='__main__': unittest.main()
