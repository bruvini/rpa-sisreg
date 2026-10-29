"""Estado conservador da sessão SISREG: CAPTCHA exige intervenção humana.

Este módulo apenas reconhece sinais visuais da proteção e gerencia a pausa.
Não resolve desafios, não reutiliza credenciais e não faz sondagens enquanto
aguarda a operadora.
"""
from __future__ import annotations
import re
from threading import Event

SINAIS_VERIFICACAO = re.compile(
    r'\b(?:re[\s-]?captcha|captcha|teste\s+automatizado\s+para\s+' 
    r'diferencia[cç][aã]o|quantidade\s+de\s+requisi[cç][oõ]es|' 
    r'computadores\s+e\s+humanos)\b', re.IGNORECASE)


SINAIS_ERRO_SERVIDOR = re.compile(
    r'(?:upstream connect error|disconnect/reset before headers|connection termination|'
    r'503 service unavailable|502 bad gateway)', re.IGNORECASE)


def texto_erro_servidor(texto: str) -> bool:
    return bool(SINAIS_ERRO_SERVIDOR.search(texto or ''))


def servidor_indisponivel(contexto) -> bool:
    for pagina in getattr(contexto, 'pages', []):
        try:
            if pagina.is_closed() or not pagina.url.lower().startswith('https://sisregiii.saude.gov.br/'):
                continue
            if texto_erro_servidor(pagina.locator('body').inner_text(timeout=1200)):
                return True
        except Exception:
            continue
    return False


def texto_exige_verificacao(texto: str) -> bool:
    """Somente inspeciona, em memória, texto já visível na tela institucional."""
    return bool(SINAIS_VERIFICACAO.search(texto or ''))


def desafio_visivel(contexto) -> bool:
    """Não guarda ou registra HTML, texto de pacientes, cookies ou credenciais."""
    for pagina in getattr(contexto, 'pages', []):
        try:
            if pagina.is_closed():
                continue
            if not pagina.url.lower().startswith('https://sisregiii.saude.gov.br/'):
                continue
            texto = pagina.locator('body').inner_text(timeout=1200)
            if texto_exige_verificacao(texto):
                return True
        except Exception:
            continue
    return False


class AguardarHumano:
    """Um sinal de confirmação, sem temporizador de encerramento da janela."""

    def __init__(self):
        self.confirmacao = Event()

    def confirmar(self) -> None:
        self.confirmacao.set()

    def esperar(self, parar: Event, reiniciar: Event | None = None) -> bool:
        """Retorna False se interrupção; nunca verifica CAPTCHA automaticamente."""
        while not parar.is_set():
            if reiniciar is not None and reiniciar.is_set():
                return False
            if self.confirmacao.wait(timeout=0.25):
                self.confirmacao.clear()
                return True
        return False
