"""Consulta hospitalar SISREG por CNS e AIH EXATA. Sem alterar solicitações.

Seletores de detalhe são provisórios: preenchimento só com 1 linha AIH e
ficha cuja AIH corresponda. Quando a tela difere, registra pendência.
"""
from __future__ import annotations
from dataclasses import dataclass
import re
import time
import hashlib
from aih_extract import normalizar_aih, digitos
from sisreg_navigation import origem_autorizada, _encontrar, NavegacaoInesperada

MENU_HOSP = 'xpath=//*[@id="barraMenu"]/ul/li[5]/a'
OPCAO_HOSP = 'xpath=//*[@id="barraMenu"]/ul/li[5]/ul/li[1]/a'
CAMPO_CNS = 'xpath=//*[@id="main_page"]/form/center[1]/table/tbody/tr[3]/td[2]/input'
BTN_PESQUISAR = 'input[name="enviar"][type="button"][onclick*="pesquisar"]'
FICHA = '#fichaInternacao'
# Seletores confirmados na ficha em 29/10/2026.
CARATER = '#fichaInternacao > table > tbody > tr:nth-child(46) > td:nth-child(1)'
# Código da solicitação não é necessariamente o código autorizador.
CODIGO_SOLICITACAO = '#fichaInternacao > table > tbody > tr:nth-child(1) > td:nth-child(1) > b'
# Sem seletor independente validado, não inferir o código autorizador.
PROCEDIMENTO = '#fichaInternacao > table > tbody > tr:nth-child(50) > td:nth-child(2)'
PAGINADOR_PROXIMO = '#main_page > form > center:nth-child(9) > table > tbody > tr > td > a > img'
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


def abrir_pesquisa_hospitalar(pagina):
    origem_autorizada(pagina)
    try:
        _encontrar(pagina, CAMPO_CNS, tempo=1100)
        return
    except NavegacaoInesperada:
        pass
    _, menu = _encontrar(pagina, MENU_HOSP, tempo=10000)
    menu.hover(timeout=8000)
    _, opcao = _encontrar(pagina, OPCAO_HOSP, tempo=9000)
    opcao.click(timeout=9000, no_wait_after=True)
    _encontrar(pagina, CAMPO_CNS, tempo=21000)


def pesquisar_por_cns(pagina, cns: str):
    if not (cns.isdigit() and len(cns) == 15):
        raise NavegacaoInesperada('CNS sem 15 dígitos. Consulta hospitalar não iniciada.')
    abrir_pesquisa_hospitalar(pagina)
    _, campo = _encontrar(pagina, CAMPO_CNS, tempo=10000)
    _, botao = _encontrar(pagina, [BTN_PESQUISAR, 'xpath=//*[@id="main_page"]//input[@name="enviar"]'], tempo=9000)
    if (campo.get_attribute('type') or 'text').lower() not in ('text','search'):
        raise NavegacaoInesperada('Campo de CNS inesperado.')
    if (botao.get_attribute('type') or '').lower() != 'button':
        raise NavegacaoInesperada('Botão Pesquisar inesperado.')
    origem_autorizada(pagina)
    campo.fill(cns, timeout=8000)
    botao.click(timeout=14000, no_wait_after=True)


def _ler_tabela_de_resultados(pagina):
    """Lê só a lista de resultados em quadros do domínio oficial.

    O fingerprint é efêmero e nunca vai para logs (nem é persistido).
    """
    for frame in _quadros_oficiais(pagina):
        try:
            trs = frame.locator('#main_page table tr')
            n = min(trs.count(), 750)
            linhas = []
            for i in range(n):
                tr = trs.nth(i)
                celulas = tr.locator('td')
                if celulas.count() < 4:
                    continue
                textos = tuple(v.strip() for v in celulas.all_inner_texts())
                # O formulário de pesquisa também possui tabelas; só considerar
                # a tabela de solicitações se a linha contiver uma AIH de 13 dígitos.
                if any(normalizar_aih(v) for v in textos):
                    linhas.append((tr, textos))
            if linhas:
                assinatura = hashlib.sha256(repr([t for _, t in linhas]).encode('utf-8')).hexdigest()
                return frame, linhas, assinatura
        except Exception:
            continue
    return None, [], None


def _link_proxima_pagina(frame):
    """Reconhece a flecha do SISREG; não clica em voltar ou em paginação ambígua."""
    try:
        imagens = frame.locator(PAGINADOR_PROXIMO)
        qtd = imagens.count()
    except Exception as exc:
        raise NavegacaoInesperada('Não foi possível verificar a paginação.') from exc
    if not qtd:
        return None
    candidatas = []
    for i in range(min(qtd, 12)):
        img = imagens.nth(i)
        try:
            if not img.is_visible():
                continue
            link = img.locator('xpath=..')
            if not link.is_visible() or not link.is_enabled():
                continue
            texto = ' '.join((img.get_attribute(k) or '') for k in ('alt','title','src'))
            texto += ' ' + ' '.join((link.get_attribute(k) or '') for k in ('title','aria-label','class'))
            texto = texto.lower()
            if any(k in texto for k in ('anterior','previous','prev','voltar','left','esquerda','disabled','inativo')):
                continue
            explicito = any(k in texto for k in ('próxim','proxim','next','avanç','avanc','right','direita'))
            candidatas.append((link, explicito))
        except Exception as exc:
            raise NavegacaoInesperada('Controle de paginação inesperado.') from exc
    explicitas = [link for link, exp in candidatas if exp]
    if len(explicitas) == 1:
        return explicitas[0]
    if len(candidatas) == 1 and qtd == 1:
        # O seletor fornecido aponta diretamente para a flecha seguinte.
        return candidatas[0][0]
    if candidatas:
        raise NavegacaoInesperada('Paginação ambígua; não foi possível determinar a próxima página.')
    return None


