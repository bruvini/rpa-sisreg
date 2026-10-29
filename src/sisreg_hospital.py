"""Consulta hospitalar SISREG por CNS e AIH EXATA. Sem alterar solicitações.

Seletores de detalhe são provisórios: preenchimento só com 1 linha AIH e
ficha cuja AIH corresponda. Quando a tela difere, registra pendência.
"""
from __future__ import annotations
from dataclasses import dataclass
import unicodedata
import re
import time
import hashlib
from aih_extract import normalizar_aih, digitos
from sisreg_navigation import origem_autorizada, _encontrar, NavegacaoInesperada

MENU_HOSP = '#barraMenu > ul > li > a:has-text("consulta hosp")'
OPCAO_HOSP = '#barraMenu a[href="/cgi-bin/cons_aih"][target="f_principal"]'
CAMPO_CNS = '#main_page input[name="cns"][type="text"][maxlength="15"]'
BTN_PESQUISAR = '#main_page input[name="enviar"][type="button"][onclick^="pesquisar("]'
LINHAS_RESULTADOS = 'table.table_listagem tr.linha_selecionavel[onclick^="mostrarFicha("]'
CABECALHO_RESULTADOS = 'table.table_listagem .td_titulo_tabela'
FICHA = '#fichaInternacao'
# Codigo de solicitacao tem rotulo na celula de cabecalho, sem depender de tr.
# Carater e procedimento sao identificados pelo par cabeçalho + proxima linha.
CODIGO_SOLICITACAO = '#fichaInternacao > table > tbody > tr:first-child > td:first-child > b'
PAGINADOR_PROXIMO = 'a[onclick^="exibirPagina("]:has(img[alt="Proxima"][src*="seta_direita.png"])'
MAX_PAGINAS_RESULTADO = 100


class AIHNaoEncontrada(Exception):
    """Busca completa nas páginas disponíveis; não comprova inexistência no SISREG."""



@dataclass(frozen=True)
class ResultadoHospital:
    situacao: str
    detalhe: str = ''
    carater: str = ''
    autorizador: str = ''
    procedimento: str = ''
    solicitacao: str = ''


def obter_carater(texto: str) -> str:
    t = (texto or '').strip().upper()
    # Um código isolado ou precedendo a descrição: sem adivinhar valores.
    achado = re.search(r'(?<!\d)(\d{1,2})(?!\d)\s*(?:[-–:]\s*[A-ZÁÉÍÓÚ]|$)', t)
    if achado:
        return achado.group(1).zfill(2)
    if re.fullmatch(r'\d{1,2}', t):
        return t.zfill(2)
    return ''


def obter_autorizador(texto: str) -> str:
    t = (texto or '').strip()
    # Exige um único bloco numérico e evita confundir data ou rótulos.
    numeros = re.findall(r'(?<!\d)\d{4,20}(?!\d)', t)
    return numeros[0] if len(numeros) == 1 else ''


def obter_procedimento(texto: str) -> str:
    codigos = re.findall(r'(?<!\d)\d{10}(?!\d)', texto or '')
    return codigos[0] if len(set(codigos)) == 1 and codigos else ''


def _quadros_oficiais(pagina):
    for frame in getattr(pagina, 'frames', [pagina]):
        try:
            origem_autorizada(frame)
            yield frame
        except (NavegacaoInesperada, ValueError):
            continue


def _formulario_hospitalar(pagina, tempo=8000):
    """Confirma o formulario de solicitacoes dentro do quadro oficial."""
    frame, campo = _encontrar(pagina, CAMPO_CNS, tempo=tempo)
    origem_autorizada(frame)
    # Evita reutilizar campo cns de outra tela da aplicacao.
    if (campo.get_attribute('name') or '').lower() != 'cns':
        raise NavegacaoInesperada('Campo CNS nao pertence ao formulario esperado.')
    frame_botao, botao = _encontrar(pagina, BTN_PESQUISAR, tempo=tempo)
    if frame_botao is not frame:
        raise NavegacaoInesperada('Botao e campo CNS estao em quadros diferentes.')
    if ((botao.get_attribute('type') or '').lower() != 'button' or
            (botao.get_attribute('name') or '').lower() != 'enviar'):
        raise NavegacaoInesperada('Botao Pesquisar nao corresponde ao esperado.')
    return frame, campo, botao


