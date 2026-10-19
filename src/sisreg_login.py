"""SISREG III — protótipo institucional de autenticação assistida.

Este protótipo apenas abre o navegador, preenche as credenciais introduzidas
pela própria pessoa operadora e submete o formulário identificado.
Não consulta prontuários, não coleta dados de pacientes e não salva senhas.

USO CONDICIONADO À AUTORIZAÇÃO DA REGULAÇÃO/TI.
"""

from __future__ import annotations

import queue
import threading
import tkinter as tk
from tkinter import ttk
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

URL_SISREG = "https://sisregiii.saude.gov.br/"
HOST_SISREG = "sisregiii.saude.gov.br"

# Seletores fornecidos pela pessoa solicitante em 19/10/2026.
XPATH_USUARIO = "/html/body/div[1]/div/div[4]/form/div/div[1]/div[1]/div[2]/input"
XPATH_SENHA = "/html/body/div[1]/div/div[4]/form/div/div[1]/div[1]/div[5]/input"
XPATH_ENTRAR = "/html/body/div[1]/div/div[4]/form/div/div[1]/div[1]/div[8]/input"

VERSAO = "0.1.0 — teste de login"
AZUL = "#063c68"
FUNDO = "#f2f6fa"


class FormularioInesperado(Exception):
    """O site ou os campos não correspondem aos esperados."""


def endereco_oficial(url: str) -> bool:
    """Só envia credenciais ao host oficial em HTTPS, sem porta alternativa."""
    try:
        u = urlparse(url)
        return (
            u.scheme.lower() == "https"
            and u.hostname is not None
            and u.hostname.lower() == HOST_SISREG
            and u.port in (None, 443)
            and not u.username
            and not u.password
        )
    except ValueError:
        return False


def submeter_login(page, usuario: str, senha: str) -> None:
    """Preenche três XPaths confirmados; falha fechada se URL/formulário mudar.

    Não tenta contornar CAPTCHA/MFA nem interpreta sucesso de autenticação.
    """
    if not endereco_oficial(page.url):
        raise FormularioInesperado(
            "A página não está no endereço HTTPS oficial do SISREG. "
            "Nenhuma credencial foi enviada."
        )
    campos = {
        "usuario": page.locator("xpath=" + XPATH_USUARIO),
        "senha": page.locator("xpath=" + XPATH_SENHA),
        "entrar": page.locator("xpath=" + XPATH_ENTRAR),
    }
    try:
        for campo in campos.values():
            campo.wait_for(state="visible", timeout=18000)
    except PlaywrightTimeout as exc:
        raise FormularioInesperado(
            "Os campos informados não estão visíveis. O SISREG pode ter alterado "
            "a página. Faça o login manualmente no navegador."
        ) from exc

    # Impede preencher senha caso o XPath passe a apontar para um campo não sensível.
    tipo_senha = (campos["senha"].get_attribute("type") or "").lower()
    tipo_usuario = (campos["usuario"].get_attribute("type") or "text").lower()
    tipo_entrar = (campos["entrar"].get_attribute("type") or "submit").lower()
    if tipo_senha != "password" or tipo_usuario not in ("text", "email", "search"):
        raise FormularioInesperado(
            "A estrutura dos campos mudou. Credenciais não foram preenchidas."
        )
    if tipo_entrar not in ("submit", "button", "image"):
        raise FormularioInesperado(
            "O botão de entrada mudou. Nenhuma credencial foi enviada."
        )

    # Segunda checagem de origem imediatamente antes de preencher credenciais.
    if not endereco_oficial(page.url):
        raise FormularioInesperado("Origem da página mudou; operação cancelada.")

    campos["usuario"].fill(usuario, timeout=10000)
    campos["senha"].fill(senha, timeout=10000)
    # Segurança adicional: conferir de novo a origem antes de submeter.
    if not endereco_oficial(page.url):
        campos["senha"].fill("")
        raise FormularioInesperado("Origem da página mudou; operação cancelada.")
    campos["entrar"].click(timeout=15000, no_wait_after=True)


