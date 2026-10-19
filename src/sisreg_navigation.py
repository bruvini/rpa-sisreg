"""Ações mínimas e assistidas no SISREG III; nenhuma coleta de resultados clínicos."""
from __future__ import annotations
from urllib.parse import urlparse

URL_HOST = 'sisregiii.saude.gov.br'
# XPaths disponibilizados pela operadora (19/10/2026), NÃO homologados.
PACIENTE_MENU = '/html/body/div/div/div[3]/ul/li[1]/a'
PACIENTE_AMB = '/html/body/div/div/div[3]/ul/li[1]/ul/li[1]'
PACIENTE_BUSCA = '/html/body/div[2]/form/center[1]/table/tbody/tr[2]/td[2]/input'
PACIENTE_PESQUISAR = '/html/body/div[2]/form/center[2]/input[1]'
SOLIC_MENU = '/html/body/div/div/div[3]/ul/li[4]/a'
SOLIC_OPCAO = '/html/body/div/div/div[3]/ul/li[4]/ul/li[1]'
SOLIC_BUSCA = '/html/body/center/div[2]/form/center/table/tbody/tr[3]/td[2]/input'
SOLIC_PESQUISAR = '/html/body/center/div[2]/form/center/table/tbody/tr[18]/td/input[1]'


class NavegacaoInesperada(Exception):
    pass


def origem_autorizada(pagina) -> None:
    u = urlparse(pagina.url)
    if u.scheme != 'https' or u.hostname != URL_HOST or u.port not in (None, 443):
        raise NavegacaoInesperada('Página fora do endereço oficial do SISREG. Pesquisa interrompida.')


def _visivel(pagina, xpath: str):
    loc = pagina.locator('xpath=' + xpath)
    loc.wait_for(state='visible', timeout=14000)
    return loc


def navegar_menu(pagina, menu: str, opcao: str) -> None:
    origem_autorizada(pagina)
    _visivel(pagina, menu).hover(timeout=10000)
    _visivel(pagina, opcao).click(timeout=10000, no_wait_after=True)
    origem_autorizada(pagina)


def _pesquisa(pagina, campo: str, botao: str, identificador: str) -> None:
    origem_autorizada(pagina)
    caixa = _visivel(pagina, campo)
    tipo = (caixa.get_attribute('type') or 'text').lower()
    if tipo not in ('text', 'search'):
        raise NavegacaoInesperada('Campo de pesquisa inesperado; não foi preenchido.')
    acao = _visivel(pagina, botao)
    tipo_acao = (acao.get_attribute('type') or 'submit').lower()
    if tipo_acao not in ('submit', 'button', 'image'):
        raise NavegacaoInesperada('Botão de pesquisa inesperado; nenhuma pesquisa enviada.')
    origem_autorizada(pagina)
    caixa.fill(identificador, timeout=10000)
    origem_autorizada(pagina)
    acao.click(timeout=10000, no_wait_after=True)


def consultar_cadastro(pagina, identificador: str) -> None:
    # Busca por CPF ou CNS previamente validado na aplicação.
    navegar_menu(pagina, PACIENTE_MENU, PACIENTE_AMB)
    _pesquisa(pagina, PACIENTE_BUSCA, PACIENTE_PESQUISAR, identificador)
    # Não usa o suposto XPath de CNS/nome: ele aponta ao mesmo botão da busca.
    # A confirmação de identidade/CNS é manual e assistida na v0.2.


def consultar_solicitacoes_amb(pagina, cns: str) -> None:
    if not (cns.isdigit() and len(cns) == 15):
        raise NavegacaoInesperada('CNS precisa ter 15 dígitos antes de pesquisar.')
    navegar_menu(pagina, SOLIC_MENU, SOLIC_OPCAO)
    _pesquisa(pagina, SOLIC_BUSCA, SOLIC_PESQUISAR, cns)
    # Não interpreta a lista de solicitações nesta versão.
