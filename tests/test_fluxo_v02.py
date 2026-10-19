import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from aih_extract import extrair_texto_paginas, normalizar_aih, escolher_espelho, cpf_valido, normalizar_nome, ler_espelhos_pdf
from planilha import SessaoPlanilha
from sisreg_navigation import consultar_cadastro, consultar_solicitacoes_amb, NavegacaoInesperada


class TesteEspelho(unittest.TestCase):
    def test_aih_com_e_sem_hifen(self):
        self.assertEqual(normalizar_aih('422650033029-4'), '4226500330294')
        self.assertEqual(normalizar_aih('4226500330294'), '4226500330294')

    def test_a_aih_malformada_nao_e_comparada(self):
        self.assertEqual(normalizar_aih('422650033029'), '')

    def test_pesquisa_textual_de_espelho(self):
        texto = ('SIHD2 Num AIH: 422650033029-4 Situação: OK\n'
                 'Paciente: DERVANIA DOROTI DRASE DA SILVA    Doc: 123456\n'
                 'CNS/CPF: 58260072904   Procedimento principal: 0408050063\n')
        index = extrair_texto_paginas([texto])
        self.assertEqual(len(index['4226500330294']), 1)
        reg, status = escolher_espelho(index['4226500330294'], 'DERVANIA DOROTI DRASE DA SILVA')
        self.assertEqual(status, 'DOCUMENTO_VALIDADO_POR_AIH_E_NOME')
        self.assertEqual(reg.cpf, '58260072904')
        self.assertEqual(reg.cns, '')

    def test_multiplas_aih_na_mesma_pagina(self):
        texto = ('Num AIH: 422650033029-4\nPaciente: DERVANIA DOROTI DRASE DA SILVA\nCNS/CPF: 58260072904\n'
                 'Num AIH: 422650033029-5\nPaciente: OUTRA PESSOA\nCNS/CPF: 11144477735\n')
        ix = extrair_texto_paginas([texto])
        self.assertEqual(set(ix), {'4226500330294', '4226500330295'})
        self.assertEqual(ix['4226500330295'][0].cpf, '11144477735')

    def test_pdf_textual_em_arquivo(self):
        from reportlab.pdfgen import canvas
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'espelho_ficticio.pdf'
            c = canvas.Canvas(str(p))
            c.drawString(40, 730, 'SIHD2 - ESPELHO DE AIH')
            c.drawString(40, 712, 'Num AIH: 422650033029-4  Situacao: OK')
            c.drawString(40, 693, 'Paciente: ANA MARIA   Doc: 00000')
            c.drawString(40, 675, 'CNS/CPF: 11144477735')
            c.save()
            dados, avisos = ler_espelhos_pdf(p)
            self.assertEqual(avisos, [])
            self.assertEqual(dados['4226500330294'][0].cpf, '11144477735')

    def test_cns_nao_e_cpf(self):
        ix = extrair_texto_paginas(['Num AIH: 422650033029-4\nPaciente: ANA MARIA\nCNS/CPF: 123456789012345'])
        self.assertEqual(ix['4226500330294'][0].cpf, '')
        self.assertEqual(ix['4226500330294'][0].cns, '123456789012345')

    def test_nome_divergente(self):
        ix = extrair_texto_paginas(['Num AIH: 422650033029-4\nPaciente: ANA MARIA\nCNS/CPF: 11144477735'])
        e, status = escolher_espelho(ix['4226500330294'], 'JOANA MARIA')
        self.assertIsNone(e)
        self.assertEqual(status, 'NOME_DIVERGENTE_ESPELHO')

    def test_pdf_duplicado_conflitante(self):
        ix = extrair_texto_paginas(['Num AIH: 422650033029-4\nPaciente: ANA MARIA\nCNS/CPF: 11144477735',
             'Num AIH: 422650033029-4\nPaciente: OUTRA PESSOA\nCNS/CPF: 58260072904'])
        e, status = escolher_espelho(ix['4226500330294'], 'ANA MARIA')
        self.assertIsNone(e)
        self.assertEqual(status, 'ESPELHOS_CONFLITANTES')

    def test_cpf_checksum(self):
        self.assertTrue(cpf_valido('58260072904'))
        self.assertFalse(cpf_valido('11111111111'))
        self.assertFalse(cpf_valido('58260072905'))


