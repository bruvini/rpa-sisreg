"""Somente dados inventados. NÃO adicionar prontuários nem credenciais reais."""
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
import time
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from app_info import APP_VERSION, rotulo_versao
from governanca import (HistoricoExecucao, sha256_arquivo,
                         limpeza_temporarios, nome_fonte_seguro, exportar_pendencias)
from planilha import SessaoPlanilha


class TesteHistoricoSeguro(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base=Path(self.temp.name)
        self.artefato=self.base/'producao_mes_teste.xlsx'
        self.artefato.write_bytes(b'DADOS DE TESTE SEM PACIENTES')

    def test_hash_sha256(self):
        self.assertEqual(sha256_arquivo(self.artefato),
                         hashlib.sha256(self.artefato.read_bytes()).hexdigest())

    def test_fonte_so_nome_e_hash(self):
        h=HistoricoExecucao(self.base/'logs')
        h.fonte(self.artefato)
        data=h.payload()
        self.assertEqual(data['fontes'][0]['nome'], 'producao_mes_teste.xlsx')
        self.assertNotIn(str(self.base), json.dumps(data))
        self.assertEqual(data['fontes'][0]['sha256'],sha256_arquivo(self.artefato))

    def test_snapshot_sem_segredos(self):
        h=HistoricoExecucao(self.base/'logs')
        h.atualizar(registros=3, cns_identificados=2, pendencias=1)
        h.evento('CADASTRO_PENDENCIA', 'cadastro', 2)
        h.encerrar('CONCLUIDA')
        snapshot=list((self.base/'logs').glob('execucao_*.json'))
        self.assertEqual(len(snapshot),1)
        obj=json.loads(snapshot[0].read_text('utf-8'))
        self.assertEqual(obj['versao'], APP_VERSION)
        self.assertEqual(obj['situacao'], 'CONCLUIDA')
        self.assertEqual(obj['contagens']['pendencias'], 1)
        self.assertTrue(obj['encerrado_em_utc'])
        self.assertGreaterEqual(obj['duracao_segundos'],0)

    def test_evento_rejeita_texto_livre(self):
        h=HistoricoExecucao(self.base/'logs')
        with self.assertRaises(ValueError):
            h.evento('Fulano CPF 11144477735 senha TESTE')
        with self.assertRaises(ValueError):
            h.evento('CADASTRO_OK', 'CNS 123456789012345')
        with self.assertRaises(ValueError):
            h.evento('CADASTRO_OK', 'cadastro', 'CPF 11144477735')

    def test_nao_exporta_identificadores_no_log(self):
        h=HistoricoExecucao(self.base/'logs')
        h.evento('ERRO_TECNICO','cadastro', 1)
        h.encerrar('FALHA_TECNICA')
        texto='\n'.join(f.read_text('utf-8') for f in (self.base/'logs').iterdir())
        for conteudo in ('11144477735','123456789012345','ANA TESTE','senha_exemplo','cookies'):
            self.assertNotIn(conteudo,texto)

    def test_numeros_invalidos_rejeitados(self):
        h=HistoricoExecucao(self.base/'logs')
        for dados in ({'pendencias':-1},{'senha':'segredo'},{'registros':'10'}, {'registros':True}):
            with self.assertRaises(ValueError): h.atualizar(**dados)

    def test_encerramento_idempotente(self):
        h=HistoricoExecucao(self.base/'logs')
        h.encerrar()
        anterior=h.termino
        h.encerrar('INTERROMPIDA')
        self.assertEqual(h.termino,anterior)
        self.assertEqual(h.situacao,'CONCLUIDA')

    def test_execucao_interrompida_preserva_snapshot(self):
        h=HistoricoExecucao(self.base/'logs')
        h.encerrar('INTERROMPIDA')
        conteudo=json.loads(next((self.base/'logs').glob('execucao_*.json')).read_text())
        self.assertEqual(conteudo['situacao'],'INTERROMPIDA')

    def test_nome_fonte_mascara_identificador(self):
        self.assertNotIn('11144477735',nome_fonte_seguro(Path('aih_11144477735.xlsx')))

    def test_pasta_sem_temporario_no_finally(self):
        h=HistoricoExecucao(self.base/'logs')
        h.salvar()
        self.assertFalse(list((self.base/'logs').glob('.historico_*.tmp')))


class TesteTemporarios(unittest.TestCase):
    def setUp(self):
        self.t=tempfile.TemporaryDirectory()
        self.addCleanup(self.t.cleanup)
        self.p=Path(self.t.name)

    def test_remove_apenas_temporario_antigo(self):
        import os
        tmp=self.p/'.rpa_sisreg_1234.xlsx'
        tmp.write_bytes(b'temporario_ficticio')
        velho=time.time()-49*3600
        os.utime(tmp,(velho,velho))
        entrada=self.p/'hospital.xlsx';entrada.write_bytes(b'entrada_valida')
        backup=self.p/'hospital.backup_antes_RPA.xlsx';backup.write_bytes(b'backup')
        self.assertEqual(limpeza_temporarios(self.p),1)
        self.assertFalse(tmp.exists())
        self.assertTrue(entrada.exists())
        self.assertTrue(backup.exists())

    def test_nao_remove_recente(self):
        tmp=self.p/'.rpa_sisreg_1234.xlsx'
        tmp.write_bytes(b'teste')
        self.assertEqual(limpeza_temporarios(self.p),0)
        self.assertTrue(tmp.exists())

    def test_nao_remove_nome_estranho(self):
        original=self.p/'.outra_aplicacao.xlsx'
        original.write_bytes(b'original')
        self.assertEqual(limpeza_temporarios(self.p,agora_epoch=time.time()+100*3600),0)
        self.assertTrue(original.exists())

    def test_limpeza_historico_temporario_abandonado(self):
        import os
        logs=self.p/'logs';logs.mkdir()
        old=logs/'.historico_abc.tmp';old.write_bytes(b'descartavel')
        tm=time.time()-50*3600
        os.utime(old,(tm,tm))
        HistoricoExecucao(logs)
        self.assertFalse(old.exists())


class TestePlanilhaSomenteLeitura(unittest.TestCase):
    def setUp(self):
        self.t=tempfile.TemporaryDirectory()
        self.addCleanup(self.t.cleanup)
        self.p=Path(self.t.name)
        fixture=Path(__file__).parent/'fixtures'/'hospital_sintetico.xlsx'
        self.entrada=self.p/'hospital.xlsx'
        shutil.copy2(fixture,self.entrada)

    def test_original_intacto_copia_automatica(self):
        from aih_extract import extrair_texto_paginas
        original=self.entrada.read_bytes()
        sessao=SessaoPlanilha();sessao.carregar(self.entrada)
        espelhos=extrair_texto_paginas(['Num AIH: 900000000012-3\nPaciente: ANA MARIA\nCNS/CPF: 11144477735'])
        sessao.complementar_pdf(espelhos,self.entrada)  # teste sem PDF real
        destino=sessao.preparar_copia_de_trabalho()
        sessao.salvar_na_planilha()
        self.assertEqual(self.entrada.read_bytes(),original)
        self.assertNotEqual(destino,self.entrada)
        self.assertTrue(destino.is_file())
        self.assertEqual(sessao.fonte_original,self.entrada)
        from openpyxl import load_workbook
        wb=load_workbook(destino,read_only=True)
        try:self.assertEqual(str(wb['PT6']['D2'].value),'11144477735')
        finally:wb.close()

    def test_dois_arquivos_de_trabalho_nao_sobrescrevem(self):
        arquivos=[]
        for _ in range(2):
            s=SessaoPlanilha();s.carregar(self.entrada)
            arquivos.append(s.preparar_copia_de_trabalho())
        self.assertNotEqual(*arquivos)
        self.assertTrue(all(arq.exists() for arq in arquivos))

    def test_rejeita_original_alterado_antes_da_copia(self):
        s=SessaoPlanilha();s.carregar(self.entrada)
        self.entrada.write_bytes(self.entrada.read_bytes()+b'MUDOU')
        with self.assertRaises(ValueError):s.preparar_copia_de_trabalho()

    def test_exportacao_pendencias_minima(self):
        s=SessaoPlanilha();s.carregar(self.entrada)
        destino=self.p/'pendencias.xlsx'
        n=exportar_pendencias(s,destino)
        self.assertGreater(n,0)
        import zipfile
        with zipfile.ZipFile(destino) as arquivo:
            raw=''.join(arquivo.read(n).decode('utf-8','ignore') for n in arquivo.namelist() if n.startswith('xl/'))
        self.assertNotIn('11144477735',raw)
        self.assertNotIn('123456789012345',raw)
        self.assertNotIn('ANA MARIA',raw)


class TesteVersao(unittest.TestCase):
    def test_versao_sem_inconsistencia(self):
        self.assertEqual(APP_VERSION,'0.6.2')
        self.assertIn(APP_VERSION,rotulo_versao())

    def test_modulo_builder_usa_versao_central(self):
        base=Path(__file__).resolve().parents[1]
        script=(base/'scripts'/'preparar_compilacao.py').read_text('utf-8')
        self.assertIn('from app_info import APP_VERSION',script)


if __name__=='__main__': unittest.main()

class TesteCredencialIncorretaETempo(unittest.TestCase):
    """Simula falha na tela, nunca testa uma conta real SISREG."""

    def test_login_nao_confirmado_mantem_bloqueio(self):
        from unittest.mock import patch
        from sisreg_navigation import autenticao_ativa, NavegacaoInesperada
        class Pagina: url = 'https://sisregiii.saude.gov.br/'
        with patch('sisreg_navigation._encontrar', side_effect=NavegacaoInesperada('menu ausente')):
            self.assertFalse(autenticao_ativa(Pagina(),timeout=10))

    def test_timeout_no_formulario_nao_preenche_senha(self):
        from playwright.sync_api import TimeoutError as PlaywrightTimeout
        from sisreg_login import FormularioInesperado, submeter_login
        class Campo:
            def wait_for(self, **kwargs):raise PlaywrightTimeout('campo ausente')
            def fill(self, value, **kwargs):raise AssertionError('NÃO DEVE PREENCHER')
        class Pagina:
            url='https://sisregiii.saude.gov.br/'
            def locator(self, _):return Campo()
        with self.assertRaises(FormularioInesperado):
            submeter_login(Pagina(), 'operador-ficticio', 'senha-ficticia')
