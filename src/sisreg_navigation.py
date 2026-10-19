"""SISREG: navegação de leitura, assistida, com falha fechada e pesquisa em lote.

Os seletores são hipóteses a homologar na sessão institucional. Não altera
solicitações nem interpreta ausência de resposta como ausência de cadastro.
"""
from __future__ import annotations
import re
import time
from urllib.parse import urlparse
from aih_extract import digitos, normalizar_nome, cns_formato

URL_HOST='sisregiii.saude.gov.br'
PACIENTE_MENU='/html/body/div/div/div[3]/ul/li[1]/a'
PACIENTE_AMB='/html/body/div/div/div[3]/ul/li[1]/ul/li[1]'
PACIENTE_BUSCA='/html/body/div[2]/form/center[1]/table/tbody/tr[2]/td[2]/input'
PACIENTE_PESQUISAR='/html/body/div[2]/form/center[2]/input[1]'
SOLIC_MENU='/html/body/div/div/div[3]/ul/li[4]/a'
SOLIC_OPCAO='/html/body/div/div/div[3]/ul/li[4]/ul/li[1]'
SOLIC_BUSCA='/html/body/center/div[2]/form/center/table/tbody/tr[3]/td[2]/input'
SOLIC_PESQUISAR='/html/body/center/div[2]/form/center/table/tbody/tr[18]/td/input[1]'
BTN_CADASTRO='input[name="btn_pesquisar"][onclick*="pesquisarPaciente"]'

class NavegacaoInesperada(Exception):
    pass

def origem_autorizada(pagina):
    u=urlparse(pagina.url)
    if u.scheme!='https' or u.hostname!=URL_HOST or u.port not in (None,443):
        raise NavegacaoInesperada('Página fora do SISREG oficial, pesquisa interrompida.')


def _encontrar(pagina, seletores, tempo=9000):
    """Encontra seletor visível no quadro atual ou iframe oficial, sem adivinhar valores."""
    if isinstance(seletores,str): seletores=[seletores]
    fim=time.monotonic()+tempo/1000
    while time.monotonic()<fim:
        frames=list(getattr(pagina,'frames',[pagina]))
        for frame in frames:
            if frame is not pagina:
                u=getattr(frame,'url','')
                if u and u!='about:blank':
                    try: origem_autorizada(frame)
                    except NavegacaoInesperada: continue
            for seletor in seletores:
                try:
                    loc=frame.locator(seletor)
                    if loc.count()==1 and loc.is_visible():
                        return frame,loc
                except Exception:
                    continue
        time.sleep(0.2)
    raise NavegacaoInesperada('Campo ou botão não foi encontrado na tela esperada. '
                              'A navegação está suspensa para revisão dos seletores.')


def _menu(pagina, xpath_menu, xpath_opcao, texto_opcao=''):
    origem_autorizada(pagina)
    _, menu=_encontrar(pagina,['xpath='+xpath_menu],tempo=10000)
    menu.hover(timeout=6000)
    frame,alvo=_encontrar(pagina,['xpath='+xpath_opcao],tempo=5000)
    # O XPath informado aponta para <li>, enquanto a navegação pode estar no <a> filho.
    try:
        ancoras=alvo.locator('a')
        if ancoras.count()==1 and ancoras.is_visible(): alvo=ancoras
    except Exception: pass
    origem_autorizada(pagina)
    alvo.click(timeout=10000, no_wait_after=True)


def abrir_busca_cadastro(pagina):
    """Abre Solicitar > Ambulatorial apenas quando a busca não está visível."""
    origem_autorizada(pagina)
    try:
        return _encontrar(pagina,['xpath='+PACIENTE_BUSCA],tempo=1000)[0]
    except NavegacaoInesperada:
        pass
    _menu(pagina,PACIENTE_MENU,PACIENTE_AMB)
    return _encontrar(pagina,['xpath='+PACIENTE_BUSCA],tempo=18000)[0]