def selecionar_linha_aih(pagina, aih: str, espera_ms: int = 15000, observador=None):
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
        frame, linhas, assinatura = _ler_tabela_de_resultados(pagina)
        if linhas:
            break
        time.sleep(.35)
    if not linhas:
        raise NavegacaoInesperada('Tabela de resultados não disponível; busca inconclusiva.')
    visitadas = set()
    for numero_pagina in range(1, MAX_PAGINAS_RESULTADO + 1):
        if assinatura in visitadas:
            raise NavegacaoInesperada('Paginação repetida; não foi possível concluir a busca.')
        visitadas.add(assinatura)
        encontrados = []
        for tr, textos in linhas:
            posicoes = [j for j,v in enumerate(textos) if normalizar_aih(v) == procurada]
            if len(posicoes) == 1:
                encontrados.append((tr,posicoes[0]))
        if len(encontrados) > 1:
            raise NavegacaoInesperada('AIH repetida na página; não foi aberta automaticamente.')
        if len(encontrados) == 1:
            tr,pos=encontrados[0]
            alvo=tr.locator('td').nth(pos)
            if not alvo.is_visible():
                raise NavegacaoInesperada('Célula da AIH encontrada não está visível.')
            alvo.click(timeout=12000,no_wait_after=True)
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
            novo_frame, novas_linhas, nova_assinatura = _ler_tabela_de_resultados(pagina)
            if novas_linhas and nova_assinatura != assinatura:
                frame, linhas, assinatura = novo_frame, novas_linhas, nova_assinatura
                atualizada = True
                break
            time.sleep(.3)
        if not atualizada:
            raise NavegacaoInesperada('Página seguinte não foi confirmada; busca inconclusiva.')
    raise NavegacaoInesperada('Limite de páginas alcançado; busca inconclusiva.')


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


def _localizar_ficha_da_aih(pagina, aih: str, espera_ms: int = 16000):
    """Não confunde ficha antiga com a AIH buscada, nem depende da janela."""
    procurada = normalizar_aih(aih)
    if not procurada:
        return None, 'AIH_NAO_COMPROVADA_FICHA'
    fim = time.monotonic() + max(0, espera_ms) / 1000
    outra_ficha = False
    while True:
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


def obter_detalhes(pagina, aih: str, procedimento_hospital: str = '',
                   espera_ficha_ms: int = 16000) -> ResultadoHospital:
    frame, falha = _localizar_ficha_da_aih(pagina, aih, espera_ms=espera_ficha_ms)
    if falha == 'FICHA_NAO_ABERTA':
        return ResultadoHospital('FICHA_NAO_ABERTA',
                                 'A ficha de internação não apareceu após selecionar a AIH.')
    if falha:
        return ResultadoHospital('AIH_NAO_COMPROVADA_FICHA',
                                 'Nenhuma ficha aberta comprovou a AIH pesquisada.')
    try:
        # Ler campos do mesmo quadro cuja AIH foi confirmada.
        _, campo_carater = _encontrar(frame, CARATER, tempo=2500)
        _, campo_solic = _encontrar(frame, CODIGO_SOLICITACAO, tempo=2500)
        _, campo_proc = _encontrar(frame, PROCEDIMENTO, tempo=2500)
        carater = obter_carater(campo_carater.inner_text(timeout=3000))
        solicitacao = obter_autorizador(campo_solic.inner_text(timeout=3000))
        procedimento = obter_procedimento(campo_proc.inner_text(timeout=3000))
    except Exception:
        return ResultadoHospital('CAMPOS_FICHA_NAO_CONFIRMADOS',
                                 'Seletores de caráter, solicitação ou procedimento não confirmados.')
    if not carater or not solicitacao or not procedimento:
        return ResultadoHospital('CAMPOS_FICHA_INCOMPLETOS',
                                 'Caráter, solicitação ou procedimento não extraídos com segurança.')
    esperado = digitos(procedimento_hospital)
    if len(esperado) != 10:
        return ResultadoHospital('PROCEDIMENTO_NAO_CONFIRMADO',
                                 'Procedimento hospitalar ausente/inválido: comparação não realizada.',
                                 carater, '', procedimento, solicitacao)
    if esperado != procedimento:
        return ResultadoHospital('PROCEDIMENTO_DIVERGENTE',
                                 'Procedimento da ficha difere do informado pelo hospital.',
                                 carater, '', procedimento, solicitacao)
    return ResultadoHospital('FICHA_CONFERIDA',
                             'AIH exata localizada e procedimento compatível.',
                             carater, '', procedimento, solicitacao)


def consultar_solicitacao_hospitalar(pagina, cns: str, aih: str,
                                   procedimento: str = '', observador=None) -> ResultadoHospital:
    """Consulta por etapas, com telemetria restrita a códigos SEM dados de pacientes."""
    for acao, funcao in (
        ('BUSCA_HOSPITALAR', lambda: pesquisar_por_cns(pagina, cns)),
        ('AIH_EXATA', lambda: selecionar_linha_aih(pagina, aih, observador=observador)),
        ('LEITURA_FICHA', lambda: obter_detalhes(pagina, aih, procedimento))):
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
