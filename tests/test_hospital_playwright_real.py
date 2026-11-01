"""Integração em navegador real; toda a página e todos os dados são sintéticos."""
import os
import sys
import time
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from sisreg_hospital import (consultar_solicitacao_hospitalar, obter_detalhes, pesquisar_por_cns,
    _ler_tres_campos, selecionar_linha_aih, _ler_tabela_de_resultados,
    _campos_por_rotulo, FalhaLeituraTabela, FalhaLeituraFicha)
from sisreg_navigation import NavegacaoInesperada
from controle_sessao import desafio_visivel

AIH = '9000000000123'
PROC = '0408050063'
HTML = r'''<!doctype html><html><body><div id="main_page">
<input name="cns" type="text" maxlength="15">
<input name="enviar" type="button" value="PESQUISAR" onclick="pesquisar()">
<div id="resultado"></div></div><div id="detalhe"></div>
<script>
let params=new URLSearchParams(location.search);
let pagina=Number(params.get('pagina')||0);
document.querySelector('input[name=cns]').value=params.get('cns')||'';
function pesquisar(){ location.href='/cgi-bin/cons_aih?cns='+document.querySelector('input[name=cns]').value+'&pagina=0'; }
function exibirPagina(n,total){ location.href='/cgi-bin/cons_aih?cns='+document.querySelector('input[name=cns]').value+'&pagina='+n; }
function render(){
 let cns=params.get('cns')||'';
 if(cns.endsWith('003')){ document.querySelector('#resultado').innerHTML='<table class="table_listagem"><tr><td>&nbsp;</td></tr><tr><td><center><i><span>Nenhum registro encontrado.</span></i></center></td></tr><tr><td>&nbsp;</td></tr></table>'; return; }
 if(cns.endsWith('004')){ document.querySelector('#resultado').innerHTML='<table class="table_listagem"><tr><td class="td_titulo_tabela">RESULTADOS DA PESQUISA (0)</td></tr></table>'; return; }
 let aih=cns.endsWith('002')?(pagina===0?'900000000099-9':'900000000088-8'):(pagina===0?'900000000000-1':'900000000012-3');
 document.querySelector('#resultado').innerHTML=`<table class="table_listagem"><tbody>
 <tr><td class="td_titulo_tabela" colspan="7">RESULTADOS DA PESQUISA (2)</td></tr>
 <tr onclick="mostrarFicha('123456')" class="par_tr linha_selecionavel">
 <td>01.01.2026</td><td>TESTE</td><td>PROCEDIMENTO</td><td>CLINICA</td>
 <td>Eletiva</td><td>${aih}</td><td>APROVADA</td></tr></tbody></table>`+
 `<div>Exibindo Página <input name="txtPagina" value="${pagina+1}"> de 2 `+
 (pagina===0?`<a href="#" onclick="exibirPagina(1,2); return false;"><img src="/imagens/seta_direita.png" alt="Proxima"></a>`:'')+'</div>';
}
if(params.has('cns')) render();
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
        self.page.goto('https://sisregiii.saude.gov.br/cgi-bin/cons_aih?cns=700000000000001&pagina=0')
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

    def test_verificacao_humana_no_frame_oficial(self):
        self.page.route('**/verificacao-ficticia',lambda route: route.fulfill(
            status=200,content_type='text/html; charset=utf-8',body='<body>CAPTCHA: verificação humana</body>'))
        self.page.evaluate("""() => { const f=document.createElement('iframe');
            f.src='https://sisregiii.saude.gov.br/verificacao-ficticia';document.body.appendChild(f); }""")
        self.page.frame_locator('iframe').locator('body').wait_for()
        self.assertTrue(desafio_visivel(self.page.context))

    def test_nova_busca_espera_resposta_antes_de_examinar_tabela_antiga(self):
        pesquisar_por_cns(self.page,'700000000000001')
        def resposta_lenta(route):
            time.sleep(.7)
            route.fulfill(status=200,content_type='text/html; charset=utf-8',body=HTML)
        self.page.route('**/*cns=700000000000002*',resposta_lenta)
        inicio=time.monotonic()
        quadro=pesquisar_por_cns(self.page,'700000000000002')
        self.assertGreaterEqual(time.monotonic()-inicio,.6)
        self.assertIn('900000000099-9',quadro.locator('table.table_listagem').inner_text())
        from sisreg_hospital import AIHNaoEncontrada
        with self.assertRaises(AIHNaoEncontrada):
            selecionar_linha_aih(quadro,'9000000000001')
        self.assertEqual(self.page.locator('#fichaInternacao').count(),0)

    def test_resultado_zero_so_apos_navegacao_confirmada(self):
        r=consultar_solicitacao_hospitalar(self.page,'700000000000003',AIH,PROC)
        self.assertEqual(r.situacao,'AIH_NAO_LOCALIZADA_PAGINAS')
        r=consultar_solicitacao_hospitalar(self.page,'700000000000004',AIH,PROC)
        self.assertEqual(r.situacao,'AIH_NAO_LOCALIZADA_PAGINAS')

    def test_ultima_pagina_nao_confirmada_nunca_vira_aih_ausente(self):
        quadro=pesquisar_por_cns(self.page,'700000000000001')
        self.page.locator('a:has(img[alt="Proxima"])').evaluate('(e)=>e.remove()')
        with self.assertRaises(NavegacaoInesperada):
            selecionar_linha_aih(quadro,'9000000000999')

    def test_pesquisa_iniciada_na_segunda_pagina_e_inconclusiva(self):
        self.page.goto('https://sisregiii.saude.gov.br/cgi-bin/cons_aih?cns=700000000000001&pagina=1')
        with self.assertRaises(NavegacaoInesperada):
            selecionar_linha_aih(self.page,AIH)
        self.assertEqual(self.page.locator('#fichaInternacao').count(),0)

    def test_falha_da_nova_navegacao_nao_consulta_resultado_anterior(self):
        pesquisar_por_cns(self.page,'700000000000001')
        self.page.route('**/*cns=700000000000002*',lambda route:route.abort())
        with self.assertRaises(NavegacaoInesperada):
            consultar_solicitacao_hospitalar(self.page,'700000000000002','9000000000001',PROC)

    def test_pesquisa_e_paginacao_dentro_de_iframe(self):
        self.page.route('**/iframe-host',lambda route:route.fulfill(
            status=200,content_type='text/html',body='<iframe name="f_principal" src="/cgi-bin/cons_aih"></iframe>'))
        self.page.goto('https://sisregiii.saude.gov.br/iframe-host')
        resultado=consultar_solicitacao_hospitalar(self.page,'700000000000001',AIH,PROC)
        self.assertEqual(resultado.situacao,'FICHA_CONFERIDA')
        self.assertEqual(resultado.procedimento,PROC)

    def test_mesma_pesquisa_pode_retornar_resultado_identico(self):
        quadro=pesquisar_por_cns(self.page,'700000000000001')
        anterior=quadro.locator('table.table_listagem').inner_text()
        quadro=pesquisar_por_cns(self.page,'700000000000001')
        self.assertEqual(anterior,quadro.locator('table.table_listagem').inner_text())

    def test_formulario_post_real_com_segunda_pagina(self):
        from urllib.parse import parse_qs
        def servidor(route):
            dados=parse_qs(route.request.post_data or '')
            cns=dados.get('cns',[''])[0]
            numero=int(dados.get('pagina',['0'])[0])
            aih='900000000000-1' if numero==0 else '900000000012-3'
            resultado=(f'''<table class="table_listagem"><tr><td class="td_titulo_tabela">RESULTADOS DA PESQUISA (2)</td></tr>
                <tr onclick="mostrarFicha('123456')" class="linha_selecionavel"><td>01.01.2026</td>
                <td>TESTE</td><td>PROC</td><td>CLINICA</td><td>Eletiva</td><td>{aih}</td><td>APROVADA</td></tr></table>
                <div>Exibindo Página <input name="txtPagina" value="{numero+1}"> de 2 '''+
                ('''<a href="#" onclick="exibirPagina(1,2); return false;"><img src="/imagens/seta_direita.png" alt="Proxima"></a>''' if numero==0 else '')+'</div>') if cns else ''
            html=f'''<!doctype html><div id="main_page"><form name="formulario" method="post" action="/sisreg-post">
              <input name="cns" type="text" maxlength="15" value="{cns}">
              <input name="pagina" type="hidden" value="{numero}">
              <input name="enviar" type="button" value="PESQUISAR" onclick="pesquisar()">{resultado}</form></div>
              <div id="detalhe"></div><script>
              function pesquisar(){{document.formulario.pagina.value=0;document.formulario.submit();}}
              function exibirPagina(n,total){{document.formulario.pagina.value=n;document.formulario.submit();}}
              function mostrarFicha(id){{document.querySelector('#detalhe').textContent='FICHA ABERTA';}}
              </script>'''
            route.fulfill(status=200,content_type='text/html; charset=utf-8',body=html)
        self.page.route('**/sisreg-post',servidor)
        self.page.goto('https://sisregiii.saude.gov.br/sisreg-post')
        quadro=pesquisar_por_cns(self.page,'700000000000001')
        selecionar_linha_aih(quadro,AIH)
        self.assertEqual(self.page.locator('#detalhe').inner_text(),'FICHA ABERTA')

    def _resultados_com_mascara(self, primeira_exata=False, mascara='*************'):
        html=HTML.replace('RESULTADOS DA PESQUISA (2)','RESULTADOS DA PESQUISA (4)')
        original='<td>Eletiva</td><td>${aih}</td><td>APROVADA</td></tr>'
        html=html.replace(original,original+f'''<tr onclick="mostrarFicha('654321')" class="linha_selecionavel">
            <td>02.01.2026</td><td>TESTE MASCARADO</td><td>PROC</td><td>CLINICA</td>
            <td>Eletiva</td><td>{mascara}</td><td>APROVADA</td></tr>''')
        if primeira_exata:
            html=html.replace("'900000000000-1'","'900000000012-3'")
        self.page.route('**/*',lambda route:route.fulfill(
            status=200,content_type='text/html; charset=utf-8',body=html))

    def test_aih_exata_nao_e_bloqueada_por_outra_mascarada(self):
        self._resultados_com_mascara(primeira_exata=True)
        r=consultar_solicitacao_hospitalar(self.page,'700000000000001',AIH,PROC)
        self.assertEqual(r.situacao,'FICHA_CONFERIDA')
        self.assertIn('pagina=0',self.page.url)

    def test_mascarada_na_primeira_nao_impede_correspondencia_na_segunda(self):
        self._resultados_com_mascara()
        r=consultar_solicitacao_hospitalar(self.page,'700000000000001',AIH,PROC)
        self.assertEqual(r.situacao,'FICHA_CONFERIDA')
        self.assertIn('pagina=1',self.page.url)

    def test_mascara_ou_aih_ausente_produz_revisao_apos_todas_as_paginas(self):
        for mascara in ('*************','','9000000000123*'):
            with self.subTest(mascara=mascara):
                self._resultados_com_mascara(mascara=mascara)
                eventos=[]
                r=consultar_solicitacao_hospitalar(self.page,'700000000000002',AIH,PROC,
                    observador=lambda *args:eventos.append(args))
                self.assertEqual(r.situacao,'AIH_NAO_COMPROVADA_RESULTADOS')
                self.assertEqual(eventos[-1][3],'AIH_NAO_CONFIRMADA')
                self.assertIn('pagina=1',self.page.url)
                self.assertEqual(self.page.locator('#fichaInternacao').count(),0)

    def test_mascara_nao_esconde_falha_real_de_paginacao(self):
        self._resultados_com_mascara()
        quadro=pesquisar_por_cns(self.page,'700000000000002')
        self.page.locator('a:has(img[alt="Proxima"])').evaluate('(e)=>e.remove()')
        with self.assertRaises(NavegacaoInesperada):
            selecionar_linha_aih(quadro,AIH)

    def test_linha_estruturalmente_invalida_continua_tecnica(self):
        self._resultados_com_mascara(primeira_exata=True,mascara='TEXTO INESPERADO')
        quadro=pesquisar_por_cns(self.page,'700000000000001')
        with self.assertRaises(FalhaLeituraTabela):
            selecionar_linha_aih(quadro,AIH)

    def _ficha_com_trocas(self, linhas):
        tabela='''<tr><td class="td_titulo_tabela" colspan="6">Troca de Procedimentos</td></tr>
            <tr><td>CID</td><td colspan="2">Procedimento</td><td colspan="2">Solicitante</td><td>Status</td></tr>'''
        for codigo,status in linhas:
            tabela+=f'<tr><td>CID TESTE</td><td colspan="2">{codigo} - PROCEDIMENTO TESTE</td><td colspan="2">OPERADOR FICTICIO</td><td>{status}</td></tr>'
        tabela+='''<tr><td class="td_titulo_tabela" colspan="6">Troca de número(s) AIH</td></tr>
            <tr><td>CID</td><td>Procedimento</td><td>Solicitante</td><td>Status</td></tr>
            <tr><td>TESTE</td><td>0409040193</td><td>TESTE</td><td>Aprovada</td></tr>
            <tr><td class="td_titulo_tabela" colspan="6">Observações gerais</td></tr>
            <tr><td colspan="6">Troca de Procedimentos: 0409040193 Aprovada</td></tr>'''
        self.page.evaluate('''html=>{mostrarFicha('123456');
            document.querySelector('#fichaInternacao tbody').insertAdjacentHTML('beforeend',html);}''',tabela)

    def test_troca_aprovada_substitui_inicial_e_repeticoes_sao_deduplicadas(self):
        for linhas in ([('0409040193',' Aprovada ')],
                       [('0409040193','Aprovada'),('0409040193','APROVADA')]):
            with self.subTest(linhas=linhas):
                self._ficha_com_trocas(linhas)
                r=obter_detalhes(self.page,AIH,'0409040193')
                self.assertEqual((r.situacao,r.procedimento,r.procedimento_original,r.origem_procedimento),
                    ('FICHA_CONFERIDA','0409040193',PROC,'troca_aprovada'))
                # O código inicial deixa de ser o vigente depois da troca aprovada.
                r=obter_detalhes(self.page,AIH,PROC)
                self.assertEqual(r.situacao,'PROCEDIMENTO_DIVERGENTE')

    def test_so_status_exatamente_aprovada_e_usado(self):
        self._ficha_com_trocas([('0409040193',s) for s in ('Pendente','Recusada','Não aprovada','Aprovada parcialmente')])
        r=obter_detalhes(self.page,AIH,PROC)
        self.assertEqual((r.situacao,r.procedimento,r.origem_procedimento),('FICHA_CONFERIDA',PROC,'inicial'))
        self.assertEqual(r.procedimento_original,PROC)

    def test_trocas_conflitantes_ou_codigo_invalido_exigem_revisao(self):
        for linhas in ([('0409040193','Aprovada'),('0408050063','Aprovada')],
                       [('SEM CODIGO','Aprovada')],
                       [('0409040193','Aprovada'),('SEM CODIGO','Aprovada')]):
            with self.subTest(linhas=linhas):
                self._ficha_com_trocas(linhas)
                r=obter_detalhes(self.page,AIH,PROC)
                self.assertEqual(r.situacao,'PROCEDIMENTO_NAO_CONFIRMADO_TROCAS')
                self.assertEqual((r.procedimento,r.carater,r.solicitacao),('','',''))

    def test_troca_nao_elimina_confirmacao_final_da_aih(self):
        self._ficha_com_trocas([('0409040193','Aprovada')])
        from sisreg_hospital import _trocas_por_rotulo
        def ler_e_trocar_ficha(frame):
            resposta=_trocas_por_rotulo(frame)
            self.page.locator('#fichaInternacao b').nth(1).evaluate('(e)=>e.textContent="900000000099-9"')
            return resposta
        with patch('sisreg_hospital._trocas_por_rotulo',side_effect=ler_e_trocar_ficha):
            r=obter_detalhes(self.page,AIH,'0409040193')
        self.assertEqual(r.situacao,'AIH_NAO_COMPROVADA_FICHA')
        self.assertEqual(r.procedimento,'')