def _buscar_cadastro_no_form(pagina, cpf):
    origem_autorizada(pagina)
    _,campo=_encontrar(pagina,['xpath='+PACIENTE_BUSCA],tempo=16000)
    if (campo.get_attribute('type') or 'text').lower() not in ('text','search'):
        raise NavegacaoInesperada('Campo de CPF não corresponde ao esperado.')
    # Usar nome+onclick como fornecido; XPath absoluto só como alternativa.
    frame,botao=_encontrar(pagina,[BTN_CADASTRO,'xpath='+PACIENTE_PESQUISAR],tempo=8000)
    if (botao.get_attribute('type') or '').lower() not in ('button','submit'):
        raise NavegacaoInesperada('Controle Pesquisar não é botão.')
    origem_autorizada(pagina)
    campo.fill(cpf,timeout=7000)
    origem_autorizada(pagina)
    botao.click(timeout=12000, no_wait_after=True)
    return frame


def consultar_cadastro(pagina, cpf):
    if len(digitos(cpf))!=11:
        raise NavegacaoInesperada('CPF inválido para busca.')
    abrir_busca_cadastro(pagina)
    return _buscar_cadastro_no_form(pagina,digitos(cpf))


def autenticao_ativa(pagina, timeout=12000):
    """Confirma que a interface de menu pós-login está visível (não prova permissões)."""
    try:
        origem_autorizada(pagina)
        _encontrar(pagina,['xpath='+PACIENTE_MENU],tempo=timeout)
        return True
    except NavegacaoInesperada:
        return False


def avaliar_resultado_cadastro(texto, nome_esperado, cpf_esperado):
    """Extrai apenas um CNS único associado a nome explícito, com confiança conservadora.

    Não infere CNS de números soltos em HTML, cabeçalhos, operadores, nem de
    etiquetas sem resultado de paciente. Se a tela for desconhecida, revisão.
    """
    nome=normalizar_nome(nome_esperado)
    t=texto or ''
    # Somente nome explícito do cadastro na mesma linha de sua etiqueta.
    nomes=re.findall(r'(?im)^\s*(?:nome(?:\s+(?:do|da)\s+paciente)?|paciente)\s*:\s*([^\n\r]+)',t)
    nomes=[normalizar_nome(n) for n in nomes]
    if not nomes or any(n!=nome for n in nomes):
        return None, 'NOME_NAO_CONFIRMADO_RESULTADO'
    cpfs={digitos(v) for v in re.findall(r'(?im)\bCPF\s*:\s*([0-9.\-]{11,15})',t)}
    if cpfs and cpfs!={digitos(cpf_esperado)}:
        return None, 'CPF_DIVERGENTE_CADASTRO'
    cns_achados={digitos(v) for v in re.findall(
        r'(?im)(?:^|\s)(?:CNS|CART[AÃ]O\s+NACIONAL\s+DE\s+SA[UÚ]DE)\s*:\s*([0-9 .\-]{15,19})',t)}
    cns_achados={n for n in cns_achados if cns_formato(n)}
    if len(cns_achados)!=1:
        return None, 'CNS_NAO_UNICO_OU_NAO_IDENTIFICADO'
    return next(iter(cns_achados)), 'CNS_CONFIRMADO_TELA'


