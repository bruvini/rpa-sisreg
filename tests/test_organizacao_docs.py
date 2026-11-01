"""Valida links locais após mover documentos, sem compilar executável localmente."""
from pathlib import Path
import re
import unittest
from urllib.parse import unquote

ROOT=Path(__file__).resolve().parents[1]


class TesteDocumentacao(unittest.TestCase):
    def test_links_relativos_da_documentacao_apontam_para_arquivos_existentes(self):
        arquivos=[ROOT/'README.md',ROOT/'SECURITY.md',ROOT/'CHANGELOG.md',*(ROOT/'docs').rglob('*.md')]
        for arquivo in arquivos:
            for destino in re.findall(r'\]\(([^)]+)\)',arquivo.read_text(encoding='utf-8')):
                if destino.startswith(('https:','http:','mailto:','#')):continue
                caminho=unquote(destino.split('#')[0])
                with self.subTest(documento=str(arquivo.relative_to(ROOT)),link=caminho):
                    self.assertTrue((arquivo.parent/caminho).exists())

    def test_historicos_ficam_em_docs_e_compilador_em_scripts(self):
        self.assertTrue((ROOT/'scripts'/'compilar_windows.ps1').is_file())
        for padrao in ('GUIA*.md','RELATORIO*.md','CHANGELOG_v*.md','SHA256*'):
            self.assertFalse(list(ROOT.glob(padrao)))
        self.assertTrue((ROOT/'requirements-build.txt').is_file())
        self.assertTrue((ROOT/'.github/workflows/compilar-windows.yml').is_file())
