"""Consulta hospitalar SISREG por CNS e AIH EXATA. Sem alterar solicitações.

Seletores de detalhe são provisórios: preenchimento só com 1 linha AIH e
ficha cuja AIH corresponda. Quando a tela difere, registra pendência.
"""
from __future__ import annotations
from dataclasses import dataclass
import re
import time
from aih_extract import normalizar_aih, digitos
from sisreg_navigation import origem_autorizada, _encontrar, NavegacaoInesperada

MENU_HOSP = 'xpath=//*[@id="barraMenu"]/ul/li[5]/a'
OPCAO_HOSP = 'xpath=//*[@id="barraMenu"]/ul/li[5]/ul/li[1]/a'
CAMPO_CNS = 'xpath=//*[@id="main_page"]/form/center[1]/table/tbody/tr[3]/td[2]/input'
BTN_PESQUISAR = 'input[name="enviar"][type="button"][onclick*="pesquisar"]'
FICHA = '#fichaInternacao'
CARATER = 'xpath=//*[@id="fichaInternacao"]/table/tbody/tr[44]/td[1]'
AUTORIZADOR = 'xpath=//*[@id="fichaInternacao"]/table/tbody/tr[1]/td[1]/b'
PROCEDIMENTO = 'xpath=//*[@id="fichaInternacao"]/table/tbody/tr[48]/td[2]'


@dataclass(frozen=True)
class ResultadoHospital:
    situacao: str
    detalhe: str = ''
    carater: str = ''
    autorizador: str = ''
    procedimento: str = ''


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


def selecionar_linha_aih(pagina, aih: str, espera_ms: int = 15000):
    """Seleciona APENAS uma linha cujo TD contém AIH exata (hífen ignorado).

    Nunca escolhe tr[4], outro paciente ou primeira linha por conveniência.
    """
    procurada = normalizar_aih(aih)
    if not procurada:
        raise NavegacaoInesperada('AIH inválida para pesquisa hospitalar.')
    fim = time.monotonic() + espera_ms / 1000
    while time.monotonic() < fim:
        encontrados = []
        for frame in _quadros_oficiais(pagina):
            try:
                trs = frame.locator('#main_page table tr')
                n = min(trs.count(), 750)
                for i in range(n):
                    tr = trs.nth(i)
                    celulas = tr.locator('td')
                    if celulas.count() < 4:
                        continue
                    textos = [v.strip() for v in celulas.all_inner_texts()]
                    posicoes = [j for j, v in enumerate(textos) if normalizar_aih(v) == procurada]
                    if len(posicoes) == 1:
                        encontrados.append((tr, posicoes[0]))
            except Exception:
                continue
        if len(encontrados) == 1:
            tr, pos = encontrados[0]
            td = tr.locator('td')
            # Se a AIH estiver clicável, usa esse TD; alguns layouts usam TD6.
            alvo = td.nth(pos)
            if not alvo.is_visible():
                raise NavegacaoInesperada('AIH encontrada, mas célula não está visível.')
            alvo.click(timeout=12000, no_wait_after=True)
            return
        if len(encontrados) > 1:
            raise NavegacaoInesperada('AIH aparece em mais de uma linha; não foi aberta automaticamente.')
        time.sleep(.35)
    raise NavegacaoInesperada('AIH não localizada de modo inequívoco na tabela consultada.')


def obter_detalhes(pagina, aih: str, procedimento_hospital: str = '') -> ResultadoHospital:
    try:
        frame, ficha = _encontrar(pagina, FICHA, tempo=16000)
    except NavegacaoInesperada:
        return ResultadoHospital('FICHA_NAO_ABERTA', 'A ficha de internação não apareceu após selecionar a AIH.')
    origem_autorizada(frame)
    texto = ficha.inner_text(timeout=9000)
    procurada = normalizar_aih(aih)
    # O número precisa estar no detalhe, independentemente da linha selecionada.
    numeros = re.findall(r'(?<!\d)\d{12}-?\d(?!\d)', texto)
    if procurada not in {normalizar_aih(v) for v in numeros}:
        return ResultadoHospital('AIH_NAO_COMPROVADA_FICHA', 'AIH não aparece identificável na ficha aberta.')
    try:
        _, campo_carater = _encontrar(pagina, CARATER, tempo=2500)
        _, campo_autor = _encontrar(pagina, AUTORIZADOR, tempo=2500)
        _, campo_proc = _encontrar(pagina, PROCEDIMENTO, tempo=2500)
        carater = obter_carater(campo_carater.inner_text(timeout=3000))
        autorizador = obter_autorizador(campo_autor.inner_text(timeout=3000))
        procedimento = obter_procedimento(campo_proc.inner_text(timeout=3000))
    except Exception:
        return ResultadoHospital('CAMPOS_FICHA_NAO_CONFIRMADOS', 'Seletores de caráter, autorizador ou procedimento mudaram.')
    if not carater or not autorizador or not procedimento:
        return ResultadoHospital('CAMPOS_FICHA_INCOMPLETOS', 'Os três dados não puderam ser extraídos com segurança.')
    esperado = digitos(procedimento_hospital)
    if esperado and (len(esperado) != 10 or esperado != procedimento):
        return ResultadoHospital('PROCEDIMENTO_DIVERGENTE',
                                'Código solicitado na ficha difere do informado pelo hospital; exige revisão.',
                                carater, autorizador, procedimento)
    return ResultadoHospital('FICHA_CONFERIDA', 'AIH exata localizada; procedimento compatível com o hospital.',
                            carater, autorizador, procedimento)


def consultar_solicitacao_hospitalar(pagina, cns: str, aih: str, procedimento: str = '') -> ResultadoHospital:
    pesquisar_por_cns(pagina, cns)
    selecionar_linha_aih(pagina, aih)
    return obter_detalhes(pagina, aih, procedimento)
