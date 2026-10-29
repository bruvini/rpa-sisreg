"""Resiliencia de log e fechamento sem depender de interface grafica."""
import sys
import threading
import unittest
from pathlib import Path
from unittest.mock import Mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from estatisticas import Estatisticas
from sisreg_login import Aplicativo

class TestesResiliencia(unittest.TestCase):
    def test_pagina_resultados_e_evento_valido(self):
        e=Estatisticas()
        e.diagnosticar('PAGINA_RESULTADOS','OK',ordinal=3,segundos=0)
        self.assertEqual(e.diagnosticos[-1]['acao'],'PAGINA_RESULTADOS')

    def test_fechar_confirmado_nao_gera_relatorio(self):
        app=Aplicativo.__new__(Aplicativo)
        app.parar=threading.Event()
        app.pausa=threading.Event()
        app.aguardar_humano=Mock()
        app.navegacao_falhou=False
        app.processando=True
        app.historico=Mock(termino=None)
        app.root=Mock()
        app._fechar_aplicacao=Mock(side_effect=AssertionError('nunca executar'))
        app._encerrar_confirmado_sem_relatorio()
        app.root.destroy.assert_called_once()
        app._fechar_aplicacao.assert_not_called()
        app.historico.encerrar.assert_called_once_with('INTERROMPIDA')
        self.assertTrue(app.parar.is_set())

if __name__=='__main__':unittest.main()