def ler_resultado_cadastro(pagina, nome_esperado, cpf_esperado, espera=10000):
    """Inspeciona texto visível após a busca (nunca marca cadastro como inexistente)."""
    # O SISREG exibe o CNS como TD > FONT > B, sem necessariamente ter
    # "CNS:" como texto ou manter o CPF no formulário após pesquisar.
    numero, motivo = ler_cns_negrito_pagina(
        pagina, nome_esperado, cpf_esperado, espera=min(4500,espera),
        consulta_efetuada=True)
    if numero:
        return numero, motivo
    fim=time.monotonic()+max(1200,espera-4500)/1000
    ultimo=motivo or 'RESULTADO_NAO_COMPROVADO'
    while time.monotonic()<fim:
        for frame in getattr(pagina,'frames',[pagina]):
            try:
                if getattr(frame,'url','') not in ('','about:blank'):
                    origem_autorizada(frame)
                texto=frame.locator('body').inner_text(timeout=1800)
                # Campos de resultado podem aparecer em <input readonly>; innerText
                # sozinho não os enxerga. Leitura SOMENTE de etiquetas identificáveis.
                try:
                    adicionais=frame.evaluate(r"""() => {
                      const nomes = /^(?:nome(?:\s+(?:do|da)\s+paciente)?|paciente)$/i;
                      const docs = /^(?:cns|cpf|cart[aã]o\s+nacional\s+de\s+sa[uú]de)$/i;
                      const resultado = [];
                      for (const el of document.querySelectorAll('input,textarea')) {
                        if (el.type === 'hidden' || !el.value || !el.getClientRects().length) continue;
                        const row = el.closest('tr');
                        const rotulos = [el.getAttribute('aria-label'), el.getAttribute('name'),
                          el.getAttribute('id'), el.previousElementSibling?.textContent,
                          el.parentElement?.previousElementSibling?.textContent,
                          row?.querySelector('td')?.textContent].filter(Boolean)
                          .map(x => x.trim().replace(/[:\s]+$/, ''));
                        for (const nome of rotulos) {
                          if (nomes.test(nome) || docs.test(nome)) {
                            resultado.push(nome + ': ' + el.value.trim()); break;
                          }
                        }
                      }
                      return resultado.join('\n');
                    }""")
                    if adicionais: texto += '\n'+adicionais
                except Exception:
                    pass
                cns,porque=avaliar_resultado_cadastro(texto,nome_esperado,cpf_esperado)
                if cns:
                    return cns,porque
                ultimo=porque
                if porque=='CPF_DIVERGENTE_CADASTRO': return None,porque
            except Exception:
                continue
        time.sleep(0.35)
    # Compatibilidade com o HTML real: CNS em TD colspan=2 > FONT size=3 > B.
    numero, motivo = ler_cns_negrito_pagina(pagina, nome_esperado, cpf_esperado, espera=1800, consulta_efetuada=True)
    if numero:
        return numero, motivo
    return None, ultimo if ultimo != 'RESULTADO_NAO_COMPROVADO' else motivo


def consultar_solicitacoes_amb(pagina,cns):
    if not cns_formato(cns):
        raise NavegacaoInesperada('CNS incompleto; não foi possível pesquisar solicitações.')
    _menu(pagina,SOLIC_MENU,SOLIC_OPCAO)
    _,caixa=_encontrar(pagina,['xpath='+SOLIC_BUSCA],tempo=18000)
    _,botao=_encontrar(pagina,['xpath='+SOLIC_PESQUISAR],tempo=9000)
    if (caixa.get_attribute('type') or 'text').lower() not in ('text','search'):
        raise NavegacaoInesperada('Campo de CNS inesperado.')
    if (botao.get_attribute('type') or '').lower() not in ('submit','button'):
        raise NavegacaoInesperada('Botão de solicitações inesperado.')
    origem_autorizada(pagina)
    caixa.fill(cns,timeout=7000)
    botao.click(timeout=10000,no_wait_after=True)