def abrir_pesquisa_hospitalar(pagina):
    origem_autorizada(pagina)
    try:
        return _formulario_hospitalar(pagina, tempo=900)[0]
    except NavegacaoInesperada:
        pass
    # Consulta Hosp > Solicitacoes (href oficial informado pelo operador).
    _, menu = _encontrar(pagina, MENU_HOSP, tempo=10000)
    menu.hover(timeout=8000)
    _, opcao = _encontrar(pagina, OPCAO_HOSP, tempo=10000)
    origem_autorizada(pagina)
    opcao.click(timeout=12000, no_wait_after=True)
    return _formulario_hospitalar(pagina, tempo=21000)[0]


def pesquisar_por_cns(pagina, cns: str):
    if not (cns.isdigit() and len(cns) == 15):
        raise NavegacaoInesperada('CNS sem 15 digitos. Busca hospitalar nao iniciada.')
    abrir_pesquisa_hospitalar(pagina)
    frame, campo, botao = _formulario_hospitalar(pagina, tempo=9000)
    # Preencher e pesquisar no mesmo iframe, sem usar valores de outra pagina.
    origem_autorizada(frame)
    campo.fill(cns, timeout=8000)
    origem_autorizada(frame)
    botao.click(timeout=14000, no_wait_after=True)

def _ler_tabela_de_resultados(pagina):
    """Le somente linhas selecionaveis da tabela RESULTADOS DA PESQUISA.

    A AIH deve estar na 6a coluna da linha que contem mostrarFicha(...).
    """
    for frame in _quadros_oficiais(pagina):
        try:
            trs = frame.locator(LINHAS_RESULTADOS)
            if hasattr(trs, 'evaluate_all'):
                dados = trs.evaluate_all("""rows => rows.slice(0,750).map((tr,i)=>({
                    indice:i, textos:Array.from(tr.querySelectorAll(':scope > td'))
                        .map(el=>(el.innerText||'').trim()),
                    acao:tr.getAttribute('onclick')||''
                }))""", timeout=7000)
                linhas = []
                for dado in dados:
                    textos = tuple(dado['textos'])
                    if (len(textos) == 7 and
                            normalizar_aih(textos[5]) and
                            re.fullmatch(r"\s*mostrarFicha\(['\"]\d+['\"]\)\s*;?\s*",
                                         dado['acao'])):
                        linhas.append((trs.nth(dado['indice']), textos))
            else:
                linhas = []
                for i in range(min(trs.count(),750)):
                    tr = trs.nth(i)
                    td = tr.locator('td')
                    textos = tuple(v.strip() for v in td.all_inner_texts())
                    acao = tr.get_attribute('onclick') if hasattr(tr,'get_attribute') else "mostrarFicha('1')"
                    if (len(textos)==7 and normalizar_aih(textos[5]) and
                            re.fullmatch(r"\s*mostrarFicha\(['\"]\d+['\"]\)\s*;?\s*",acao or '')):
                        linhas.append((tr,textos))
            if linhas:
                assinatura = hashlib.sha256(
                    repr([textos for _,textos in linhas]).encode('utf-8')).hexdigest()
                return frame, linhas, assinatura
        except Exception:
            continue
    return None, [], None

def _link_proxima_pagina(frame):
    """Usa apenas a seta Proxima aninhada em exibirPagina(...) no quadro oficial."""
    try:
        imagens = frame.locator(PAGINADOR_PROXIMO)
        qtd = imagens.count()
        if qtd == 0:
            return None
        if qtd != 1:
            raise NavegacaoInesperada('Mais de um botao Proxima: paginacao ambigua.')
        link = imagens.first if hasattr(imagens,'first') else imagens.nth(0)
        if not link.is_visible() or not link.is_enabled():
            raise NavegacaoInesperada('Botao Proxima indisponivel; pagina nao confirmada.')
        acao=link.get_attribute('onclick') or ''
        if not re.match(r"^\s*exibirPagina\(\s*\d+\s*,\s*\d+\s*\)",acao):
            raise NavegacaoInesperada('Acao do paginador fora do padrao esperado.')
        return link
    except NavegacaoInesperada:
        raise
    except Exception as exc:
        raise NavegacaoInesperada('Nao foi possivel validar o paginador.') from exc