class TestePlanilha(unittest.TestCase):
    def setUp(self):
        import shutil
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.arq = Path(self.tmp.name)/'hospital_sintetico.xlsx'
        origem = Path(__file__).resolve().parent / 'fixtures' / 'hospital_sintetico.xlsx'
        shutil.copyfile(origem, self.arq)

    def test_prepara_e_exporta_copia_sem_sobrescrever(self):
        s = SessaoPlanilha()
        self.assertEqual(s.carregar(self.arq), 1)
        from aih_extract import extrair_texto_paginas
        ix=extrair_texto_paginas(['Num AIH: 422650033029-4\nPaciente: ANA MARIA\nCNS/CPF: 11144477735'])
        fake_pdf=Path(self.tmp.name)/'simulado.pdf'
        fake_pdf.write_text('conteudo ficticio')
        s.complementar_pdf(ix, fake_pdf)
        self.assertEqual(s.registros[0].cpf, '11144477735')
        with self.assertRaises(ValueError):
            s.confirmar_cns_manual(s.registros[0], '123456789012345', False)
        s.confirmar_cns_manual(s.registros[0], '123456789012345', True)
        saida=Path(self.tmp.name)/'saida.xlsx'
        s.salvar_copia(saida)
        # Verificação estrutural com ZIP/XML para não exigir dependências de teste.
        from zipfile import ZipFile
        from xml.etree import ElementTree as ET
        with ZipFile(saida) as z:
            todas = [z.read(nome).decode('utf-8') for nome in z.namelist()
                     if nome.startswith('xl/worksheets/sheet') and nome.endswith('.xml')]
        self.assertTrue(any('11144477735' in txt and '123456789012345' in txt
                            for txt in todas))
        self.assertTrue(any('rpaSituacao' in txt for txt in todas))
        self.assertNotEqual(self.arq.read_bytes(), saida.read_bytes())

    def test_nao_sobrescreve_original(self):
        s=SessaoPlanilha();s.carregar(self.arq)
        with self.assertRaises(ValueError):
            s.salvar_copia(self.arq)


class MockCampo:
    def __init__(self, tipo='text'):
        self.tipo=tipo;self.acao=[]
    def wait_for(self, **kwargs): self.acao.append('aguardou')
    def get_attribute(self, chave): return self.tipo
    def hover(self, **kwargs): self.acao.append('hover')
    def click(self, **kwargs): self.acao.append('clicou')
    def fill(self, v, **kwargs): self.acao.append(('preencheu',v))


class MockPagina:
    url='https://sisregiii.saude.gov.br/'
    def __init__(self): self.campos={}
    def locator(self, xpath):
        if xpath not in self.campos:
            typ = 'submit' if xpath.endswith('input[1]') and ('center[2]' in xpath or 'tr[18]' in xpath) else 'text'
            self.campos[xpath] = MockCampo(typ)
        return self.campos[xpath]


class TesteNavegacao(unittest.TestCase):
    def test_cadastro_abre_busca_e_nao_extrai_cns(self):
        p=MockPagina(); consultar_cadastro(p,'11144477735')
        acao=[v for campo in p.campos.values() for v in campo.acao]
        self.assertIn(('preencheu','11144477735'),acao)
        self.assertEqual(acao.count('clicou'),2)

    def test_solicitacoes_pesquisa_por_cns(self):
        p=MockPagina(); consultar_solicitacoes_amb(p,'123456789012345')
        acao=[v for campo in p.campos.values() for v in campo.acao]
        self.assertIn(('preencheu','123456789012345'),acao)

    def test_erro_cns_curto(self):
        with self.assertRaises(NavegacaoInesperada):
            consultar_solicitacoes_amb(MockPagina(), '123')

    def test_erro_host(self):
        p=MockPagina(); p.url='https://example.org'
        with self.assertRaises(NavegacaoInesperada):
            consultar_cadastro(p, '11144477735')

if __name__=='__main__':
    unittest.main()
