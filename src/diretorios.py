"""Pastas institucionais do RPA: ficam ao lado do executável, não no diretório dos pacientes."""
from __future__ import annotations
import sys
from pathlib import Path


def diretorio_aplicacao() -> Path:
    """Fora do onefile temporário (_MEIPASS); no desenvolvimento usa raiz do projeto."""
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


def pastas_de_saida(base: Path | None = None) -> tuple[Path, Path]:
    """Cria Análises e Logs. Falha explicitamente em mídia somente leitura."""
    raiz = Path(base) if base is not None else diretorio_aplicacao()
    analises, logs = raiz / 'Análises', raiz / 'Logs'
    for pasta in (analises, logs):
        pasta.mkdir(parents=True, exist_ok=True)
        if not pasta.is_dir():
            raise OSError('Pasta de resultados indisponível.')
    return analises, logs
