"""Janela de intervenção com botão real, em interface sintética e sem dados de pacientes."""
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
try:
    import tkinter as tk
except ImportError:
    tk=None
from sisreg_login import Aplicativo

class TesteAvisoReal(unittest.TestCase):
    def test_botao_modal_permite_confirmar_sem_fechar_navegador(self):
        if tk is None:self.skipTest('Tk indisponível')
        try: root=tk.Tk()
        except tk.TclError:self.skipTest('Sem ambiente gráfico')
        self.addCleanup(root.destroy)
        root.withdraw()
        app=Aplicativo(root)
        app._exibir_verificacao('hospital')
        root.update_idletasks()
        self.assertTrue(app.janela_verificacao.winfo_exists())
        self.assertIn('Verificar sessão e retomar',app.btn_modal_confirmar.cget('text'))
        self.assertTrue(app.aguardar_humano.confirmacao.is_set() is False)
        app._confirmar_verificacao()
        self.assertTrue(app.aguardar_humano.confirmacao.is_set())
        # O próprio teste jamais pede login ou abre o navegador.
        app._ocultar_verificacao()
        self.assertFalse(app.intervencao_pendente)

if __name__=='__main__':unittest.main()
