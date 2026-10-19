"""SISREG III — protótipo institucional de autenticação assistida.

Este protótipo apenas abre o navegador, preenche as credenciais introduzidas
pela própria pessoa operadora e submete o formulário identificado.
Não consulta prontuários, não coleta dados de pacientes e não salva senhas.

USO CONDICIONADO À AUTORIZAÇÃO DA REGULAÇÃO/TI.
"""

from __future__ import annotations

import queue
import os
from pathlib import Path
from tkinter import filedialog
from datetime import datetime
from aih_extract import ler_espelhos_pdf, cpf_valido, cns_formato
from planilha import SessaoPlanilha
from sisreg_navigation import consultar_cadastro, consultar_solicitacoes_amb, NavegacaoInesperada
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

VERSAO = "0.2.0 — espelho de AIH e consulta ambulatorial assistida"
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
    """Interface de três passos; todas as operações do Playwright usam uma só thread."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        root.title('RPA SISREG · Preparação e consulta assistida — v0.2')
        root.geometry('1010x736')
        root.minsize(885, 655)
        root.configure(bg=FUNDO)
        root.protocol('WM_DELETE_WINDOW', self.encerrar)
        self.eventos: queue.Queue = queue.Queue()
        self.comandos: queue.Queue = queue.Queue()
        self.parar = threading.Event()
        self.thread_navegador: threading.Thread | None = None
        self.sessao = SessaoPlanilha()
        self.arquivo_planilha: Path | None = None
        self.arquivo_pdf: Path | None = None
        self.carregando = False
        self.browser_ready = False
        self.usuario = tk.StringVar()
        self.senha = tk.StringVar()
        self.navegador = tk.StringVar(value='Google Chrome')
        self.login_confirmado = tk.BooleanVar(value=False)
        self.identidade_confirmada = tk.BooleanVar(value=False)
        self.cns_confirmado = tk.StringVar()
        self.status = tk.StringVar(value='Selecione a planilha-padrão e, se disponível, o PDF das AIHs.')
        self.resumo = tk.StringVar(value='Nenhum registro carregado.')
        self.selecionado = tk.StringVar(value='Nenhuma AIH selecionada.')
        self._montar()
        root.after(140, self._ler_eventos)

    def _montar(self) -> None:
        estilos = ttk.Style()
        estilos.theme_use('clam')
        estilos.configure('TFrame', background=FUNDO)
        estilos.configure('TLabel', background=FUNDO, foreground='#183b59', font=('Segoe UI', 10))
        estilos.configure('TButton', font=('Segoe UI', 10), padding=8)
        estilos.configure('Acao.TButton', background=AZUL, foreground='white', font=('Segoe UI', 10, 'bold'), padding=9)
        estilos.map('Acao.TButton', background=[('active', '#11669e')])
        estilos.configure('TEntry', font=('Segoe UI', 11), padding=5)
        estilos.configure('Treeview', font=('Segoe UI', 9), rowheight=25)
        estilos.configure('Treeview.Heading', font=('Segoe UI', 9, 'bold'))

        topo = tk.Frame(self.root, bg=AZUL, height=81)
        topo.pack(fill='x')
        topo.pack_propagate(False)
        tk.Label(topo, text='RPA SISREG  |  Conferência assistida', bg=AZUL,
                 fg='white', font=('Segoe UI', 17, 'bold')).pack(anchor='w', padx=23, pady=(12, 0))
        tk.Label(topo, text='Versão 0.2 · PDF + Planilha + SISREG  |  Processamento local',
                 bg=AZUL, fg='#cce7fa', font=('Segoe UI', 10)).pack(anchor='w', padx=24)

        corpo = ttk.Frame(self.root, padding=13)
        corpo.pack(fill='both', expand=True)
        self.abas = ttk.Notebook(corpo)
        self.abas.pack(fill='both', expand=True)
        self.tab_arquivos = ttk.Frame(self.abas, padding=12)
        self.tab_sisreg = ttk.Frame(self.abas, padding=15)
        self.tab_saida = ttk.Frame(self.abas, padding=15)
        self.abas.add(self.tab_arquivos, text='  1  Arquivos e AIHs  ')
        self.abas.add(self.tab_sisreg, text='  2  Consulta SISREG  ')
        self.abas.add(self.tab_saida, text='  3  Planilha de saída  ')

        arqs = self.tab_arquivos
        ttk.Label(arqs, text='Importe os dados antes de abrir a sessão SISREG.',
                  font=('Segoe UI', 11, 'bold')).pack(anchor='w', pady=(0, 10))
        faixa = ttk.Frame(arqs)
        faixa.pack(fill='x')
        ttk.Button(faixa, text='Escolher XLSX do hospital', command=self._escolher_xlsx).pack(side='left')
        self.lbl_xlsx = ttk.Label(faixa, text='Nenhum XLSX escolhido')
        self.lbl_xlsx.pack(side='left', padx=12)
        faixa_pdf = ttk.Frame(arqs)
        faixa_pdf.pack(fill='x', pady=(7, 7))
        ttk.Button(faixa_pdf, text='Escolher espelho PDF (opcional)', command=self._escolher_pdf).pack(side='left')
        self.lbl_pdf = ttk.Label(faixa_pdf, text='Não informado')
        self.lbl_pdf.pack(side='left', padx=12)
        faixa_ctrl = ttk.Frame(arqs)
        faixa_ctrl.pack(fill='x', pady=(5, 8))
        self.btn_preparar = ttk.Button(faixa_ctrl, text='Preparar conferência',
                                       style='Acao.TButton', command=self._preparar)
        self.btn_preparar.pack(side='left')
        ttk.Label(faixa_ctrl, textvariable=self.resumo).pack(side='left', padx=12)

        tabela_container = ttk.Frame(arqs)
        tabela_container.pack(fill='both', expand=True)
        cols = ('aba', 'linha', 'aih', 'paciente', 'cpf', 'cns', 'situacao')
        self.tabela = ttk.Treeview(tabela_container, columns=cols, show='headings', selectmode='browse')
        config = [('aba','Aba',145),('linha','Linha',53),('aih','AIH',130),
                  ('paciente','Paciente',210),('cpf','CPF',110),('cns','CNS',143),
                  ('situacao','Situação',188)]
        for chave, titulo, largura in config:
            self.tabela.heading(chave, text=titulo)
            self.tabela.column(chave, width=largura, minwidth=45, stretch=(chave=='paciente'))
        barra = ttk.Scrollbar(tabela_container, orient='vertical', command=self.tabela.yview)
        self.tabela.configure(yscrollcommand=barra.set)
        self.tabela.pack(side='left', fill='both', expand=True)
        barra.pack(side='right', fill='y')
        self.tabela.bind('<<TreeviewSelect>>', self._ao_selecionar)
        ttk.Label(arqs, text='Selecione uma linha e abra a etapa 2 para pesquisar o paciente. '
                  'A AIH com hífen e sem hífen é tratada como o mesmo identificador.',
                  wraplength=890).pack(anchor='w', pady=(6, 0))

        tab = self.tab_sisreg
        ttk.Label(tab, textvariable=self.selecionado, font=('Segoe UI', 12, 'bold')).pack(anchor='w', pady=(0, 12))
        form = ttk.Frame(tab)
        form.pack(fill='x', pady=(0, 8))
        ttk.Label(form, text='Usuário SISREG').grid(row=0, column=0, sticky='w')
        ttk.Label(form, text='Senha (apenas em memória)').grid(row=0, column=1, sticky='w', padx=(12, 0))
        ttk.Entry(form, textvariable=self.usuario, width=25).grid(row=1, column=0, sticky='ew', pady=(3, 8))
        ttk.Entry(form, textvariable=self.senha, show='•', width=25).grid(row=1, column=1, sticky='ew', padx=(12, 0), pady=(3, 8))
        ttk.Label(form, text='Navegador').grid(row=0, column=2, sticky='w', padx=(12, 0))
        ttk.Combobox(form, textvariable=self.navegador, state='readonly',
                     values=['Microsoft Edge','Google Chrome'], width=18).grid(row=1, column=2, padx=(12, 0), pady=(3, 8))
        form.columnconfigure(0, weight=1)
        form.columnconfigure(1, weight=1)
        self.btn_login = ttk.Button(tab, text='Abrir SISREG e enviar login',
                                    style='Acao.TButton', command=self._iniciar_login)
        self.btn_login.pack(anchor='w', pady=(0, 6))
        ttk.Checkbutton(tab, text='Confirmei que o SISREG aceitou meu login no navegador',
                        variable=self.login_confirmado).pack(anchor='w', pady=(1, 10))
        ttk.Separator(tab, orient='horizontal').pack(fill='x', pady=(1, 9))
        ttk.Label(tab, text='Consulta 1 — Cadastro pelo CPF ou CNS',
                  font=('Segoe UI', 11, 'bold')).pack(anchor='w')
        ttk.Label(tab, text='Usa o identificador presente na planilha/PDF. O SISREG abre no navegador; '
                  'confira o nome e o CNS manualmente. Não há captura automática desses dados nesta etapa.',
                  wraplength=860).pack(anchor='w', pady=(3, 6))
        ttk.Button(tab, text='Pesquisar cadastro do paciente',
                   command=self._consulta_cadastro).pack(anchor='w', pady=(0, 9))
        confirmacao = ttk.Frame(tab)
        confirmacao.pack(fill='x', pady=2)
        ttk.Label(confirmacao, text='CNS visualizado no SISREG:').grid(row=0, column=0, sticky='w')
        ttk.Entry(confirmacao, textvariable=self.cns_confirmado, width=27).grid(row=1, column=0, sticky='w', pady=(3, 4))
        ttk.Checkbutton(confirmacao, text='Conferi o nome do paciente no SISREG',
                        variable=self.identidade_confirmada).grid(row=1, column=1, sticky='w', padx=(16, 0))
        ttk.Button(tab, text='Confirmar CNS para esta AIH',
                   command=self._confirmar_cns).pack(anchor='w', pady=(5, 10))
        ttk.Separator(tab, orient='horizontal').pack(fill='x', pady=(1, 8))
        ttk.Label(tab, text='Consulta 2 — Consulta Amb → Solicitações',
                  font=('Segoe UI', 11, 'bold')).pack(anchor='w')
        ttk.Label(tab, text='Após confirmar o CNS, navega até Solicitações, preenche o CNS e abre a pesquisa. '
                  'Ainda NÃO interpreta nem confirma solicitações.', wraplength=860).pack(anchor='w', pady=(3, 6))
        ttk.Button(tab, text='Pesquisar solicitações pelo CNS', style='Acao.TButton',
                   command=self._consultar_solicitacoes).pack(anchor='w', pady=(0, 5))

        saida = self.tab_saida
        ttk.Label(saida, text='Salvar uma cópia enriquecida da planilha do hospital',
                  font=('Segoe UI', 12, 'bold')).pack(anchor='w', pady=(0, 8))
        ttk.Label(saida, text='Preserva as três abas e as sete colunas originais. '
                  'Adiciona cinco colunas de rastreabilidade à direita; completa somente CPF/CNS '
                  'vazios e verificados, sem sobrescrever valores conflitantes. '
                  'A pesquisa de solicitações fica registrada apenas como ABERTA, não como confirmada.',
                  wraplength=845).pack(anchor='w', pady=(0, 15))
        ttk.Button(saida, text='Salvar cópia XLSX com as conferências',
                   style='Acao.TButton', command=self._salvar).pack(anchor='w')
        ttk.Label(saida, text='A planilha contém dados sensíveis. Salve apenas em pasta institucional '
                  'autorizada; o arquivo não possui criptografia automática.',
                  wraplength=845).pack(anchor='w', pady=(17, 0))

        rodape = ttk.Frame(corpo)
        rodape.pack(fill='x', pady=(9, 1))
        ttk.Label(rodape, textvariable=self.status, wraplength=880).pack(side='left', fill='x', expand=True)
        ttk.Button(rodape, text='Encerrar', command=self.encerrar).pack(side='right')

    def _escolher_xlsx(self) -> None:
        f = filedialog.askopenfilename(title='Planilha-padrão do hospital',
                                       filetypes=[('Excel XLSX', '*.xlsx')])
        if f:
            self.arquivo_planilha = Path(f)
            self.lbl_xlsx.configure(text=self.arquivo_planilha.name)

    def _escolher_pdf(self) -> None:
        f = filedialog.askopenfilename(title='Espelho de AIH em PDF (opcional)',
                                       filetypes=[('PDF', '*.pdf')])
        if f:
            self.arquivo_pdf = Path(f)
            self.lbl_pdf.configure(text=self.arquivo_pdf.name)

    def _preparar(self) -> None:
        if self.carregando:
            return
        if not self.arquivo_planilha:
            self.status.set('Selecione primeiro a planilha XLSX.')
            return
        self.carregando = True
        self.btn_preparar.configure(state='disabled')
        self.status.set('Lendo planilha e indexando PDF localmente...')
        def tarefa():
            try:
                sessao = SessaoPlanilha()
                sessao.carregar(self.arquivo_planilha)
                info = 'Sem PDF.'
                if self.arquivo_pdf:
                    index, avisos = ler_espelhos_pdf(self.arquivo_pdf)
                    sessao.complementar_pdf(index, self.arquivo_pdf)
                    info = f'{len(index)} AIHs indexadas no PDF.'
                    if avisos:
                        info += ' PDF sem espelhos pesquisáveis ou estrutura não reconhecida.'
                self.eventos.put(('preparado', (sessao, info)))
            except Exception as exc:
                self.eventos.put(('erro_preparo', str(exc)))
        threading.Thread(target=tarefa, daemon=True).start()

    def _atualizar_tabela(self) -> None:
        selecionar = self.tabela.selection()
        manter = selecionar[0] if selecionar else None
        for iid in self.tabela.get_children():
            self.tabela.delete(iid)
        for indice, r in enumerate(self.sessao.registros):
            self.tabela.insert('', 'end', iid=str(indice), values=(
                r.aba, r.linha, r.aih, r.nome, r.cpf, r.cns, r.situacao
            ))
        if manter and self.tabela.exists(manter):
            self.tabela.selection_set(manter)

    def _registro(self):
        s = self.tabela.selection()
        if not s:
            raise ValueError('Selecione uma AIH na tabela da etapa 1.')
        return self.sessao.registros[int(s[0])]

    def _ao_selecionar(self, _ev=None) -> None:
        try:
            r = self._registro()
            self.selecionado.set(f'{r.nome}   |   AIH {r.aih}   |   {r.aba}, linha {r.linha}')
            self.cns_confirmado.set(r.cns)
            self.identidade_confirmada.set(False)
        except Exception:
            pass

    def _iniciar_login(self) -> None:
        if self.thread_navegador and self.thread_navegador.is_alive():
            self.status.set('Já existe uma sessão de navegador ativa.')
            return
        u, s = self.usuario.get().strip(), self.senha.get()
        if not u or not s:
            self.status.set('Preencha usuário e senha; serão apagados dos campos ao iniciar.')
            return
        canal = 'msedge' if self.navegador.get() == 'Microsoft Edge' else 'chrome'
        self.usuario.set('')
        self.senha.set('')
        self.parar.clear()
        self.browser_ready = False
        self.login_confirmado.set(False)
        self.thread_navegador = threading.Thread(
            target=self._navegador_worker, args=(u, s, canal), daemon=True)
        self.thread_navegador.start()
        self.status.set('Abrindo navegador e aguardando os controles de login...')

    def _navegador_worker(self, usuario: str, senha: str, canal: str) -> None:
        browser = None
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(channel=canal, headless=False)
                contexto = browser.new_context(accept_downloads=False)
                pagina = contexto.new_page()
                try:
                    pagina.goto(URL_SISREG, wait_until='domcontentloaded', timeout=45000)
                    submeter_login(pagina, usuario, senha)
                    self.eventos.put(('login_enviado', None))
                except Exception:
                    self.eventos.put(('erro_login', 'Não foi possível enviar o login. '
                                      'Verifique a página no navegador; nenhum login foi confirmado.'))
                    return
                finally:
                    usuario = ''
                    senha = ''
                while not self.parar.wait(0.1):
                    try:
                        cmd, identificador, idx = self.comandos.get(timeout=0.2)
                    except queue.Empty:
                        continue
                    try:
                        if not browser.is_connected():
                            raise NavegacaoInesperada('O navegador foi fechado.')
                        # Quando o site abriu uma nova aba, só usar página oficial.
                        validas = [pg for pg in contexto.pages if endereco_oficial(pg.url) and not pg.is_closed()]
                        if not validas:
                            raise NavegacaoInesperada('Página oficial não encontrada na sessão.')
                        pagina = validas[-1]
                        if cmd == 'cadastro':
                            consultar_cadastro(pagina, identificador)
                            self.eventos.put(('cadastro_aberto', idx))
                        elif cmd == 'solicitacoes':
                            consultar_solicitacoes_amb(pagina, identificador)
                            self.eventos.put(('solicitacoes_abertas', idx))
                    except Exception:
                        self.eventos.put(('erro_navegacao',
                             'A tela esperada não foi localizada, ou o SISREG não respondeu. '
                             'Confira o navegador; o robô não prosseguiu automaticamente.'))
        except Exception:
            self.eventos.put(('erro_login', 'Falha ao abrir navegador. Confira Edge/Chrome e liberação da TI.'))
        finally:
            if browser is not None:
                try:
                    browser.close()
                except Exception:
                    pass
            self.eventos.put(('navegador_parou', None))

    def _consulta_cadastro(self) -> None:
        try:
            r = self._registro()
            if not self.browser_ready or not self.login_confirmado.get():
                raise ValueError('Primeiro abra o SISREG e confirme o login no navegador.')
            if not r.aih or not r.nome:
                raise ValueError('AIH e nome são necessários para a conferência.')
            id = r.cpf if cpf_valido(r.cpf) else (r.cns if cns_formato(r.cns) else '')
            if not id:
                raise ValueError('Não há CPF válido nem CNS para pesquisa. Revise o espelho da AIH.')
            idx = self.sessao.registros.index(r)
            self.comandos.put(('cadastro', id, idx))
            self.status.set('Pesquisando o cadastro no SISREG; confira o nome e o CNS no navegador.')
        except ValueError as exc:
            self.status.set(str(exc))

    def _confirmar_cns(self) -> None:
        try:
            r = self._registro()
            if not self.browser_ready or not self.login_confirmado.get():
                raise ValueError('Confirme primeiro o login no navegador.')
            self.sessao.confirmar_cns_manual(r, self.cns_confirmado.get(),
                                             self.identidade_confirmada.get())
            self._atualizar_tabela()
            self.status.set('CNS conferido e associado à AIH em memória. Salve a cópia XLSX depois.')
        except ValueError as exc:
            self.status.set(str(exc))

    def _consultar_solicitacoes(self) -> None:
        try:
            r = self._registro()
            if not self.browser_ready or not self.login_confirmado.get():
                raise ValueError('Abra e confirme a sessão SISREG primeiro.')
            if not r.revisado or not cns_formato(r.cns):
                raise ValueError('Confirme manualmente a identidade e o CNS antes de continuar.')
            idx = self.sessao.registros.index(r)
            self.comandos.put(('solicitacoes', r.cns, idx))
            self.status.set('Abrindo pesquisa de solicitações pelo CNS. Resultado exige análise humana.')
        except ValueError as exc:
            self.status.set(str(exc))

    def _salvar(self) -> None:
        if not self.sessao.origem:
            self.status.set('Prepare primeiro a planilha.')
            return
        nome = self.sessao.origem.stem + '_RPA_CONFERENCIA.xlsx'
        destino = filedialog.asksaveasfilename(title='Salvar cópia — somente pasta institucional autorizada',
                                                defaultextension='.xlsx', initialfile=nome,
                                                filetypes=[('Planilha Excel','*.xlsx')])
        if not destino:
            return
        try:
            p = self.sessao.salvar_copia(destino)
            self.status.set(f'Cópia salva: {p.name}. A planilha original foi preservada.')
        except Exception as exc:
            self.status.set('Falha ao salvar cópia: ' + str(exc))

    def _ler_eventos(self) -> None:
        try:
            while True:
                evt, dado = self.eventos.get_nowait()
                if evt == 'preparado':
                    sessao, info = dado
                    self.sessao = sessao
                    self._atualizar_tabela()
                    self.resumo.set(f'{len(sessao.registros)} registros. {info}')
                    self.status.set('Arquivos preparados. Selecione uma AIH e passe para a etapa 2.')
                    self.carregando = False
                    self.btn_preparar.configure(state='normal')
                elif evt == 'erro_preparo':
                    self.carregando = False
                    self.btn_preparar.configure(state='normal')
                    self.status.set('Não foi possível preparar: ' + str(dado))
                elif evt == 'login_enviado':
                    self.browser_ready = True
                    self.status.set('Formulário enviado. Verifique o login no SISREG e marque a confirmação.')
                elif evt == 'cadastro_aberto':
                    self.status.set('Pesquisa de cadastro enviada. Confira paciente e CNS na página aberta.')
                elif evt == 'solicitacoes_abertas':
                    if isinstance(dado, int) and dado < len(self.sessao.registros):
                        self.sessao.marcar_consulta_aberta(self.sessao.registros[dado])
                        self._atualizar_tabela()
                    self.status.set('Pesquisa de solicitações aberta. Ainda não houve conferência dos resultados.')
                elif evt in ('erro_login', 'erro_navegacao'):
                    self.status.set(str(dado))
                elif evt == 'navegador_parou':
                    self.browser_ready = False
                    self.login_confirmado.set(False)
        except queue.Empty:
            pass
        self.root.after(140, self._ler_eventos)

    def encerrar(self) -> None:
        self.parar.set()
        self.usuario.set('')
        self.senha.set('')
        self.root.after(270, self.root.destroy)


def main() -> None:
    janela = tk.Tk()
    Aplicativo(janela)
    janela.mainloop()


if __name__ == '__main__':
    main()
