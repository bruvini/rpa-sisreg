"""Integração em navegador real; toda a página e todos os dados são sintéticos."""
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from sisreg_hospital import (consultar_solicitacao_hospitalar, obter_detalhes,
    _ler_tres_campos, selecionar_linha_aih, _ler_tabela_de_resultados,
    _campos_por_rotulo, FalhaLeituraTabela, FalhaLeituraFicha)
from sisreg_navigation import NavegacaoInesperada

AIH = '9000000000123'
PROC = '0408050063'
HTML = r'''<!doctype html><html><body><div id="main_page">
<input name="cns" type="text" maxlength="15">
<input name="enviar" type="button" value="PESQUISAR" onclick="pesquisar()">
<div id="resultado"></div></div><div id="detalhe"></div>
<script>
let pagina=0;
function pesquisar(){ pagina=0; render(); }
function exibirPagina(n,total){ pagina=n; render(); }
function render(){
 let aih=pagina===0?'900000000000-1':'900000000012-3';
 document.querySelector('#resultado').innerHTML=`<table class="table_listagem"><tbody>
 <tr><td class="td_titulo_tabela" colspan="7">RESULTADOS DA PESQUISA</td></tr>
 <tr onclick="mostrarFicha('123456')" class="par_tr linha_selecionavel">
 <td>01.01.2026</td><td>TESTE</td><td>PROCEDIMENTO</td><td>CLINICA</td>
 <td>Eletiva</td><td>${aih}</td><td>APROVADA</td></tr></tbody></table>`+
 (pagina===0?`<a href="#" onclick="exibirPagina(1,2); return false;"><img src="/imagens/seta_direita.png" alt="Proxima"></a>`:'');
}
function mostrarFicha(id){ document.querySelector('#detalhe').innerHTML=`
 <div id="fichaInternacao"><table><tbody>
 <tr><td colspan="3">Código Solicitação: <b>670478410</b></td><td colspan="3">Número AIH: <b>900000000012-3</b></td></tr>
 <tr><td colspan="2"><b>Caráter</b></td><td colspan="4"><b>Classificação de Risco</b></td></tr>
 <tr><td colspan="2">10 - Eletivo</td><td colspan="4">Prioridade 2</td></tr>
 <tr><td colspan="2"><b>Procedimento Solicitado:</b></td><td colspan="4"><b>Código:</b></td></tr>
 <tr><td colspan="2">PROCEDIMENTO SINTETICO</td><td colspan="4">0408050063</td></tr>
 </tbody></table></div>`; }
</script></body></html>'''

class TesteHospitalPlaywrightReal(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pw = sync_playwright().start()
        kwargs = {'headless': True}
        if os.environ.get('SISREG_TEST_CHROME'):
            kwargs['executable_path'] = os.environ['SISREG_TEST_CHROME']
        cls.browser = cls.pw.chromium.launch(**kwargs)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.pw.stop()

    def setUp(self):
        self.page = self.browser.new_page()
        self.page.route('**/*', lambda route: route.fulfill(status=200, content_type='text/html; charset=utf-8', body=HTML))
        self.page.goto('https://sisregiii.saude.gov.br/cgi-bin/cons_aih')

    def tearDown(self):
        self.page.close()

    def test_pesquisa_pagina_e_le_ficha(self):
        eventos=[]
        resultado=consultar_solicitacao_hospitalar(self.page,'700000000000001',AIH,PROC,
            observador=lambda *args:eventos.append(args))
        self.assertEqual((resultado.situacao,resultado.carater,resultado.solicitacao,resultado.procedimento),
                         ('FICHA_CONFERIDA','10','670478410',PROC))
        self.assertTrue(any(e[0]=='PAGINA_RESULTADOS' for e in eventos))

    def test_primeira_pagina_e_aih_ausente(self):
        self.page.evaluate('pesquisar()')
        selecionar_linha_aih(self.page,'9000000000001')
        self.assertEqual(self.page.locator('#fichaInternacao').count(),1)
        self.page.reload()
        eventos=[]
        r=consultar_solicitacao_hospitalar(self.page,'700000000000001','9000000000999',PROC,
            observador=lambda *a:eventos.append(a))
        self.assertEqual(r.situacao,'AIH_NAO_LOCALIZADA_PAGINAS')
        self.assertEqual(eventos[-1][3],'AIH_NAO_LOCALIZADA_PAGINAS')

    def test_ficha_incorreta_campo_ausente_e_cancelamento(self):
        self.page.evaluate("mostrarFicha('123456')")
        r=obter_detalhes(self.page,'9000000000001',PROC,espera_ficha_ms=0)
        self.assertEqual(r.situacao,'AIH_NAO_COMPROVADA_FICHA')
        self.page.locator('#fichaInternacao tr').last.locator('td').last.evaluate('(e) => e.textContent=""')
        campos, erro=_ler_tres_campos(self.page.main_frame,espera_ms=0)
        self.assertIsNone(campos)
        self.assertEqual(erro,'CAMPOS_FICHA_INCOMPLETOS')
        with self.assertRaises(NavegacaoInesperada):
            selecionar_linha_aih(self.page,AIH,cancelar=lambda:True)

    def test_erros_de_leitura_nao_sao_tratados_como_campos_ausentes(self):
        frame=Mock()
        frame.locator.return_value.evaluate_all.side_effect=TypeError('falha sintetica')
        with self.assertRaises(FalhaLeituraFicha):
            _campos_por_rotulo(frame)
        with patch('sisreg_hospital._quadros_oficiais',return_value=[frame]):
            with self.assertRaises(FalhaLeituraTabela):
                _ler_tabela_de_resultados(self.page)
