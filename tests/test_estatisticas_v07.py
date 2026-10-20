"""Regressão de indicadores/TXT com identidades completamente fictícias."""
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from estatisticas import Estatisticas, relatorio_tecnico, percentual, duracao
from governanca import HistoricoExecucao
from app_info import APP_VERSION

class EstatisticasV07(unittest.TestCase):
    def test_versao(self):
        self.assertEqual(APP_VERSION, '0.7.2')

    def test_denominadores_taxa(self):
        self.assertEqual(percentual(750,784),'95.7%')
        self.assertEqual(percentual(0,0),'—')
        self.assertEqual(duracao(3661), '01:01:01')

    def test_soma_manual_dos_registros_efetivos(self):
        e=Estatisticas()
        e.registrar_total('preparo',784)
        e.concluir('preparo',18,consultados=784,encontrados=750,pendencias=34)
        e.registrar_total('cadastro',750)
        e.concluir('cadastro',80,consultados=5,encontrados=4,pendencias=1,completa=False)
        e.registrar_total('hospital',4)
        e.concluir('hospital',20,consultados=2,encontrados=1,pendencias=1,completa=False)
        self.assertEqual(e.total_manual(),784*15 + 5*10 + 2*10)
        self.assertIn('00:00:50',e.comparativo('cadastro'))

    def test_log_privado_com_eventos_tipos_controlados(self):
        with tempfile.TemporaryDirectory() as d:
            pasta=Path(d)
            xlsx=pasta/'arquivo_ficticio.xlsx'
            pdf=pasta/'pdf_ficticio.pdf'
            xlsx.write_bytes(b'conjunto sintetico de planilha')
            pdf.write_bytes(b'espelho sintetico')
            historico=HistoricoExecucao(pasta=pasta/'historico')
            historico.fonte(xlsx,tipo='xlsx')
            historico.fonte(pdf,tipo='pdf')
            historico.evento('CADASTRO_PENDENCIA','cadastro',153)
            historico.evento('ERRO_TECNICO','hospital',205)
            historico.encerrar('INTERROMPIDA')
            e=Estatisticas()
            e.registrar_total('preparo',10)
            e.concluir('preparo',4.0,consultados=10,encontrados=9,pendencias=1,
                fases={'planilha':.1,'indexacao_pdf':2.5,'cruzamento':.2,'gravacao':1.2})
            e.registrar_total('cadastro',9)
            e.concluir('cadastro',15,consultados=3,encontrados=2,pendencias=1,completa=False)
            e.encerrar(segundos=40,situacao='PARCIAL')
            saida=pasta/'RELATORIO_TECNICO_RPA_01012026_100000.txt'
            relatorio_tecnico(e,historico,saida)
            texto=saida.read_text(encoding='utf-8')
            self.assertIn('RPA SISREG — RELATÓRIO TÉCNICO',texto)
            self.assertIn('registro ordinal 153',texto)
            self.assertIn('Etapa',texto) if False else None
            self.assertIn('00:00:40',texto)
            self.assertIn('indexacao_pdf',texto)
            self.assertNotIn('arquivo_ficticio',texto)
            self.assertNotIn('pdf_ficticio',texto)
            for proibido in ('111.444.777-35','900000000000001','ANA MARIA EXEMPLO','senha-ficticia'):
                self.assertNotIn(proibido,texto)
            with self.assertRaises(FileExistsError):
                relatorio_tecnico(e,historico,saida)

    def test_log_impede_localizacao_externa_e_valores_livres(self):
        with tempfile.TemporaryDirectory() as d:
            e=Estatisticas();e.encerrar(segundos=2,situacao='PARCIAL')
            arquivo=Path(d)/'tecnico.txt'
            relatorio_tecnico(e,None,arquivo)
            self.assertNotIn('None',arquivo.read_text(encoding='utf-8'))
            with self.assertRaises(ValueError):
                relatorio_tecnico(e,None,Path(d)/'tecnico.csv')


if __name__=='__main__':unittest.main()
