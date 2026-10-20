"""Gera metadados PyInstaller no runner Windows, sem dados de produção.

Uso: python scripts/preparar_compilacao.py
"""
from pathlib import Path
from datetime import datetime, timezone
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from app_info import APP_VERSION


def montar_metadados() -> tuple[Path, Path]:
    partes = [int(v) for v in APP_VERSION.split('.')]
    if len(partes) != 3:
        raise ValueError('Versão deve seguir MAJOR.MINOR.PATCH')
    versao = tuple(partes + [0])
    data = datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M UTC')
    versao_src = ROOT / 'src' / 'build_info.py'
    versao_src.write_text('BUILD_DATE_UTC = ' + repr(data) + '\n', encoding='utf-8')
    manifest = ROOT / 'versao_windows.txt'
    manifest.write_text(f'''# Gerado automaticamente, sem dados sensíveis.
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers={versao!r}, prodvers={versao!r},
    mask=0x3f, flags=0x0, OS=0x40004, fileType=0x1, subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo([
      StringTable('040904B0', [
        StringStruct('CompanyName', 'Aplicativo de apoio - utilizacao depende de autorizacao da TI'),
        StringStruct('FileDescription', 'RPA SISREG - apoio a conferencia de internacoes'),
        StringStruct('FileVersion', '{APP_VERSION}'),
        StringStruct('ProductName', 'RPA SISREG'),
        StringStruct('ProductVersion', '{APP_VERSION}'),
        StringStruct('LegalCopyright', 'Copyright (c) 2026 Bruno Vinicius e coautoras. MIT para codigo; sem atesto fiscal.')
      ])
    ]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
''', encoding='utf-8')
    return versao_src, manifest


if __name__ == '__main__':
    for arquivo in montar_metadados():
        print(f'Metadados preparados: {arquivo.name}')
