"""Identificação única da aplicação e data de compilação, quando disponível."""
APP_VERSION = '0.7.7'
APP_NAME = 'RPA SISREG'
try:
    from build_info import BUILD_DATE_UTC
except ImportError:
    BUILD_DATE_UTC = None


def rotulo_versao() -> str:
    return f'Versão {APP_VERSION}' + (f' · compilação {BUILD_DATE_UTC}' if BUILD_DATE_UTC else ' · versão de desenvolvimento')