def selecionar_linha_aih(pagina, aih: str, espera_ms: int = 15000, observador=None, cancelar=None):
    """Busca AIH exata em TODAS as páginas acessíveis de resultados.

    Sem próximo link, só conclui ausência após visitar a última página.
    Se não for possível confirmar avanço/última página, deixa pendência técnica.
    """
    procurada = normalizar_aih(aih)
    if not procurada:
        raise NavegacaoInesperada('AIH inválida para pesquisa hospitalar.')
    fim = time.monotonic() + espera_ms / 1000
    frame = None
    linhas = []
    assinatura = None
    while time.monotonic() < fim:
        _verificar_interrupcao(cancelar)
        frame, linhas, assinatura = _ler_tabela_de_resultados(pagina)
        if linhas:
            break
        time.sleep(.35)
    if not linhas:
        raise NavegacaoInesperada('Tabela de resultados não disponível; busca inconclusiva.')
    visitadas = set()
    for numero_pagina in range(1, MAX_PAGINAS_RESULTADO + 1):
        _verificar_interrupcao(cancelar)
        if assinatura in visitadas:
            raise NavegacaoInesperada('Paginação repetida; não foi possível concluir a busca.')
        visitadas.add(assinatura)
        encontrados = []
        for tr, textos in linhas:
            if len(textos)==7 and normalizar_aih(textos[5]) == procurada:
                encontrados.append(tr)
        if len(encontrados) > 1:
            raise NavegacaoInesperada('AIH repetida na página; não foi aberta automaticamente.')
        if len(encontrados) == 1:
            tr=encontrados[0]
            if not tr.is_visible():
                raise NavegacaoInesperada('Linha da AIH nao esta visivel.')
            # O evento de abertura esta na TR (onclick mostrarFicha).
            origem_autorizada(frame)
            tr.click(timeout=12000,no_wait_after=True)
            return
        if observador:
            observador('PAGINA_RESULTADOS','OK',0.0,'NENHUM')
        proxima = _link_proxima_pagina(frame)
        if proxima is None:
            raise AIHNaoEncontrada('AIH não encontrada nas páginas de resultados consultadas.')
        try:
            origem_autorizada(frame)
            proxima.click(timeout=12000,no_wait_after=True)
        except Exception as exc:
            raise NavegacaoInesperada('Não foi possível avançar a página de resultados.') from exc
        limite = time.monotonic() + 12
        atualizada = False
        while time.monotonic() < limite:
            _verificar_interrupcao(cancelar)
            novo_frame, novas_linhas, nova_assinatura = _ler_tabela_de_resultados(pagina)
            if novas_linhas and nova_assinatura != assinatura:
                frame, linhas, assinatura = novo_frame, novas_linhas, nova_assinatura
                atualizada = True
                break
            time.sleep(.3)
        if not atualizada:
            raise NavegacaoInesperada('Página seguinte não foi confirmada; busca inconclusiva.')
    raise NavegacaoInesperada('Limite de páginas alcançado; busca inconclusiva.')


def _verificar_interrupcao(cancelar):
    if cancelar is not None and cancelar():
        raise NavegacaoInesperada('Consulta interrompida pelo operador.')


def _paginas_para_ficha(pagina):
    """Pesquisa somente páginas oficiais da sessão, incluindo popups."""
    contexto = getattr(pagina, 'context', None)
    try:
        paginas = list(contexto.pages) if contexto is not None else []
    except Exception:
        paginas = []
    if pagina not in paginas:
        paginas.append(pagina)
    for candidata in reversed(paginas):
        try:
            if getattr(candidata, 'is_closed', lambda: False)():
                continue
            origem_autorizada(candidata)
            yield candidata
        except (NavegacaoInesperada, ValueError):
            continue


def _localizar_ficha_da_aih(pagina, aih: str, espera_ms: int = 16000, cancelar=None):
    """Não confunde ficha antiga com a AIH buscada, nem depende da janela."""
    procurada = normalizar_aih(aih)
    if not procurada:
        return None, 'AIH_NAO_COMPROVADA_FICHA'
    fim = time.monotonic() + max(0, espera_ms) / 1000
    outra_ficha = False
    while True:
        _verificar_interrupcao(cancelar)
        for candidata in _paginas_para_ficha(pagina):
            try:
                frame, ficha = _encontrar(candidata, FICHA, tempo=350)
                origem_autorizada(frame)
                texto = ficha.inner_text(timeout=1800)
            except Exception:
                continue
            outra_ficha = True
            numeros = re.findall(r'(?<!\d)\d{12}-?\d(?!\d)', texto)
            if procurada in {normalizar_aih(v) for v in numeros}:
                return frame, ''
        if time.monotonic() >= fim:
            break
        time.sleep(.25)
    return None, ('AIH_NAO_COMPROVADA_FICHA' if outra_ficha else 'FICHA_NAO_ABERTA')