class Aplicativo:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("SISREG III | Login assistido — Protótipo")
        self.root.geometry("535x427")
        self.root.minsize(485, 410)
        self.root.configure(bg=FUNDO)
        self.root.protocol("WM_DELETE_WINDOW", self.encerrar)

        self.mensagens: queue.Queue[tuple[str, str]] = queue.Queue()
        self.parar = threading.Event()
        self.trabalhando = False
        self.usuario = tk.StringVar()
        self.senha = tk.StringVar()
        self.exibir_senha = tk.BooleanVar(value=False)
        self.navegador = tk.StringVar(value="Microsoft Edge")
        self.status = tk.StringVar(value="Pronto para abrir o SISREG em uma nova janela.")
        self._montar_interface()
        self.root.after(120, self.processar_mensagens)

    def _montar_interface(self) -> None:
        estilos = ttk.Style()
        estilos.theme_use("clam")
        estilos.configure("TFrame", background=FUNDO)
        estilos.configure("TLabel", background=FUNDO, foreground="#24405a", font=("Segoe UI", 10))
        estilos.configure("TEntry", font=("Segoe UI", 11), padding=7)
        estilos.configure("TCombobox", font=("Segoe UI", 10), padding=4)
        estilos.configure("Primary.TButton", font=("Segoe UI", 10, "bold"), padding=10,
                          background=AZUL, foreground="#ffffff")
        estilos.map("Primary.TButton", background=[("active", "#0b598d")])
        estilos.configure("TButton", font=("Segoe UI", 10), padding=8)

        topo = tk.Frame(self.root, bg=AZUL, height=77)
        topo.pack(fill="x")
        topo.pack_propagate(False)
        tk.Label(topo, text="SISREG III  |  Login assistido", bg=AZUL,
                 fg="white", font=("Segoe UI", 16, "bold")).pack(anchor="w", padx=23, pady=(13, 0))
        tk.Label(topo, text="Protótipo de acesso — somente autenticação", bg=AZUL,
                 fg="#d3e8f6", font=("Segoe UI", 9)).pack(anchor="w", padx=24)

        corpo = ttk.Frame(self.root, padding=(23, 14, 23, 0))
        corpo.pack(fill="both", expand=True)
        ttk.Label(corpo, text="Usuário institucional").pack(anchor="w")
        self.entrada_usuario = ttk.Entry(corpo, textvariable=self.usuario)
        self.entrada_usuario.pack(fill="x", pady=(3, 10))
        ttk.Label(corpo, text="Senha (não será armazenada)").pack(anchor="w")
        self.entrada_senha = ttk.Entry(corpo, textvariable=self.senha, show="•")
        self.entrada_senha.pack(fill="x", pady=(3, 1))
        ttk.Checkbutton(corpo, text="Mostrar senha", variable=self.exibir_senha,
                        command=self.alternar_senha).pack(anchor="w", pady=(0, 6))

        ttk.Label(corpo, text="Navegador disponível no computador").pack(anchor="w")
        ttk.Combobox(corpo, textvariable=self.navegador, state="readonly",
                     values=["Microsoft Edge", "Google Chrome"]).pack(fill="x", pady=(3, 10))

        botoes = ttk.Frame(corpo)
        botoes.pack(fill="x", pady=(3, 4))
        self.botao_entrar = ttk.Button(botoes, text="Abrir SISREG e entrar",
                                       style="Primary.TButton", command=self.iniciar)
        self.botao_entrar.pack(side="left", fill="x", expand=True)
        self.botao_encerrar = ttk.Button(botoes, text="Encerrar", command=self.encerrar)
        self.botao_encerrar.pack(side="left", padx=(9, 0))
        ttk.Label(corpo, textvariable=self.status, wraplength=465,
                  foreground="#315b70").pack(anchor="w", pady=(8, 2))
        ttk.Label(corpo, text="A autenticação deve ser autorizada pela Regulação/TI. "
                  "Não fecha nem altera solicitações e não contorna CAPTCHA ou MFA.",
                  wraplength=470, foreground="#5f7180").pack(anchor="w", pady=(7, 0))
        self.entrada_usuario.focus_set()

    def alternar_senha(self) -> None:
        self.entrada_senha.configure(show="" if self.exibir_senha.get() else "•")

    def iniciar(self) -> None:
        if self.trabalhando:
            return
        u, s = self.usuario.get().strip(), self.senha.get()
        if not u or not s:
            self.status.set("Preencha usuário e senha para iniciar.")
            return
        canal = "msedge" if self.navegador.get() == "Microsoft Edge" else "chrome"
        self.parar.clear()
        self.trabalhando = True
        self.botao_entrar.configure(state="disabled")
        # Remove dos widgets; valores ficam só em memória até o preenchimento.
        self.usuario.set("")
        self.senha.set("")
        self.status.set("Abrindo o navegador institucional...")
        threading.Thread(target=self.executar, args=(u, s, canal), daemon=True).start()

    def executar(self, usuario: str, senha: str, canal: str) -> None:
        navegador = None
        try:
            with sync_playwright() as p:
                try:
                    navegador = p.chromium.launch(channel=canal, headless=False)
                except Exception:
                    self.mensagens.put(("erro", "Não foi possível abrir o navegador escolhido. "
                                        "Confirme se ele está instalado e liberado pela TI."))
                    return
                contexto = navegador.new_context(accept_downloads=False)
                pagina = contexto.new_page()
                try:
                    pagina.goto(URL_SISREG, wait_until="domcontentloaded", timeout=40000)
                    submeter_login(pagina, usuario, senha)
                    self.mensagens.put(("info", "Formulário enviado. Confira no navegador "
                                        "se o SISREG confirmou o acesso; CAPTCHA/MFA são manuais."))
                except FormularioInesperado as exc:
                    self.mensagens.put(("erro", str(exc)))
                except PlaywrightTimeout:
                    self.mensagens.put(("erro", "O SISREG não respondeu no prazo. "
                                        "Verifique a página no navegador; não repetiremos o login automaticamente."))
                except Exception:
                    self.mensagens.put(("erro", "Não foi possível concluir o preenchimento. "
                                        "Verifique o navegador e, se necessário, faça login manualmente."))
                finally:
                    # Strings não vão para disco/log; Python não garante limpeza física de RAM.
                    usuario = ""
                    senha = ""
                while not self.parar.wait(0.3):
                    if not navegador.is_connected():
                        self.mensagens.put(("info", "A janela do navegador foi fechada."))
                        break
        finally:
            if navegador is not None:
                try:
                    navegador.close()
                except Exception:
                    pass
            self.mensagens.put(("parou", ""))

    def processar_mensagens(self) -> None:
        try:
            while True:
                tipo, mensagem = self.mensagens.get_nowait()
                if tipo in ("erro", "info"):
                    self.status.set(mensagem)
                elif tipo == "parou":
                    self.trabalhando = False
                    self.botao_entrar.configure(state="normal")
        except queue.Empty:
            pass
        self.root.after(120, self.processar_mensagens)

    def encerrar(self) -> None:
        self.parar.set()
        self.usuario.set("")
        self.senha.set("")
        self.root.after(350, self.root.destroy)


def main() -> None:
    root = tk.Tk()
    Aplicativo(root)
    root.mainloop()


if __name__ == "__main__":
    main()