def avaliar_cadastro_com_cns_em_negrito(texto_visivel, numeros_destacados, nome_esperado,
                                          cpf_esperado, cpf_consultado, consulta_efetuada=False):
    """Validação adicional para o TD <font size=3><b>CNS</b> do SISREG.

    Exige CPF ainda preenchido na pesquisa, nome completo visível na página e
    somente um CNS na região de resultado. Números soltos nunca são usados.
    """
    cpf = digitos(cpf_esperado)
    pesquisado = digitos(cpf_consultado)
    if not cpf or (pesquisado and cpf != pesquisado):
        return None, 'CPF_PESQUISADO_NAO_CONFIRMADO'
    if not pesquisado and not consulta_efetuada:
        return None, 'CPF_PESQUISADO_NAO_CONFIRMADO'
    nome = normalizar_nome(nome_esperado)
    texto = normalizar_nome(texto_visivel)
    if not nome or not re.search(r'(?<!\w)' + re.escape(nome) + r'(?!\w)', texto):
        return None, 'NOME_NAO_CONFIRMADO_RESULTADO'
    # Se existir CPF explicitamente apresentado no resultado, não aceitar
    # documento de outro paciente nem vários CPFs distintos.
    vistos = {digitos(x) for x in re.findall(
        r'(?im)\bCPF\s*[:：]\s*([0-9.\- ]{11,18})', texto_visivel or '')}
    vistos.discard('')
    if vistos and vistos != {cpf}:
        return None, 'CPF_DIVERGENTE_CADASTRO'
    # Um nome de paciente diferente em campo explicitamente rotulado é conflito.
    nomes_rotulados = [normalizar_nome(x) for x in re.findall(
        r'(?im)^\s*(?:nome(?:\s+(?:do|da)\s+paciente)?|paciente)\s*:\s*([^\r\n]+)',
        texto_visivel or '')]
    if nomes_rotulados and any(n != nome for n in nomes_rotulados):
        return None, 'NOME_DIVERGENTE_RESULTADO'
    ns = {digitos(x) for x in numeros_destacados if cns_formato(digitos(x))}
    if len(ns) != 1:
        return None, 'CNS_DESTACADO_AMBIGUO_OU_AUSENTE'
    # A busca foi efetuada para o CPF validado e o resultado contém o nome
    # completo esperado e um único CNS destacado. Na ausência do CPF textual,
    # usar procedência da consulta, mas registrar uma justificativa distinta.
    motivo = ('CNS_CONFIRMADO_TD_NEGRITO' if pesquisado or vistos
              else 'CNS_CONFIRMADO_NOME_E_PESQUISA_CPF')
    return next(iter(ns)), motivo


def ler_cns_negrito_pagina(pagina, nome_esperado, cpf_esperado, espera=3200, consulta_efetuada=True):
    """Examina apenas TDs destacadas e o CPF da busca, sem salvar HTML localmente."""
    fim = time.monotonic() + espera / 1000
    ultima = 'CNS_NAO_IDENTIFICADO_DOM'
    while time.monotonic() < fim:
        for frame in getattr(pagina, 'frames', [pagina]):
            try:
                if getattr(frame, 'url', '') not in ('', 'about:blank'):
                    origem_autorizada(frame)
                instantaneo = frame.evaluate(r"""() => {
                  // Valores em INPUT não constam em innerText, mesmo quando a
                  // tela apresenta o nome somente em campo readonly.
                  const campos = [...document.querySelectorAll('input,textarea')]
                    .filter(e => e.getClientRects().length && e.value && e.type !== 'password' && e.type !== 'hidden')
                    .map(e => {
                      const rotulo = ((e.getAttribute('aria-label') || '') + ' ' +
                        (e.getAttribute('name') || '') + ' ' + (e.id || '')).toLowerCase();
                      if (/nome|paciente/.test(rotulo)) return 'Nome: ' + String(e.value).trim();
                      if (/cpf/.test(rotulo)) return 'CPF: ' + String(e.value).trim();
                      return '';
                    }).filter(Boolean);
                  const doc = document.querySelector('input[name="cpf"],input[id="cpf"],input[name="nu_cpf"]');
                  return {
                    texto: (document.body?.innerText || '') + '\n' + campos.join('\n'),
                    numeros: [...document.querySelectorAll('td[colspan="2"] font[size="3"] b')]
                      .filter(e => !!e.getClientRects().length)
                      .map(e => (e.textContent || '').trim()),
                    cpfPesquisa: (doc && doc.getClientRects().length) ? (doc.value || '') : ''
                  };
                }""")
                # O formulário pode não usar name/id cpf: então conferir que a caixa
                # que já foi usada na busca mantém exatamente o CPF pesquisado.
                cpf_pesquisa = instantaneo.get('cpfPesquisa', '')
                if not cpf_pesquisa:
                    try:
                        campo = frame.locator('xpath=' + PACIENTE_BUSCA)
                        if campo.count() == 1 and campo.is_visible():
                            cpf_pesquisa = campo.input_value(timeout=2000)
                    except Exception:
                        pass
                numero, motivo = avaliar_cadastro_com_cns_em_negrito(
                    instantaneo.get('texto',''), instantaneo.get('numeros', []),
                    nome_esperado, cpf_esperado, cpf_pesquisa, consulta_efetuada=consulta_efetuada)
                if numero:
                    return numero, motivo
                ultima = motivo
            except Exception:
                continue
        time.sleep(.3)
    return None, ultima