def _texto_campo_ficha(frame, seletor):
    try:
        _, local = _encontrar(frame, seletor, tempo=450)
        return local.inner_text(timeout=1200).strip()
    except Exception:
        return ''


def _normalizar_rotulo(texto):
    texto = unicodedata.normalize('NFD', str(texto or '').upper())
    texto = ''.join(ch for ch in texto if unicodedata.category(ch) != 'Mn')
    return ' '.join(texto.strip(' :\t\r\n').split())


def _extrair_campos_de_linhas(linhas):
    """Le campos por cabecalhos do SISREG e a linha seguinte, nao por indice.

    Cada entrada eh uma lista de textos de TDs da mesma TR. O cabecalho de
    carater fica ao lado de Classificacao de Risco; procedimento solicitado
    fica ao lado de Codigo. O valor e lido APENAS da linha imediatamente
    seguinte e na coluna correspondente. Duplicidade gera campo vazio.
    """
    candidatos = {'carater':set(),'solicitacao':set(),'procedimento':set()}
    if not isinstance(linhas, (list,tuple)):
        return '', '', ''
    for pos, valores in enumerate(linhas[:160]):
        if not isinstance(valores,(list,tuple)) or not valores:
            continue
        rotulos = [_normalizar_rotulo(c) for c in valores]
        primeiro = rotulos[0]
        segundo = rotulos[1] if len(rotulos)>1 else ''
        if primeiro.startswith('CODIGO SOLICITACAO'):
            # O primeiro TD e um texto da forma Codigo Solicitacao: <b>numero</b>.
            trecho = re.sub(r'^CODIGO SOLICITACAO\s*:?\s*', '', primeiro)
            codigo = obter_autorizador(trecho)
            if codigo:
                candidatos['solicitacao'].add(codigo)
        if pos + 1 >= len(linhas):
            continue
        seguintes = linhas[pos + 1]
        if not isinstance(seguintes,(list,tuple)) or not seguintes:
            continue
        if primeiro == 'CARATER' and segundo == 'CLASSIFICACAO DE RISCO':
            codigo = obter_carater(seguintes[0])
            if codigo:
                candidatos['carater'].add(codigo)
        if primeiro == 'PROCEDIMENTO SOLICITADO' and segundo == 'CODIGO' and len(seguintes)>1:
            # Texto da primeira celula identifica o procedimento; segunda e SIGTAP.
            if str(seguintes[0]).strip():
                codigo = obter_procedimento(seguintes[1])
                if codigo:
                    candidatos['procedimento'].add(codigo)
    def unico(chave):
        valores=candidatos[chave]
        return next(iter(valores)) if len(valores)==1 else ''
    return unico('carater'), unico('solicitacao'), unico('procedimento')


def _campos_por_rotulo(frame):
    """Captura, uma vez por tentativa, somente TDs do #fichaInternacao."""
    try:
        trs = frame.locator('#fichaInternacao > table > tbody > tr')
        # Um unico acesso a pagina evita dezenas de esperas do Playwright.
        linhas = trs.evaluate_all("""rows => rows.slice(0,160).map(tr =>
          Array.from(tr.children).filter(el=>el.tagName==='TD')
            .map(el=>(el.innerText||'').trim())
        )""", timeout=4000)
        return _extrair_campos_de_linhas(linhas)
    except Exception:
        return '', '', ''


def _ler_tres_campos(frame, cancelar=None, espera_ms=8500):
    """Aguarda a ficha e valida campos apenas por seus rotulos semanticos."""
    fim = time.monotonic() + espera_ms / 1000
    achou_algum = False
    while True:
        _verificar_interrupcao(cancelar)
        origem_autorizada(frame)
        valores = _campos_por_rotulo(frame)
        achou_algum |= any(bool(x) for x in valores)
        if all(valores):
            return valores, ''
        if time.monotonic() >= fim:
            return None, ('CAMPOS_FICHA_INCOMPLETOS' if achou_algum
                          else 'CAMPOS_FICHA_NAO_CONFIRMADOS')
        time.sleep(.3)

