import importlib.util
import ast
from unittest.mock import patch
import pathlib
import unittest

PATH = pathlib.Path(__file__).resolve().parents[1] / 'src' / 'sisreg_login.py'
spec = importlib.util.spec_from_file_location('sisreg_login', PATH)
app = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app)


class Campo:
    def __init__(self, tipo):
        self.tipo = tipo
        self.acoes = []

    def wait_for(self, **kwargs):
        self.acoes.append(('wait', kwargs['state']))

    def get_attribute(self, chave):
        return self.tipo if chave == 'type' else None

    def fill(self, valor, **kwargs):
        self.acoes.append(('fill', valor))

    def click(self, **kwargs):
        self.acoes.append(('click', None))


class Pagina:
    def __init__(self, url='https://sisregiii.saude.gov.br/'):
        self.url = url
        self.campos = {
            'xpath=' + app.XPATH_USUARIO: Campo('text'),
            'xpath=' + app.XPATH_SENHA: Campo('password'),
            'xpath=' + app.XPATH_ENTRAR: Campo('submit'),
        }

    def locator(self, chave):
        return self.campos[chave]


class SegurancaETestes(unittest.TestCase):
    def test_endereco_oficial_https(self):
        self.assertTrue(app.endereco_oficial('https://sisregiii.saude.gov.br/'))

    def test_redirecionamento_externo_bloqueado(self):
        self.assertFalse(app.endereco_oficial('https://sisregiii.saude.gov.br.evil.test/'))

    def test_http_bloqueado(self):
        self.assertFalse(app.endereco_oficial('http://sisregiii.saude.gov.br/'))

    def test_url_com_userinfo_bloqueada(self):
        self.assertFalse(app.endereco_oficial('https://x:y@sisregiii.saude.gov.br/'))

    def test_porta_inesperada_bloqueada(self):
        self.assertFalse(app.endereco_oficial('https://sisregiii.saude.gov.br:8443/'))

    def test_preenche_e_envia_formulario(self):
        pagina = Pagina()
        app.submeter_login(pagina, 'usuario-teste', 'senha-ficticia')
        self.assertIn(('fill', 'usuario-teste'), pagina.campos['xpath=' + app.XPATH_USUARIO].acoes)
        self.assertIn(('fill', 'senha-ficticia'), pagina.campos['xpath=' + app.XPATH_SENHA].acoes)
        self.assertIn(('click', None), pagina.campos['xpath=' + app.XPATH_ENTRAR].acoes)

    def test_nao_preenche_host_desconhecido(self):
        pagina = Pagina(url='https://outro.gov.br/')
        with self.assertRaises(app.FormularioInesperado):
            app.submeter_login(pagina, 'user', 'secret')
        self.assertFalse(any(a[0] == 'fill' for c in pagina.campos.values() for a in c.acoes))

    def test_nao_preenche_se_campo_senha_nao_for_password(self):
        pagina = Pagina()
        pagina.campos['xpath=' + app.XPATH_SENHA].tipo = 'text'
        with self.assertRaises(app.FormularioInesperado):
            app.submeter_login(pagina, 'user', 'secret')
        self.assertFalse(any(a[0] == 'fill' for c in pagina.campos.values() for a in c.acoes))

    def test_nao_preenche_se_botao_for_outro_campo(self):
        pagina = Pagina()
        pagina.campos['xpath=' + app.XPATH_ENTRAR].tipo = 'password'
        with self.assertRaises(app.FormularioInesperado):
            app.submeter_login(pagina, 'user', 'secret')
        self.assertFalse(any(a[0] == 'fill' for c in pagina.campos.values() for a in c.acoes))


if __name__ == '__main__':
    unittest.main()

class TesteInicializacaoDoExecutavel(unittest.TestCase):
    def test_entrypoint_nao_pode_ser_removido(self):
        arvore = ast.parse(PATH.read_text(encoding='utf-8'))
        funcoes = {n.name for n in arvore.body if isinstance(n, ast.FunctionDef)}
        self.assertIn('main', funcoes)
        guardas = [n for n in arvore.body if isinstance(n, ast.If)
                   and isinstance(n.test, ast.Compare)
                   and isinstance(n.test.left, ast.Name)
                   and n.test.left.id == '__name__']
        self.assertTrue(any(isinstance(n, ast.Expr) and isinstance(n.value, ast.Call)
                            and isinstance(n.value.func, ast.Name)
                            and n.value.func.id == 'main'
                            for g in guardas for n in g.body))

    def test_main_deve_criar_janela_tkinter(self):
        with patch.object(app.tk, 'Tk') as criar, patch.object(app, 'Aplicativo') as aplicativo:
            app.main()
            aplicativo.assert_called_once_with(criar.return_value)
            criar.return_value.mainloop.assert_called_once()