def obter_detalhes(pagina, aih: str, procedimento_hospital: str = '',
                   espera_ficha_ms: int = 16000, cancelar=None) -> ResultadoHospital:
    frame, falha = _localizar_ficha_da_aih(pagina, aih, espera_ms=espera_ficha_ms,
                                          cancelar=cancelar)
    if falha == 'FICHA_NAO_ABERTA':
        return ResultadoHospital('FICHA_NAO_ABERTA', 'Ficha não apareceu após clicar na AIH.')
    if falha:
        return ResultadoHospital('AIH_NAO_COMPROVADA_FICHA',
                                 'Nenhuma ficha confirmou a AIH selecionada.')
    campos, erro = _ler_tres_campos(frame, cancelar=cancelar)
    if erro:
        return ResultadoHospital(erro,
                                 'A ficha abriu, mas os três campos não foram validados.')
    carater, solicitacao, procedimento = campos
    # Um carregamento tardio não pode misturar dados da ficha anterior.
    _verificar_interrupcao(cancelar)
    try:
        _, ficha = _encontrar(frame, FICHA, tempo=450)
        numeros = re.findall(r'(?<!\d)\d{12}-?\d(?!\d)', ficha.inner_text(timeout=1600))
        if normalizar_aih(aih) not in {normalizar_aih(v) for v in numeros}:
            return ResultadoHospital('AIH_NAO_COMPROVADA_FICHA',
                                     'A ficha mudou durante a leitura; dados descartados.')
    except Exception:
        return ResultadoHospital('AIH_NAO_COMPROVADA_FICHA',
                                 'A ficha não pôde ser validada ao finalizar a leitura.')
    esperado = digitos(procedimento_hospital)
    if len(esperado) != 10:
        return ResultadoHospital('PROCEDIMENTO_NAO_CONFIRMADO',
                                 'Procedimento do hospital indisponível; comparação pendente.',
                                 carater, '', procedimento, solicitacao)
    if esperado != procedimento:
        return ResultadoHospital('PROCEDIMENTO_DIVERGENTE',
                                 'O procedimento da ficha difere do informado pelo hospital.',
                                 carater, '', procedimento, solicitacao)
    return ResultadoHospital('FICHA_CONFERIDA',
                             'AIH exata e procedimento compatível com o hospital.',
                             carater, '', procedimento, solicitacao)


def consultar_solicitacao_hospitalar(pagina, cns: str, aih: str,
                                   procedimento: str = '', observador=None, cancelar=None) -> ResultadoHospital:
    """Consulta por etapas, com telemetria restrita a códigos SEM dados de pacientes."""
    for acao, funcao in (
        ('BUSCA_HOSPITALAR', lambda: pesquisar_por_cns(pagina, cns)),
        ('AIH_EXATA', lambda: selecionar_linha_aih(
            pagina, aih, observador=observador, cancelar=cancelar)
            if cancelar is not None else selecionar_linha_aih(
                pagina, aih, observador=observador)),
        ('LEITURA_FICHA', lambda: obter_detalhes(
            pagina, aih, procedimento, cancelar=cancelar)
            if cancelar is not None else obter_detalhes(pagina, aih, procedimento))):
        _verificar_interrupcao(cancelar)
        inicio = time.perf_counter()
        try:
            resultado = funcao()
        except AIHNaoEncontrada:
            resultado = ResultadoHospital('AIH_NAO_LOCALIZADA_PAGINAS',
                'AIH não encontrada após percorrer as páginas disponíveis; confirmar em consulta oficial.')
            if observador:
                observador(acao, 'PENDENCIA', time.perf_counter()-inicio, 'AIH_NAO_LOCALIZADA_PAGINAS')
            return resultado
        except Exception:
            if observador:
                observador(acao, 'ERRO', time.perf_counter()-inicio,
                           'SELETOR_NAO_ENCONTRADO')
            raise
        if observador:
            situacao = 'OK'
            categoria = 'NENHUM'
            if acao == 'LEITURA_FICHA' and resultado.situacao not in ('FICHA_CONFERIDA', 'PROCEDIMENTO_DIVERGENTE'):
                situacao = 'PENDENCIA'
                categoria = {
                    'FICHA_NAO_ABERTA':'FICHA_NAO_ABERTA',
                    'AIH_NAO_COMPROVADA_FICHA':'AIH_NAO_CONFIRMADA',
                    'CAMPOS_FICHA_NAO_CONFIRMADOS':'SELETOR_NAO_ENCONTRADO',
                    'CAMPOS_FICHA_INCOMPLETOS':'CAMPOS_FICHA_INCOMPLETOS',
                    'PROCEDIMENTO_NAO_CONFIRMADO':'CAMPOS_FICHA_INCOMPLETOS',
                }.get(resultado.situacao, 'ERRO_NAO_CLASSIFICADO')
            observador(acao, situacao, time.perf_counter()-inicio, categoria)
    return resultado
