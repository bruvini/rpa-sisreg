"""SISREG III — automação autorizada de consultas em três etapas.

Lê PDF/XLSX localmente, busca CNS e dados da solicitação hospitalar no SISREG.
Não altera solicitações e não salva senha. Dados só são gravados na XLSX local.

USO CONDICIONADO À AUTORIZAÇÃO DA REGULAÇÃO/TI.
"""

from __future__ import annotations

import queue
import sys
import time
import os
from pathlib import Path
from tkinter import filedialog, messagebox
from importlib import resources
from datetime import datetime
from sisreg_navigation import (consultar_cadastro, ler_cadastro_contexto, autenticao_ativa, NavegacaoInesperada)
from aih_extract import ler_espelhos_pdf, cpf_valido, cns_formato
from planilha import SessaoPlanilha
from retomada import SaudeLote, selecionar_cadastros
from progresso import resumo_progresso, candidato_hospitalar, ficha_hospitalar_completa
from controle_sessao import AguardarHumano, desafio_visivel, servidor_indisponivel
from sisreg_navigation import NavegacaoInesperada
from sisreg_hospital import consultar_solicitacao_hospitalar, ResultadoHospital
import threading
import tkinter as tk
from tkinter import ttk
from urllib.parse import urlparse
from diretorios import pastas_de_saida
from app_info import APP_VERSION, rotulo_versao
from apresentacao import rotulo_situacao
from governanca import HistoricoExecucao, limpeza_temporarios
from estatisticas import Estatisticas, relatorio_tecnico, duracao as duracao_stats, percentual, MANUAL_SEGUNDOS, categoria_excecao

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

URL_SISREG = "https://sisregiii.saude.gov.br/"
HOST_SISREG = "sisregiii.saude.gov.br"

# Seletores fornecidos pela pessoa solicitante em 19/10/2026.
XPATH_USUARIO = "/html/body/div[1]/div/div[4]/form/div/div[1]/div[1]/div[2]/input"
XPATH_SENHA = "/html/body/div[1]/div/div[4]/form/div/div[1]/div[1]/div[5]/input"
XPATH_ENTRAR = "/html/body/div[1]/div/div[4]/form/div/div[1]/div[1]/div[8]/input"

VERSAO = APP_VERSION
MANUAL_SEGUNDOS_POR_AIH = 15
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
    """Executa PDF em lote + pesquisa somente leitura por CPF, com status e retomada."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        root.title(f'RPA SISREG · Conferência em lote — v{APP_VERSION}')
        if sys.platform == 'win32':
            try:
                raiz = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parents[1]))
                root.iconbitmap(str(raiz / 'assets' / 'Logo-SISREG.ico'))
            except (OSError, tk.TclError):
                pass
        # Caber na área útil mesmo com escalonamento/monitor institucional.
        largura=min(1160,max(820,root.winfo_screenwidth()-70))
        altura=min(850,max(590,root.winfo_screenheight()-125))
        root.geometry(f'{largura}x{altura}+18+18')
        root.minsize(min(850,largura),min(580,altura))
        if sys.platform=='win32':
            # Windows conhece a área de trabalho sem invadir a barra de tarefas.
            try: root.state('zoomed')
            except tk.TclError: pass
        root.configure(bg=FUNDO)
        root.protocol('WM_DELETE_WINDOW', self.encerrar)
        self.eventos=queue.Queue()
        self.comandos=queue.Queue()
        self.parar=threading.Event()
        self.pausa=threading.Event()
        self.thread_navegador=None
        self.login_pendente=False
        self.reiniciar_navegador=threading.Event()
        self.aguardar_humano=AguardarHumano()
        self.intervencao_pendente=False
        self.consultas_acumuladas=0
        self.sessao=SessaoPlanilha()
        self.historico = None
        self.estatisticas = Estatisticas()
        self.inicio_ciclo = None
        self.inicio_cadastro = None
        self.inicio_hospital = None
        self.tentativas_hospital = 0
        self.acertos_hospital = 0
        self.falhas_hospital = 0
        self.consultas_cadastro = 0
        self.relatorio_finalizado = False
        self.ultima_fonte = None
        self.arquivo_planilha=None
        self.arquivo_pdf=None
        self.carregando=False
        self.browser_ready=False
        self.processando=False
        self.persistencia_falhou=False
        self.navegacao_falhou=False
        self.usuario=tk.StringVar()
        self.senha=tk.StringVar()
        self.navegador=tk.StringVar(value='Google Chrome')
        self.preparo_concluido=False
        self.cadastro_concluido=False
        self.revisao_anterior=0
        self.motivos_cadastro={}
        self.atividade_preparo=tk.StringVar(value='Aguardando início.')
        self.resultado_titulo=tk.StringVar(value='')
        self.resultado_descritivo=tk.StringVar(value='')
        self.resultado_tempo=tk.StringVar(value='')
        self.resultado_arquivo=tk.StringVar(value='')
        self.cronometro=tk.StringVar(value='Tempo: 00:00')
        self.inicio_preparo=None
        self.tipo_lote='cadastro'
        self.status=tk.StringVar(value='Selecione a planilha-padrão e o espelho PDF do hospital.')
        self.resumo=tk.StringVar(value='Nenhuma conferência carregada.')
        self.progresso=tk.StringVar(value='Aguardando preparação.')
        self.resumo_cadastro=tk.StringVar(value='Taxa de completude: aguardando consulta.')
        self.tempo_cadastro=tk.StringVar(value='Tempo: aguardando · manual hipotético: 10s por consulta.')
        self.resumo_hospital=tk.StringVar(value='Completude: aguardando início.')
        self.tempo_hospital=tk.StringVar(value='Tempo: aguardando · manual hipotético: 10s por consulta.')
        self.resultado_geral=tk.StringVar(value='Aguardando conclusão das três etapas.')
        self.resultado_tempos=tk.StringVar(value='Os tempos serão calculados durante a execução.')
        self.resultado_arquivo_log=tk.StringVar(value='O TXT será salvo em Logs, ao lado do executável.')
        self.dados_atuais={'cpf':0,'cns':0,'pendentes':0,'falhas':0,'total':0}
        self.estatisticas.diagnosticar('INICIO_EXECUCAO', 'INICIO')
        self._montar()
        self.abas.tab(1,state='disabled')
        self.abas.tab(2,state='disabled')
        self.abas.tab(3,state='disabled')
        self.btn_lote.configure(state='disabled')
        root.after(140,self._ler_eventos)

    def _montar(self):
        estilo=ttk.Style();estilo.theme_use('clam')
        estilo.configure('TFrame',background=FUNDO)
        estilo.configure('TLabel',background=FUNDO,foreground='#183b59',font=('Segoe UI',10))
        estilo.configure('TButton',font=('Segoe UI',10),padding=8)
        estilo.configure('Acao.TButton',background=AZUL,foreground='#ffffff',font=('Segoe UI',10,'bold'),padding=9)
        estilo.map('Acao.TButton',background=[('active','#11669e')])
        estilo.configure('TEntry',font=('Segoe UI',11),padding=5)
        estilo.configure('Treeview',font=('Segoe UI',9),rowheight=24)
        estilo.configure('Treeview.Heading',font=('Segoe UI',9,'bold'))
        topo=tk.Frame(self.root,bg=AZUL,height=82);topo.pack(fill='x');topo.pack_propagate(False)
        # Logo PNG incorporado ao EXE; sem dependência de arquivos externos no PC da Joice.
        self.logo_cabecalho = None
        try:
            import sys
            base = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parents[1]))
            caminho_logo = base / 'assets' / 'logo_sisreg_header.png'
            self.logo_cabecalho = tk.PhotoImage(file=str(caminho_logo))
        except (OSError, tk.TclError):
            pass  # O programa funciona com cabeçalho textual se o PNG estiver indisponível.
        if self.logo_cabecalho:
            tk.Label(topo,image=self.logo_cabecalho,bg=AZUL).pack(side='left',padx=(14,10),pady=2)
        titulo=tk.Frame(topo,bg=AZUL)
        titulo.pack(side='left',fill='y')
        tk.Label(titulo,text='RPA SISREG  |  Conferência em lote',bg=AZUL,fg='white',
                 font=('Segoe UI',17,'bold')).pack(anchor='w',pady=(12,0))
        tk.Label(titulo,text=f'v{APP_VERSION} · CPF, CNS e solicitação hospitalar · cópia de trabalho automática',
                 bg=AZUL,fg='#d4e8f7',font=('Segoe UI',10)).pack(anchor='w')
        tk.Button(topo, text='ⓘ Sobre', command=self._sobre, bg='#174f79', fg='white',
                  borderwidth=0, cursor='hand2', font=('Segoe UI',10)).place(relx=0.985, y=22, anchor='ne')
        corpo=ttk.Frame(self.root,padding=13);corpo.pack(fill='both',expand=True)
        self.abas=ttk.Notebook(corpo);self.abas.pack(fill='both',expand=True)
        a=ttk.Frame(self.abas,padding=12);b=ttk.Frame(self.abas,padding=12);c=ttk.Frame(self.abas,padding=12);d=ttk.Frame(self.abas,padding=16)
        self.abas.add(a,text='  1  Planilha e PDF  ')
        self.abas.add(b,text='  2  Pesquisa em lote SISREG  ')
        self.abas.add(c,text='  3  Solicitações hospitalares  ')
        self.abas.add(d,text='  4  Resultados da execução  ')
        ttk.Label(a,text='A planilha recebida é preservada; os dados são gravados automaticamente numa cópia de trabalho.',
                  wraplength=950,font=('Segoe UI',10,'bold')).pack(anchor='w',pady=(0,10))
        seletores=ttk.Frame(a);seletores.pack(fill='x',pady=(0,8))
        for col in (0,1): seletores.columnconfigure(col,weight=1)
        quadro_xlsx=ttk.Frame(seletores,padding=8,relief='solid',borderwidth=1)
        quadro_pdf=ttk.Frame(seletores,padding=8,relief='solid',borderwidth=1)
        quadro_xlsx.grid(row=0,column=0,sticky='nsew',padx=(0,6))
        quadro_pdf.grid(row=0,column=1,sticky='nsew',padx=(6,0))
        ttk.Button(quadro_xlsx,text='📊  Selecionar planilha XLSX',style='Acao.TButton',
                   command=self._escolher_xlsx).pack(fill='x')
        self.lbl_xlsx=ttk.Label(quadro_xlsx,text='Nenhum arquivo escolhido')
        self.lbl_xlsx.pack(anchor='w',pady=(7,0))
        ttk.Button(quadro_pdf,text='📄  Selecionar espelho de AIH em PDF',style='Acao.TButton',
                   command=self._escolher_pdf).pack(fill='x')
        self.lbl_pdf=ttk.Label(quadro_pdf,text='PDF opcional')
        self.lbl_pdf.pack(anchor='w',pady=(7,0))
        fprep=ttk.Frame(a);fprep.pack(fill='x',pady=(1,8))
        self.btn_preparar=ttk.Button(fprep,text='Executar conferência',
                                    command=self._preparar,style='Acao.TButton')
        self.btn_preparar.pack(side='left')
        ttk.Label(fprep,textvariable=self.cronometro,font=('Segoe UI',11,'bold')).pack(side='left',padx=(12,8))
        self.lbl_atividade=ttk.Label(fprep,textvariable=self.atividade_preparo,wraplength=450)
        self.lbl_atividade.pack(side='left',padx=(11,0))
        self.cartao_resultado=tk.Frame(a,bg='#e9f5ed',highlightbackground='#9ccdaf',highlightthickness=1)
        tk.Label(self.cartao_resultado,textvariable=self.resultado_titulo,bg='#e9f5ed',fg='#175d39',
                 font=('Segoe UI',11,'bold')).pack(anchor='w',padx=12,pady=(9,2))
        tk.Label(self.cartao_resultado,textvariable=self.resultado_descritivo,bg='#e9f5ed',fg='#204937',
                 font=('Segoe UI',10),wraplength=955,justify='left').pack(anchor='w',padx=12,pady=(0,2))
        tk.Label(self.cartao_resultado,textvariable=self.resultado_tempo,bg='#e9f5ed',fg='#204937',
                 font=('Segoe UI',10),wraplength=955,justify='left').pack(anchor='w',padx=12,pady=(0,2))
        tk.Label(self.cartao_resultado,textvariable=self.resultado_arquivo,bg='#e9f5ed',fg='#204937',
                 font=('Segoe UI',10),wraplength=955,justify='left').pack(anchor='w',padx=12,pady=(0,9))
        grade=ttk.Frame(a);grade.pack(fill='both',expand=True)
        self.grade=grade
        cfg=[('aba','Aba',130),('linha','Linha',52),('aih','AIH',122),('paciente','Paciente',240),
             ('cpf','CPF',112),('situacao','Situação',305)]
        self.tabela=ttk.Treeview(grade,columns=[x[0] for x in cfg],show='headings')
        for chave,titulo,w in cfg:
            self.tabela.heading(chave,text=titulo)
            self.tabela.column(chave,width=w,minwidth=45,stretch=(chave=='paciente'))
        scroll=ttk.Scrollbar(grade,orient='vertical',command=self.tabela.yview)
        self.tabela.configure(yscrollcommand=scroll.set)
        self.tabela.pack(side='left',fill='both',expand=True);scroll.pack(side='right',fill='y')
        ttk.Label(a,text='Não sobrescrevemos CPFs ou CNS existentes quando houver divergência. '
                  'O processo em lote não exige seleção individual de pacientes.',wraplength=930).pack(anchor='w',pady=(7,0))
        ttk.Label(b,text='Etapa 2 — Consulta de todos os CPFs válidos no SISREG',
                  font=('Segoe UI',12,'bold')).pack(anchor='w',pady=(0,8))
        fc=ttk.Frame(b);fc.pack(fill='x',pady=(0,7))
        ttk.Label(fc,text='Usuário institucional').grid(row=0,column=0,sticky='w')
        ttk.Label(fc,text='Senha (não armazenada)').grid(row=0,column=1,sticky='w',padx=(12,0))
        ttk.Label(fc,text='Navegador').grid(row=0,column=2,sticky='w',padx=(12,0))
        ttk.Entry(fc,textvariable=self.usuario,width=25).grid(row=1,column=0,sticky='ew',pady=3)
        ttk.Entry(fc,textvariable=self.senha,show='•',width=25).grid(row=1,column=1,sticky='ew',padx=(12,0),pady=3)
        ttk.Combobox(fc,textvariable=self.navegador,state='readonly',width=19,
                     values=['Google Chrome','Microsoft Edge']).grid(row=1,column=2,sticky='ew',padx=(12,0),pady=3)
        fc.columnconfigure(0,weight=2);fc.columnconfigure(1,weight=2);fc.columnconfigure(2,weight=1)
        self.btn_login=ttk.Button(b,text='Abrir SISREG e entrar',style='Acao.TButton',command=self._iniciar_login)
        self.btn_login.pack(anchor='w',pady=(0,7))
        self.aviso_verificacao=ttk.Label(
            b,text='⚠ SISREG aguardando verificação humana. Resolva no navegador e confirme aqui.',
            foreground='#8a3500', font=('Segoe UI',11,'bold'),wraplength=1040)
        self.btn_verificacao=ttk.Button(b,text='Verificar sessão e retomar',
            command=self._confirmar_verificacao)
        self.janela_verificacao=None
        # Estes controles somente aparecem quando o SISREG exigir intervenção.

        ttk.Label(b,text='A pesquisa começa automaticamente após o SISREG apresentar o menu de usuário autenticado.',
                  wraplength=920).pack(anchor='w',pady=(0,6))
        ttk.Separator(b,orient='horizontal').pack(fill='x',pady=10)
        fexec=ttk.Frame(b);fexec.pack(fill='x')
        self.btn_lote=ttk.Button(fexec,text='Retomar CPFs pendentes',
                                 command=self._iniciar_lote)
        self.btn_lote.pack(side='left',padx=(0,8))
        self.btn_pausa=ttk.Button(fexec,text='Pausar',command=self._pausar)
        self.btn_pausa.pack(side='left',padx=(0,8))
        ttk.Button(fexec,text='Tentar salvar',command=self._tentar_salvar).pack(side='left',padx=(0,8))
        ttk.Button(fexec,text='Interromper',command=self._interromper).pack(side='left')
        ttk.Label(b,textvariable=self.progresso,font=('Segoe UI',12,'bold')).pack(anchor='w',pady=(11,2))
        ttk.Label(b,textvariable=self.resumo_cadastro,font=('Segoe UI',10,'bold')).pack(anchor='w',pady=(0,2))
        ttk.Label(b,textvariable=self.tempo_cadastro,wraplength=930).pack(anchor='w',pady=(0,8))
        self.diagnostico_cns=tk.StringVar(value='O motivo das pendências será mostrado aqui após as consultas.')
        ttk.Label(b,textvariable=self.diagnostico_cns,wraplength=930).pack(anchor='w',pady=(0,8))
        self.barra=ttk.Progressbar(b,mode='determinate',maximum=100,value=0)
        self.barra.pack(fill='x')
        ttk.Label(b,text='Cadastros consultados — CNS e situação atualizados durante a pesquisa',
                  font=('Segoe UI',10,'bold')).pack(anchor='w',pady=(11,5))
        quadro_cns=ttk.Frame(b)
        quadro_cns.pack(fill='both',expand=True,pady=(0,4))
        colunas_cns=[('aba','Aba',125),('linha','Linha',48),('aih','AIH',115),
                     ('paciente','Paciente',220),('cpf','CPF',106),('cns','CNS',132),
                     ('situacao','Situação',245)]
        self.tabela_cns=ttk.Treeview(quadro_cns,columns=[x[0] for x in colunas_cns],
                                    show='headings',height=8)
        for chave,titulo,largura in colunas_cns:
            self.tabela_cns.heading(chave,text=titulo)
            self.tabela_cns.column(chave,width=largura,minwidth=40,stretch=(chave=='paciente'))
        barra_cns=ttk.Scrollbar(quadro_cns,orient='vertical',command=self.tabela_cns.yview)
        self.tabela_cns.configure(yscrollcommand=barra_cns.set)
        self.tabela_cns.pack(side='left',fill='both',expand=True)
        barra_cns.pack(side='right',fill='y')
        ttk.Label(b,text='O RPA pesquisa CPF por CPF. Só grava CNS quando o resultado mostra nome '
                  'inequívoco e um único CNS identificado. Resultados ambíguos viram pendência; '
                  'o robô segue para o próximo paciente. A etapa 3 pesquisa a AIH hospitalar.',
                  wraplength=930).pack(anchor='w',pady=(6,0))
        ttk.Label(b,text='A planilha é salva ao longo do lote. Feche-a no Excel antes de iniciar; '
                  'o programa interrompe a gravação se detectar edição externa ou bloqueio do arquivo.',
                  wraplength=930).pack(anchor='w',pady=(6,0))
        ttk.Label(c,text='Etapa 3 — Consultar solicitações hospitalares por CNS e AIH',
                  font=('Segoe UI',13,'bold')).pack(anchor='w',pady=(0,10))
        ttk.Label(c,text='Após os CNS serem preenchidos, o robô pesquisa as solicitações hospitalares do CNS, '
                  'localiza a AIH exata na tabela e abre a ficha. Só grava caráter e autorizador com '
                  'identificação inequívoca; procedimento divergente fica sinalizado para revisão.',
                  wraplength=920).pack(anchor='w',pady=(0,12))
        hf=ttk.Frame(c);hf.pack(fill='x')
        self.btn_hospital=ttk.Button(hf,text='Pesquisar solicitações hospitalares em lote',
                  style='Acao.TButton',command=self._iniciar_hospital)
        self.btn_hospital.pack(side='left',padx=(0,10))
        ttk.Button(hf,text='Pausar / Retomar',command=self._pausar).pack(side='left',padx=(0,10))
        ttk.Button(hf,text='Interromper',command=self._interromper).pack(side='left')
        self.progresso_hospital=tk.StringVar(value='Aguardando conclusão da etapa 2 e autorização para consultar.')
        ttk.Label(c,textvariable=self.progresso_hospital,font=('Segoe UI',11,'bold')).pack(anchor='w',pady=(12,3))
        ttk.Label(c,textvariable=self.resumo_hospital,font=('Segoe UI',10,'bold')).pack(anchor='w',pady=(0,2))
        ttk.Label(c,textvariable=self.tempo_hospital,wraplength=930).pack(anchor='w',pady=(0,8))
        self.barra_hospital=ttk.Progressbar(c,mode='determinate',maximum=100,value=0)
        self.barra_hospital.pack(fill='x')
        ttk.Label(c,text='Solicitações consultadas — resultado exibido durante a execução',
                  font=('Segoe UI',10,'bold')).pack(anchor='w',pady=(10,5))
        quadro_hosp=ttk.Frame(c);quadro_hosp.pack(fill='both',expand=True)
        colunas_hosp=[('aih','AIH',134),('paciente','Paciente',218),('cns','CNS',143),
                       ('carater','Caráter',105),('procedimento','Procedimento',134),
                       ('solicitacao','Solicitação',143),('situacao','Situação',215)]
        self.tabela_hospital=ttk.Treeview(quadro_hosp,columns=[x[0] for x in colunas_hosp],show='headings',height=8)
        for chave,titulo,largura in colunas_hosp:
            self.tabela_hospital.heading(chave,text=titulo)
            self.tabela_hospital.column(chave,width=largura,minwidth=40,stretch=(chave=='paciente'))
        barra_hosp=ttk.Scrollbar(quadro_hosp,orient='vertical',command=self.tabela_hospital.yview)
        self.tabela_hospital.configure(yscrollcommand=barra_hosp.set)
        self.tabela_hospital.pack(side='left',fill='both',expand=True)
        barra_hosp.pack(side='right',fill='y')
        ttk.Label(c,text='O RPA pesquisa e organiza os dados. A análise das pendências e a decisão final continuam com o fiscal. Mantenha o Excel fechado durante as consultas.',
                  wraplength=920).pack(anchor='w',pady=(14,0))
        ttk.Label(d,text='Resultados da execução',font=('Segoe UI',16,'bold')).pack(anchor='w',pady=(3,3))
        ttk.Label(d,text='Resumo operacional · a decisão fiscal permanece humana',
                  foreground='#536b7d').pack(anchor='w',pady=(0,15))
        resumo=tk.Frame(d,bg='#f4f7fa',highlightbackground='#d1dde8',highlightthickness=1)
        resumo.pack(fill='x',pady=(0,12))
        tk.Label(resumo,text='COBERTURA E PENDÊNCIAS',bg='#f4f7fa',fg='#506c83',
                 font=('Segoe UI',9,'bold')).pack(anchor='w',padx=15,pady=(12,4))
        tk.Label(resumo,textvariable=self.resultado_geral,bg='#f4f7fa',fg=AZUL,
                 font=('Segoe UI',11,'bold'),justify='left',wraplength=900).pack(anchor='w',padx=15,pady=(0,12))
        tempos=tk.Frame(d,bg='#ffffff',highlightbackground='#d1dde8',highlightthickness=1)
        tempos.pack(fill='x',pady=(0,12))
        tk.Label(tempos,text='TEMPO DE EXECUÇÃO',bg='#ffffff',fg='#506c83',
                 font=('Segoe UI',9,'bold')).pack(anchor='w',padx=15,pady=(12,4))
        tk.Label(tempos,textvariable=self.resultado_tempos,bg='#ffffff',fg='#315267',
                 font=('Segoe UI',11),justify='left',wraplength=900).pack(anchor='w',padx=15,pady=(0,12))
        arquivos=tk.Frame(d,bg='#ffffff',highlightbackground='#d1dde8',highlightthickness=1)
        arquivos.pack(fill='x')
        tk.Label(arquivos,text='ARQUIVOS GERADOS',bg='#ffffff',fg='#506c83',
                 font=('Segoe UI',9,'bold')).pack(anchor='w',padx=15,pady=(12,4))
        tk.Label(arquivos,textvariable=self.resultado_arquivo_log,bg='#ffffff',fg=AZUL,
                 font=('Segoe UI',10),justify='left',wraplength=900).pack(anchor='w',padx=15,pady=(0,12))
        ttk.Label(d,text='Dados coletados automaticamente não constituem aprovação ou atesto. '
                  'Ocorrências e divergências continuam sob análise do fiscal.',wraplength=930).pack(anchor='w',pady=(15,0))
        rodape=ttk.Frame(corpo);rodape.pack(side='bottom',fill='x',pady=(10,0))
        ttk.Label(rodape,text=f'v{APP_VERSION} · Atesto é decisão do fiscal.',
                  foreground='#4c6375').pack(side='left',padx=(0,10))
        ttk.Label(rodape,textvariable=self.status,wraplength=700).pack(side='left',fill='x',expand=True)
        self.btn_encerrar=ttk.Button(rodape,text='Encerrar',command=self.encerrar)
        self.btn_encerrar.pack(side='right')
        self.btn_proxima=ttk.Button(rodape,text='Próxima etapa  →',
                                    command=self._proxima_etapa, state='disabled')
        self.btn_proxima.pack(side='right',padx=(0,10))
        # Reservar espaço ao rodapé ANTES do notebook expansível; do contrário,
        # em telas menores a tabela consome o espaço dos botões.
        self.abas.pack_forget()
        self.abas.pack(fill='both',expand=True)
        # Ações têm prioridade na reserva de largura: mensagens longas não
        # devem comprimir 'Próxima etapa' até exibir somente uma letra.
        elementos_rodape=rodape.winfo_children()
        for elemento in elementos_rodape:
            elemento.pack_forget()
        self.btn_encerrar.pack(side='right')
        self.btn_proxima.pack(side='right',padx=(0,10))
        for elemento in elementos_rodape:
            if elemento not in (self.btn_proxima,self.btn_encerrar):
                elemento.pack(side='left',fill='x',expand=True)
        self.abas.bind('<<NotebookTabChanged>>',self._atualizar_avanco)

    def _atualizar_avanco(self, _evento=None):
        if not hasattr(self,'btn_proxima'): return
        atual=self.abas.index(self.abas.select())
        pronto = ((atual==0 and self.preparo_concluido and not self.carregando) or
                  (atual==1 and self.cadastro_concluido and not self.processando) or
                  (atual==2 and self.estatisticas.etapas['hospital'].concluida and not self.processando))
        self.btn_proxima.configure(state='normal' if pronto else 'disabled')
        if atual>=3:
            self.btn_proxima.pack_forget()
        elif not self.btn_proxima.winfo_manager():
            self.btn_proxima.pack(side='right',padx=(0,10),before=self.btn_encerrar)

    def _proxima_etapa(self):
        atual=self.abas.index(self.abas.select())
        if atual==0 and self.preparo_concluido and not self.carregando:
            self.abas.select(1)
        elif atual==1 and self.cadastro_concluido and not self.processando:
            self.abas.select(2)
        elif atual==2 and self.estatisticas.etapas['hospital'].concluida and not self.processando:
            self.abas.select(3)
        self._atualizar_avanco()

    def _linha_visual(self, r, com_cns=False):
        dados=(r.aba,r.linha,r.aih,r.nome,r.cpf)
        if com_cns: dados+=(r.cns,)
        return dados+(rotulo_situacao(r.situacao),)

    def _atualizar_linha_visual(self, indice, dados, com_cns=False):
        tabela=self.tabela_cns if com_cns else self.tabela
        iid=str(indice)
        if tabela.exists(iid):
            tabela.item(iid,values=dados)
        else:
            tabela.insert('','end',iid=iid,values=dados)

    def _linha_hospital(self, r):
        # Somente o código de solicitação comprovado na ficha, nunca a AIH.
        estado = r.consulta_hospitalar
        referencia = r.solicitacao if r.solicitacao else '—'
        ficha_confirmada=estado in ('FICHA_CONFERIDA','PROCEDIMENTO_DIVERGENTE')
        return (r.aih, r.nome, r.cns,
                (r.carater or '—') if ficha_confirmada else '—',
                (r.procedimento_sisreg or r.comparacao_anterior or '—') if ficha_confirmada else '—',
                referencia if ficha_confirmada else '—',
                rotulo_situacao(r.situacao) if estado else 'Aguardando consulta')

    def _atualizar_linha_hospital(self, indice):
        iid=str(indice)
        dados=self._linha_hospital(self.sessao.registros[indice])
        if self.tabela_hospital.exists(iid):
            self.tabela_hospital.item(iid,values=dados)
        else:
            self.tabela_hospital.insert('', 'end', iid=iid,values=dados)

    def _escolher_xlsx(self):
        arq=filedialog.askopenfilename(title='Planilha-padrão',filetypes=[('Excel','*.xlsx')])
        if arq:
            if self.carregando or self.processando:
                return
            self._invalidar_preparo()
            self.arquivo_planilha=Path(arq)
            # Só temporários com prefixo exclusivo e idade >=48h. Nunca originais.
            try:
                analises, _logs = pastas_de_saida()
                limpeza_temporarios(analises)
            except OSError:
                self.status.set('Não foi possível criar Análises/Logs junto do executável. Verifique permissões da TI.')
            self.lbl_xlsx.configure(text=self.arquivo_planilha.name)
    def _escolher_pdf(self):
        arq=filedialog.askopenfilename(title='Espelho de AIH',filetypes=[('PDF','*.pdf')])
        if arq:
            if self.carregando or self.processando:
                return
            self._invalidar_preparo()
            self.arquivo_pdf=Path(arq)
            self.lbl_pdf.configure(text=self.arquivo_pdf.name)

    def _invalidar_preparo(self):
        if self.carregando or self.processando:
            return
        self.preparo_concluido=False
        self.cadastro_concluido=False
        self.abas.tab(1,state='disabled')
        self.abas.tab(2,state='disabled')
        self.abas.tab(3,state='disabled')
        self.cartao_resultado.pack_forget()
        self.atividade_preparo.set('Arquivos alterados: execute a conferência novamente.')

    def _preparar(self):
        if self.carregando or self.processando:return
        if not self.arquivo_planilha:
            self.status.set('Selecione o XLSX hospitalar.');return
        self.preparo_concluido=False;self.cadastro_concluido=False
        self.abas.tab(1,state='disabled');self.abas.tab(2,state='disabled');self.abas.tab(3,state='disabled')
        self.estatisticas=Estatisticas()
        self.consultas_acumuladas=0
        self.inicio_ciclo=time.perf_counter()
        self.relatorio_finalizado=False
        self.cartao_resultado.pack_forget()
        self.carregando=True;self.inicio_preparo=time.perf_counter();self._atualizar_relogio();self.btn_preparar.configure(state='disabled')
        self.atividade_preparo.set('Lendo planilha, indexando PDF e criando backup...')
        self.status.set('Preparação em andamento; a fonte recebida não será modificada.')
        try:
            if self.historico and not self.historico.termino:
                self.historico.encerrar('INTERROMPIDA')
            _analises, logs = pastas_de_saida()
            self.historico=HistoricoExecucao(pasta=logs)
            self.historico.fonte(self.arquivo_planilha, tipo='xlsx')
            if self.arquivo_pdf:
                self.historico.fonte(self.arquivo_pdf, tipo='pdf')
        except OSError:
            # Uma indisponibilidade de histórico não deve mascarar a execução.
            self.historico=None
            self.status.set('Histórico local indisponível. Avise a TI antes de uso oficial.')
        def tarefa():
            try:
                tempos={}
                t0=time.perf_counter()
                sessao=SessaoPlanilha()
                sessao.carregar(self.arquivo_planilha)
                # Detectar layout legado antes da indexação cara do PDF.
                sessao.validar_layout_para_saida()
                tempos['planilha']=time.perf_counter()-t0
                pendentes_pdf=[i for i,r in enumerate(sessao.registros) if not r.cpf]
                self.eventos.put(('preparo_fase', (f'Planilha lida. {len(pendentes_pdf)} CPFs ainda precisam de pesquisa no espelho.',)))
                # Uma tabela provisória aparece imediatamente; nenhum widget Tk
                # é acessado pela thread de processamento.
                self.eventos.put(('preparo_inicio', [
                    (i, self._linha_visual(sessao.registros[i])) for i in pendentes_pdf]))
                informacao='PDF não informado.'
                if self.arquivo_pdf and pendentes_pdf:
                    t0=time.perf_counter()
                    ix,avisos=ler_espelhos_pdf(self.arquivo_pdf)
                    tempos['indexacao_pdf']=time.perf_counter()-t0
                    self.eventos.put(('preparo_fase', (f'PDF indexado em {self._duracao(tempos["indexacao_pdf"])}. Cruzando as AIHs...',)))
                    t0=time.perf_counter()
                    lote=[]
                    def ao_complementar(indice, registro, total):
                        if registro.cpf_origem:
                            return
                        lote.append((indice-1, self._linha_visual(registro)))
                        if len(lote) >= 8 or indice == total:
                            self.eventos.put(('preparo_linhas', (lote[:], min(indice,len(pendentes_pdf)),len(pendentes_pdf))))
                            lote.clear()
                    sessao.complementar_pdf(ix,self.arquivo_pdf,progresso=ao_complementar)
                    tempos['cruzamento']=time.perf_counter()-t0
                    informacao=f'{len(ix)} AIHs indexadas no espelho para complementar CPFs ausentes.'
                    if avisos: informacao+=' Estrutura do PDF requer revisão.'
                elif self.arquivo_pdf:
                    informacao='Todos os CPFs já estavam preenchidos; PDF não reprocessado.'
                self.eventos.put(('preparo_fase', ('Cruzamento finalizado. Gravando a planilha de trabalho...',)))
                t0=time.perf_counter()
                analises, _logs = pastas_de_saida()
                trabalho=sessao.preparar_copia_de_trabalho(diretorio_saida=analises)
                gravacao=sessao.salvar_na_planilha(motivo='pdf')
                tempos['gravacao']=time.perf_counter()-t0
                self.eventos.put(('historico_preparacao', len(sessao.registros)))
                self.eventos.put(('preparado',(sessao,informacao,gravacao,time.perf_counter()-self.inicio_preparo,tempos,len(pendentes_pdf))))
            except Exception as e:
                # Não registrar str(e), paths ou valores do XLSX/PDF.
                etapa='salvamento' if 'trabalho' in locals() else 'preparacao'
                descartada = False
                if 'sessao' in locals():
                    try: descartada=sessao.descartar_copia_nao_gravada()
                    except OSError: pass
                self.eventos.put(('erro_preparo',
                    (type(e).__name__,etapa,time.perf_counter()-self.inicio_preparo,
                     len(sessao.registros) if 'sessao' in locals() else 0,descartada)))
        threading.Thread(target=tarefa,daemon=True).start()

    def _atualizar_relogio(self):
        if not self.carregando or self.inicio_preparo is None:return
        decorrido=int(time.perf_counter()-self.inicio_preparo)
        self.cronometro.set(f'Tempo: {decorrido//60:02d}:{decorrido%60:02d}')
        self.root.after(250,self._atualizar_relogio)

    @staticmethod
    def _duracao(segundos):
        segundos=max(0,int(segundos))
        h, resto=divmod(segundos,3600);m,s=divmod(resto,60)
        return f'{h}h {m}min {s}s' if h else f'{m}min {s}s'

    def _atualizar_tabela(self):
        for tabela in (self.tabela,self.tabela_cns):
            itens=tabela.get_children()
            if itens:tabela.delete(*itens)
        for i,r in enumerate(self.sessao.registros):
            if not r.cpf_origem:
                self._atualizar_linha_visual(i,self._linha_visual(r))
            if not r.cns_origem:
                self._atualizar_linha_visual(i,self._linha_visual(r,com_cns=True),True)

    def _cns_totais(self):
        """Progresso acumulado do XLSX, independente do lote e de novo login."""
        elegiveis=sum(bool(r.cpf) for r in self.sessao.registros)
        identificados=sum(cns_formato(r.cns) for r in self.sessao.registros)
        return identificados,elegiveis

    def _exibir_verificacao(self, causa):
        """Executada somente na thread Tk; sem CAPTCHA em log nem dados clínicos."""
        self.intervencao_pendente=True
        self.browser_ready=False
        self.aviso_verificacao.pack(anchor='w',pady=(6,3))
        self.btn_verificacao.pack(anchor='w',pady=(0,8))
        self.btn_verificacao.configure(state='normal')
        self.btn_lote.configure(state='disabled')
        self.btn_hospital.configure(state='disabled')
        self.status.set('Aguardando verificação humana no navegador. Dados já coletados preservados.')
        self._evento_seguro('VERIFICACAO_HUMANA_EXIGIDA','geral')
        self.estatisticas.diagnosticar('VERIFICACAO_HUMANA_EXIGIDA','PENDENCIA',categoria='INTERVENCAO_HUMANA')
        # Janela não modal: permanece acessível sem bloquear Chrome/Edge.
        # O botão de confirmação fica DENTRO do aviso, não oculto atrás da tabela.
        if self.janela_verificacao is None or not self.janela_verificacao.winfo_exists():
            janela=tk.Toplevel(self.root)
            janela.title('RPA SISREG — atendimento necessário')
            janela.geometry('545x225')
            janela.resizable(False,False)
            janela.transient(self.root)
            area=ttk.Frame(janela,padding=18);area.pack(fill='both',expand=True)
            ttk.Label(area,text='SISREG: verificação ou reconexão necessária',
                      font=('Segoe UI',12,'bold'),wraplength=500).pack(anchor='w',pady=(0,9))
            ttk.Label(area,text='As consultas estão pausadas e os dados já coletados foram preservados. '
                      'Conclua a verificação ou regularize a conexão no navegador oficial. '
                      'Depois clique no botão abaixo.',wraplength=490,justify='left').pack(anchor='w')
            botoes=ttk.Frame(area);botoes.pack(side='bottom',fill='x',pady=(16,0))
            self.btn_modal_confirmar=ttk.Button(botoes,text='Verificar sessão e retomar',
                                               command=self._confirmar_verificacao)
            self.btn_modal_confirmar.pack(side='left')
            ttk.Button(botoes,text='Continuar aguardando',command=janela.withdraw).pack(side='right')
            janela.protocol('WM_DELETE_WINDOW',janela.withdraw)
            self.janela_verificacao=janela
        else:
            self.janela_verificacao.deiconify()
            self.btn_modal_confirmar.configure(state='normal')
        self.janela_verificacao.lift()

    def _ocultar_verificacao(self):
        self.intervencao_pendente=False
        self.aviso_verificacao.pack_forget()
        self.btn_verificacao.pack_forget()
        if self.janela_verificacao is not None and self.janela_verificacao.winfo_exists():
            self.janela_verificacao.withdraw()

    def _confirmar_verificacao(self):
        if not self.intervencao_pendente:
            return
        self.btn_verificacao.configure(state='disabled')
        if self.janela_verificacao is not None and self.janela_verificacao.winfo_exists():
            self.btn_modal_confirmar.configure(state='disabled')
            self.janela_verificacao.withdraw()
        self.status.set('Verificando se a sessão SISREG já está disponível...')
        self._evento_seguro('VERIFICACAO_CONFIRMADA_OPERADOR','geral')
        self.aguardar_humano.confirmar()

    def _esperar_intervencao(self, contexto, origem: str) -> bool:
        """Worker: mantém navegador aberto por tempo indeterminado.

        O Playwright só é acessado pela thread do navegador. Nenhum polling
        de autenticação enquanto a pessoa resolve o desafio.
        """
        self.aguardar_humano.confirmacao.clear()
        self.eventos.put(('verificacao_pendente',origem))
        while self.aguardar_humano.esperar(self.parar,self.reiniciar_navegador):
            try:
                if desafio_visivel(contexto):
                    confirmado=False
                else:
                    paginas=[p for p in contexto.pages if not p.is_closed() and endereco_oficial(p.url)]
                    confirmado=any(autenticao_ativa(pg,timeout=2200) for pg in paginas)
            except Exception:
                confirmado=False
            if confirmado:
                if origem != 'login':
                    self.eventos.put(('sessao_recuperada',origem))
                return True
            self.eventos.put(('verificacao_incompleta',origem))
        return False

    def _iniciar_login(self):
        if not self.preparo_concluido or self.carregando:
            self.status.set('Conclua a etapa 1 antes de acessar o SISREG.');return
        if self.browser_ready:
            self.status.set('Uma sessão SISREG autenticada já está ativa.');return
        u=self.usuario.get().strip();s=self.senha.get()
        if not u or not s:
            self.status.set('Preencha usuário e senha para abrir o SISREG.');return
        if self.thread_navegador and self.thread_navegador.is_alive():
            # Na falha anterior, a thread pode ainda estar liberando o Chrome.
            # Agendar nova tentativa na própria GUI, sem guardar senha em arquivo.
            self.login_pendente=True
            self.reiniciar_navegador.set()
            self.status.set('Encerrando sessão anterior para novo login; a planilha será mantida...')
            return
        self.login_pendente=False
        self.reiniciar_navegador.clear()
        self._ocultar_verificacao()
        canal='chrome' if self.navegador.get()=='Google Chrome' else 'msedge'
        self.usuario.set('');self.senha.set('');self.parar.clear()
        self.browser_ready=False;self.cadastro_concluido=False
        self.thread_navegador=threading.Thread(target=self._navegador_worker,args=(u,s,canal),daemon=True)
        self.thread_navegador.start();self.status.set('Abrindo nova sessão SISREG...')

    def _retomar_login_pendente(self):
        if self.parar.is_set() or not self.preparo_concluido:
            return
        if self.thread_navegador and self.thread_navegador.is_alive():
            self.root.after(250, self._retomar_login_pendente)
            return
        self._iniciar_login()

    def _navegador_worker(self,usuario,senha,canal):
        browser=None
        try:
            with sync_playwright() as p:
                browser=p.chromium.launch(channel=canal,headless=False)
                contexto=browser.new_context(accept_downloads=False)
                pagina=contexto.new_page()
                pagina_principal=pagina
                try:
                    pagina.goto(URL_SISREG,wait_until='domcontentloaded',timeout=45000)
                    submeter_login(pagina,usuario,senha)
                    self.eventos.put(('login_enviado',None))
                    # Não deixar o timeout de autenticação fechar um CAPTCHA.
                    # Verificar o menu brevemente; se houver desafio, não sondar
                    # novamente até confirmação explícita da operadora.
                    menu_ok=False
                    inicio_espera=time.monotonic()
                    while time.monotonic()-inicio_espera<12 and not self.parar.is_set():
                        if desafio_visivel(contexto):
                            break
                        if autenticao_ativa(pagina,timeout=1600):
                            menu_ok=True
                            break
                        self.parar.wait(0.35)
                    if not menu_ok:
                        menu_ok=self._esperar_intervencao(contexto,'login')
                    if not menu_ok:
                        return
                    self.eventos.put(('autenticado',None))
                except Exception:
                    self.eventos.put(('erro_login','Login ou acesso indisponível. Tente novamente sem refazer a etapa 1.'))
                    return
                finally:
                    usuario='';senha=''
                while not self.parar.is_set() and not self.reiniciar_navegador.is_set():
                    try: cmd,payload=self.comandos.get(timeout=0.2)
                    except queue.Empty:
                        # Se a operadora fechou o Chrome, liberar novo login na
                        # mesma janela do RPA (sem reiniciar a etapa 1).
                        try:
                            if (not browser.is_connected() or
                                    not any(not pg.is_closed() for pg in contexto.pages)):
                                return
                        except Exception:
                            return
                        continue
                    if cmd == 'hospital':
                        indices=payload
                        self.eventos.put(('hospital_iniciado',len(indices)))
                        erros_seguidos=0
                        hospital_suspenso=False
                        pausa_tecnica=False
                        for j,idx in enumerate(indices,1):
                            if self.parar.is_set():break
                            while self.pausa.is_set() and not self.parar.wait(.25):pass
                            if self.parar.is_set():break
                            r=self.sessao.registros[idx]
                            inicio=time.perf_counter()
                            try:
                                if desafio_visivel(contexto):
                                    raise NavegacaoInesperada('VERIFICACAO_HUMANA_EXIGIDA')
                                validas=[pg for pg in contexto.pages if not pg.is_closed() and endereco_oficial(pg.url)]
                                if not validas:raise NavegacaoInesperada('Sessão SISREG encerrada.')
                                # Não usar popup de ficha para pesquisar o próximo CNS.
                                pagina=(pagina_principal
                                        if not pagina_principal.is_closed() and endereco_oficial(pagina_principal.url)
                                        else validas[0])
                                def observador(acao,estado,tempo_fase,categoria):
                                    self.eventos.put(('diagnostico_tecnico',
                                        (acao,estado,j,tempo_fase,categoria)))
                                resultado=consultar_solicitacao_hospitalar(
                                    pagina,r.cns,r.aih,r.procedimento,observador=observador,
                                    cancelar=self.parar.is_set)
                                # Ficha incompleta conta como erro técnico, mesmo
                                # quando a função retorna sem exceção.
                                if resultado.situacao in (
                                        'FICHA_NAO_ABERTA', 'AIH_NAO_COMPROVADA_FICHA',
                                        'CAMPOS_FICHA_NAO_CONFIRMADOS',
                                        'CAMPOS_FICHA_INCOMPLETOS'):
                                    erros_seguidos+=1
                                else:
                                    erros_seguidos=0
                            except Exception as exc:
                                # Erro de gateway é indisponibilidade do serviço,
                                # não ausência da AIH. Não emitir nova pesquisa.
                                if servidor_indisponivel(contexto):
                                    # Upstream/502/503 não é prova de sessão expirada.
                                    # Sem reconexão nem CAPTCHA artificial; pausa a fila
                                    # para evitar novas requisições a um servidor instável.
                                    pausa_tecnica=True
                                    self.eventos.put(('hospital_pausa_tecnica',
                                        'O SISREG apresentou instabilidade. Dados salvos. '
                                        'Quando normalizar, clique em Pesquisar solicitações hospitalares para continuar.'))
                                    break
                                erros_seguidos+=1
                                resultado=ResultadoHospital('FALHA_NAVEGACAO',
                                              'Consulta não finalizada. Revisar a tela do SISREG.')
                                self.eventos.put(('diagnostico_tecnico',('FICHA_HOSPITALAR',
                                   'ERRO',j,time.perf_counter()-inicio,categoria_excecao(type(exc).__name__))))
                            if self.parar.is_set():
                                break  # Não criar pendência falsa ao cancelar a consulta.
                            if desafio_visivel(contexto):
                                hospital_suspenso=True
                                self.eventos.put(('hospital_alerta',
                                    'Acesso do SISREG indisponível ou requer verificação. Consulte o navegador e aguarde a recuperação.'))
                                break
                            falha = resultado.situacao not in ('FICHA_CONFERIDA','PROCEDIMENTO_DIVERGENTE')
                            categoria = ({'PROCEDIMENTO_DIVERGENTE':'PROCEDIMENTO_DIVERGENTE',
                                'FICHA_NAO_ABERTA':'FICHA_NAO_ABERTA',
                                'AIH_NAO_COMPROVADA_FICHA':'AIH_NAO_CONFIRMADA',
                                'CAMPOS_FICHA_INCOMPLETOS':'CAMPOS_FICHA_INCOMPLETOS',
                                'CAMPOS_FICHA_NAO_CONFIRMADOS':'SELETOR_NAO_ENCONTRADO',
                                'PROCEDIMENTO_NAO_CONFIRMADO':'CAMPOS_FICHA_INCOMPLETOS',
                                'FALHA_NAVEGACAO':'FALHA_NAVEGACAO'}).get(resultado.situacao,
                                'ERRO_NAO_CLASSIFICADO' if falha else 'NENHUM')
                            self.eventos.put(('diagnostico_tecnico',('FICHA_HOSPITALAR',
                                'PENDENCIA' if falha else 'OK',j,time.perf_counter()-inicio,categoria)))
                            self.eventos.put(('hospital_item',(idx,resultado,time.perf_counter()-inicio,j,len(indices))))
                            if erros_seguidos>=3:
                                # Um seletor fora do lugar ou paginação lenta não
                                # comprova necessidade de reautenticação. Só abre
                                # o diálogo humano com evidência de sessão ausente.
                                try:
                                    paginas_ativas=[pg for pg in contexto.pages
                                        if not pg.is_closed() and endereco_oficial(pg.url)]
                                    autenticada=any(autenticao_ativa(pg,timeout=2500)
                                        for pg in paginas_ativas)
                                except Exception:
                                    autenticada=False
                                if not autenticada:
                                    hospital_suspenso=True
                                    self.eventos.put(('hospital_alerta',
                                        'A sessão não pôde ser confirmada. Verifique o SISREG no navegador.'))
                                else:
                                    pausa_tecnica=True
                                    self.eventos.put(('hospital_pausa_tecnica',
                                        'Três consultas tiveram falhas técnicas. A sessão continua ativa; '
                                        'o processamento foi pausado para evitar resultados incorretos. '
                                        'Você pode retomar a etapa hospitalar pelo botão de pesquisa.'))
                                break
                            self.parar.wait(1.8)
                        # Não declarar fim nem finalizar relatório enquanto houver
                        # CAPTCHA, sessão comprometida ou fila ainda incompleta.
                        if hospital_suspenso and not self.parar.is_set():
                            self.eventos.put(('hospital_suspenso',len(indices)))
                            if not self._esperar_intervencao(contexto,'hospital'):
                                return
                        elif pausa_tecnica and not self.parar.is_set():
                            # A thread permanece aberta para retomada pelo botão.
                            # Não marcar como concluído e NÃO pedir login/captcha.
                            self.eventos.put(('hospital_pausa',len(indices)))
                        elif not self.parar.is_set():
                            self.eventos.put(('hospital_fim',len(indices)))
                        else:
                            self.eventos.put(('hospital_suspenso',len(indices)))
                        continue
                    if cmd!='lote':continue
                    indices=payload
                    self.eventos.put(('lote_iniciado',len(indices)))
                    saude=SaudeLote()
                    provisoria=[]  # Até confirmar que a sessão continua saudável.
                    processados=0
                    def confirmar_uma(item):
                        nonlocal processados
                        indice,numero,razao,ordinal,duracao,tecnico=item
                        self.eventos.put(('diagnostico_tecnico',('CADASTRO_CPF',
                            'OK' if numero else 'PENDENCIA',ordinal,duracao,
                            'NENHUM' if numero else ('FALHA_NAVEGACAO' if tecnico
                            else 'IDENTIDADE_NAO_CONFIRMADA'))))
                        self.eventos.put(('lote_item',(indice,numero,razao,ordinal,len(indices))))
                        processados+=1
                    suspenso=False
                    for j,idx in enumerate(indices,1):
                        if self.parar.is_set():break
                        while self.pausa.is_set() and not self.parar.wait(0.25):pass
                        if self.parar.is_set():break
                        r=self.sessao.registros[idx]
                        inicio_item=time.perf_counter()
                        identificador=r.cpf
                        cns,motivo=None,'FALHA_DE_NAVEGACAO_OU_TEMPO'
                        erro_tecnico=False
                        if desafio_visivel(contexto):
                            suspenso=True
                            self.eventos.put(('lote_alerta',
                                'O SISREG solicitou verificação humana. Consultas pausadas.'))
                            break
                        # No máximo duas tentativas apenas para falhas de navegação.
                        # Não repetir automaticamente uma identidade divergente.
                        for tentativa in (1,2):
                            if self.parar.is_set():break
                            try:
                                validas=[pg for pg in contexto.pages if not pg.is_closed() and endereco_oficial(pg.url)]
                                if not validas:
                                    raise NavegacaoInesperada('Sessão SISREG encerrada.')
                                pagina=validas[-1]
                                # Uma verificação periódica evita consultar centenas
                                # de registros numa página que já perdeu a sessão.
                                if (j==1 or j%20==0 or tentativa>1) and not autenticao_ativa(pagina,timeout=2500):
                                    raise NavegacaoInesperada('Menu autenticado indisponível.')
                                consultar_cadastro(pagina,identificador)
                                cns,motivo=ler_cadastro_contexto(contexto,pagina,r.nome,identificador,espera=7500)
                                erro_tecnico=False
                                break
                            except Exception as exc:
                                erro_tecnico=True
                                self.eventos.put(('diagnostico_navegacao', type(exc).__name__))
                                if desafio_visivel(contexto):
                                    break  # Não repetir pesquisa diante de CAPTCHA.
                                if tentativa==1 and not self.parar.wait(2.0):
                                    continue
                        if self.parar.is_set():break
                        if desafio_visivel(contexto):
                            suspenso=True
                            self.eventos.put(('lote_alerta',
                                'O SISREG solicitou verificação humana. Nenhum dado incerto será salvo.'))
                            break
                        decisao=saude.registrar(cns,erro_tecnico=erro_tecnico)
                        if decisao.startswith('SUSPENDER_'):
                            motivo_suspensao = ('Falhas de navegação consecutivas.' if erro_tecnico
                                else 'Vários resultados consecutivos sem identidade confirmada.')
                            self.eventos.put(('diagnostico_tecnico',('SESSAO_SUSPENSA','PENDENCIA',j,
                                time.perf_counter()-inicio_item,'FALHA_NAVEGACAO' if erro_tecnico else 'IDENTIDADE_NAO_CONFIRMADA')))
                            self.eventos.put(('lote_alerta',motivo_suspensao+
                                ' Pesquisas suspensas; confira a sessão e faça novo login para retomar.'))
                            suspenso=True
                            break  # Não marca este registro como ausência de paciente.
                        item=(idx,cns,motivo,j,time.perf_counter()-inicio_item,erro_tecnico)
                        if cns:
                            # A próxima consulta correta confirma a navegação; só
                            # então consolidar os casos imediatamente anteriores.
                            for anterior in provisoria: confirmar_uma(anterior)
                            provisoria.clear()
                            confirmar_uma(item)
                        else:
                            provisoria.append(item)
                        # Intervalo deliberado: respeitar a operação do SISREG.
                        self.parar.wait(1.8)
                    if provisoria and not suspenso and not self.parar.is_set():
                        try:
                            validas=[pg for pg in contexto.pages if not pg.is_closed() and endereco_oficial(pg.url)]
                            sessao_ok=bool(validas and autenticao_ativa(validas[-1],timeout=2500))
                        except Exception:
                            sessao_ok=False
                        if sessao_ok:
                            for anterior in provisoria: confirmar_uma(anterior)
                        else:
                            suspenso=True
                            self.eventos.put(('lote_alerta',
                                'Não foi possível confirmar a sessão após resultados inconclusivos. '
                                'Faça novo login para retomar sem perder os CNS anteriores.'))
                    self.eventos.put(('lote_fim',(processados,len(indices))))
                    if suspenso and not self.parar.is_set():
                        # O navegador permanece disponível para CAPTCHA ou login
                        # manual. Retomada somente após confirmação da operadora.
                        if not self._esperar_intervencao(contexto,'cadastro'):
                            return
        except Exception:
            self.eventos.put(('erro_login','Não foi possível iniciar o navegador autorizado.'))
        finally:
            if browser:
                try: browser.close()
                except Exception:pass
            self.eventos.put(('navegador_parou',None))

    def _iniciar_lote(self):
        if self.processando:
            self.status.set('Já há um lote em execução.');return
        if not self.preparo_concluido or not self.sessao.origem:
            self.status.set('Conclua a conferência da etapa 1 primeiro.');return
        if not self.thread_navegador or not self.thread_navegador.is_alive() or not self.browser_ready:
            self.status.set('Aguarde o reconhecimento do login pelo SISREG.');return
        from aih_extract import cpf_valido
        selecionados,self.revisao_anterior=selecionar_cadastros(self.sessao.registros)
        if not selecionados:
            identificados,elegiveis=self._cns_totais()
            self.resumo_cadastro.set('Cadastro e CNS · '+
                resumo_progresso(elegiveis,identificados,0,0).resumo()+
                f' · {elegiveis-identificados} ainda sem CNS (inclui revisões humanas)')
            self.status.set('Nenhum CPF elegível pendente. Etapa 2 concluída.')
            self.estatisticas.registrar_total('cadastro',0)
            self.estatisticas.concluir('cadastro',0.0,consultados=0,encontrados=0)
            self.cadastro_concluido=True
            self.abas.tab(2,state='normal')
            self._atualizar_avanco()
            self.status.set('CNS existentes preservados; iniciando consultas hospitalares automaticamente.')
            self.root.after(200, self._iniciar_hospital)
            return
        self.inicio_cadastro=time.perf_counter()
        self.consultas_cadastro=0
        self.estatisticas.registrar_total('cadastro',len(selecionados))
        identificados,elegiveis=self._cns_totais()
        self.cns_aproveitados=identificados
        self.cns_previstos=len(selecionados)
        self.resumo_cadastro.set(f'Cadastro e CNS · '+
            resumo_progresso(elegiveis,identificados,len(selecionados),0).resumo()+
            f' · revisão humana: {self.revisao_anterior}')
        self.tempo_cadastro.set(f'Iniciando · manual projetado: {self._duracao(len(selecionados)*10)} (10s/consulta).')
        self.tipo_lote='cadastro';self.processando=True;self.persistencia_falhou=False;self.navegacao_falhou=False;self.pausa.clear();self.parar.clear()
        self.cadastro_concluido=False
        self.abas.tab(2,state='disabled')
        self.dados_atuais={'cpf':0,'cns':0,'pendentes':0,'falhas':0,'total':len(selecionados)}
        self.motivos_cadastro={}
        self.barra.configure(value=0)
        self.btn_lote.configure(state='disabled')
        self.comandos.put(('lote',selecionados))
        self.status.set(f'Lote iniciado: {len(selecionados)} cadastros pendentes; {self.revisao_anterior} para revisão humana. A etapa hospitalar iniciará automaticamente ao concluir.')
    def _iniciar_hospital(self):
        if self.processando:
            self.status.set('Outro lote em execução; aguarde sua conclusão.');return
        if not self.preparo_concluido or not self.cadastro_concluido or not self.thread_navegador or not self.thread_navegador.is_alive() or not self.browser_ready:
            self.status.set('Aguarde o fim das etapas 1 e 2 antes da consulta hospitalar.');return
        candidatos=[i for i,r in enumerate(self.sessao.registros) if candidato_hospitalar(r)]
        self.hospital_universo=len(self.sessao.registros)
        self.hospital_aproveitados=sum(ficha_hospitalar_completa(r) for r in self.sessao.registros)
        self.hospital_previstos=len(candidatos)
        if not candidatos:
            self.status.set('Sem solicitações hospitalares elegíveis para pesquisa. Resultado registrado sem consultas adicionais.')
            self.estatisticas.registrar_total('hospital',0)
            self.estatisticas.concluir('hospital',0.0,consultados=0,encontrados=0)
            self._finalizar_relatorio()
            return
        self.inicio_hospital=time.perf_counter()
        self.tentativas_hospital=0;self.acertos_hospital=0;self.falhas_hospital=0
        self.estatisticas.registrar_total('hospital',len(candidatos))
        self.resumo_hospital.set('Solicitações hospitalares · '+
            resumo_progresso(self.hospital_universo,self.hospital_aproveitados,len(candidatos),0).resumo())
        self.tempo_hospital.set(f'Iniciando · manual projetado: {self._duracao(len(candidatos)*10)} (10s/consulta).')
        for i in candidatos: self._atualizar_linha_hospital(i)
        self.tipo_lote='hospital';self.processando=True
        self.persistencia_falhou=False;self.navegacao_falhou=False
        self.parar.clear();self.pausa.clear()
        self.btn_hospital.configure(state='disabled');self.barra_hospital.configure(value=0)
        self.comandos.put(('hospital',candidatos))
        self.status.set(f'Etapa 3 iniciada: {len(candidatos)} AIHs para consulta, sem escolher posições fixas na tabela.')

    def _pausar(self):
        if not self.processando:return
        if self.pausa.is_set():
            self.pausa.clear();self.btn_pausa.configure(text='Pausar')
        else:
            self.pausa.set();self.btn_pausa.configure(text='Retomar')
    def _interromper(self):
        # Interrompe o processo e encerra o navegador, evitando pesquisas sem supervisão.
        self.parar.set();self.pausa.clear();self.aguardar_humano.confirmar()
        self._evento_seguro('INTERRUPCAO','geral')
        self.estatisticas.diagnosticar('INTERRUPCAO','INTERRUPCAO',categoria='INTERRUPCAO_SOLICITADA')
        self.status.set('Solicitada interrupção; os resultados recebidos serão salvos.')

    def _salvar_checkpoint(self):
        try:
            saida=self.sessao.salvar_na_planilha(motivo='lote_cns')
            return True
        except Exception as e:
            self.persistencia_falhou=True
            self.parar.set()
            self.pausa.clear()
            self.status.set('Não foi possível gravar a planilha de trabalho. Feche o Excel e tente novamente; a execução foi interrompida.')
            self._evento_seguro('FALHA_SALVAMENTO', 'geral')
            self.estatisticas.diagnosticar('SALVAMENTO_XLSX','ERRO',categoria='PERSISTENCIA_FALHOU')
            return False

    def _tentar_salvar(self):
        if self._salvar_checkpoint():
            self.persistencia_falhou=False
            self.status.set('Alterações salvas na planilha hospitalar.')

    def _ler_eventos(self):
        try:
            passos=0
            while passos < 3:
                evento,dado=self.eventos.get_nowait()
                passos+=1
                if evento=='diagnostico_tecnico':
                    acao,resultado,indice,segundos,categoria=dado
                    self.estatisticas.diagnosticar(acao,resultado,ordinal=indice,
                                                  segundos=segundos,categoria=categoria)
                elif evento=='preparo_fase':
                    self.atividade_preparo.set(dado[0])
                elif evento=='preparo_inicio':
                    itens=self.tabela.get_children()
                    if itens:self.tabela.delete(*itens)
                    for indice,linha in dado:
                        self._atualizar_linha_visual(indice,linha)
                    self.atividade_preparo.set(f'{len(dado)} registros sem CPF selecionados para análise.')
                elif evento=='preparo_linhas':
                    linhas,contador,total=dado
                    for indice,linha in linhas:
                        self._atualizar_linha_visual(indice,linha)
                    self.atividade_preparo.set(f'Conferindo documentos: {contador}/{total} registros...')
                elif evento=='preparado':
                    sessao,informacao,atualizacao,segundos,fases,previstos=dado
                    self.sessao=sessao
                    self._atualizar_tabela()
                    self.cronometro.set('Tempo: '+self._duracao(segundos))
                    manual=previstos*MANUAL_SEGUNDOS_POR_AIH
                    self.resultado_titulo.set(f'✓ Extração automática concluída — {len(sessao.registros)} AIHs em {self._duracao(segundos)}')
                    cpf_presentes=sum(bool(r.cpf) for r in sessao.registros)
                    total=len(sessao.registros)
                    cobertura=(100*cpf_presentes/total) if total else 0
                    ja_aproveitados=sum(bool(r.cpf_origem) for r in sessao.registros)
                    novos=sum(bool(r.cpf) and not r.cpf_origem for r in sessao.registros)
                    self.resultado_descritivo.set(
                        resumo_progresso(total,ja_aproveitados,previstos,novos).resumo()+f' · {informacao}')
                    self.resultado_tempo.set(
                        f'Manual estimado: {self._duracao(manual)} (15 s/AIH, hipótese fixa) · '
                        f'Diferença estimada: {self._duracao(max(0,manual-segundos))}.')
                    self.resultado_arquivo.set(
                        f'✓ Nova planilha criada: {sessao.origem.name} · Arquivo hospitalar original preservado.')
                    self.cartao_resultado.pack(fill='x',pady=(0,8),before=self.grade)
                    self.atividade_preparo.set('Concluído. Cópia de trabalho atualizada.')
                    for etapa,fase in (('PDF_INDEXACAO','indexacao_pdf'),
                                       ('CPF_CRUZAMENTO','cruzamento'),('SALVAMENTO_XLSX','gravacao')):
                        self.estatisticas.diagnosticar(etapa,'OK',segundos=fases.get(fase,0))
                    self.estatisticas.registrar_total('preparo',previstos)
                    self.estatisticas.concluir('preparo',segundos,consultados=previstos,
                        encontrados=novos,pendencias=previstos-novos,fases=fases)
                    self.preparo_concluido=True
                    self.abas.tab(1,state='normal')
                    self.status.set('Etapa 1: dados extraídos na cópia de trabalho. Agora pode acessar o SISREG.')
                    self.carregando=False;self.btn_preparar.configure(state='normal')
                    self._atualizar_avanco()
                elif evento=='erro_preparo':
                    tipo,etapa,segundos,total,descartada = dado
                    self.carregando=False;self.btn_preparar.configure(state='normal')
                    self.preparo_concluido=False
                    categoria=categoria_excecao(tipo)
                    if categoria == 'ERRO_NAO_CLASSIFICADO':
                        categoria='PREPARACAO_NAO_CONCLUIDA'
                    try:
                        self.estatisticas.concluir('preparo',segundos,consultados=total,
                            encontrados=0,pendencias=total,falhas=1,completa=False)
                        self.estatisticas.diagnosticar('SALVAMENTO_XLSX' if etapa=='salvamento' else 'PDF_INDEXACAO',
                            'ERRO',segundos=segundos,categoria=categoria)
                    except (ValueError,OSError):pass
                    self.atividade_preparo.set('Não foi possível concluir a preparação. O arquivo original foi preservado.')
                    self.status.set('Preparação interrompida: '+(
                        'modelo XLSX de versão diferente; revise ou atualize o arquivo.'
                        if categoria=='LAYOUT_XLSX_INCOMPATIVEL'
                        else 'falha técnica; consulte o TXT gerado na pasta da planilha.'))
                    self._evento_seguro('PREPARO_ERRO','preparo')
                    # Gerar um TXT mesmo quando nenhuma etapa foi concluída.
                    # A função sanitiza os campos, sem aceitar mensagens livres.
                    try:
                        self._registrar_falha_preparacao(segundos)
                    except (OSError,ValueError):
                        self.status.set('Falha na preparação; TXT indisponível. Acione a TI.')
                elif evento=='historico_preparacao':
                    if self.historico:
                        try:
                            self.historico.atualizar(registros=dado, preparados=dado)
                            self.historico.evento('PREPARO_OK', 'preparo')
                        except OSError:
                            self.status.set('Histórico local não pôde ser atualizado; avise a TI.')
                elif evento=='verificacao_pendente':
                    self._salvar_checkpoint() if self.preparo_concluido and self.sessao.origem else None
                    self._exibir_verificacao(dado)
                elif evento=='verificacao_incompleta':
                    self.btn_verificacao.configure(state='normal')
                    if self.janela_verificacao is not None and self.janela_verificacao.winfo_exists():
                        self.btn_modal_confirmar.configure(state='normal')
                        self.janela_verificacao.deiconify()
                    self.status.set('Acesso ainda indisponível. Continue a verificação no navegador e confirme novamente.')
                elif evento=='sessao_recuperada':
                    self._ocultar_verificacao()
                    self.browser_ready=True
                    self.navegacao_falhou=False
                    self._evento_seguro('SESSAO_RECUPERADA','geral')
                    self.estatisticas.diagnosticar('SESSAO_RECUPERADA','OK')
                    self.status.set('Sessão confirmada. Retomando apenas as consultas pendentes...')
                    if dado=='hospital':
                        self.root.after(250,self._iniciar_hospital)
                    else:
                        self.root.after(250,self._iniciar_lote)
                elif evento=='login_enviado':
                    self.estatisticas.diagnosticar('LOGIN_SUBMETIDO','OK')
                    self.status.set('Login enviado; aguardando o menu autenticado para iniciar o lote automaticamente.')
                elif evento=='autenticado':
                    self._ocultar_verificacao()
                    self.estatisticas.diagnosticar('MENU_AUTENTICADO','OK')
                    self.estatisticas.diagnosticar('SESSAO_HTTPS_OFICIAL','OK')
                    self.browser_ready=True
                    self.status.set('Acesso identificado. Retomando consultas elegíveis, preservando CNS já encontrados...')
                    self._iniciar_lote()
                elif evento=='hospital_iniciado':
                    self.progresso_hospital.set(f'Iniciando {dado} consultas hospitalares...')
                elif evento=='hospital_item':
                    idx,resultado,duracao,contador,total=dado
                    self.tentativas_hospital += 1
                    if resultado.situacao=='FALHA_NAVEGACAO': self.falhas_hospital+=1
                    reg=self.sessao.registros[idx]
                    self.sessao.registrar_hospital(reg,resultado,duracao)
                    if reg.situacao=='DADOS_COLETADOS_SEM_DIVERGENCIA': self.acertos_hospital+=1
                    self._evento_seguro('HOSPITAL_OK' if reg.situacao == 'DADOS_COLETADOS_SEM_DIVERGENCIA' else 'HOSPITAL_PENDENCIA', 'hospital', contador)
                    if resultado.situacao=='FALHA_NAVEGACAO':
                        self._evento_seguro('ERRO_TECNICO','hospital',contador)
                    if contador%15==0: self._salvar_checkpoint()
                    self._atualizar_linha_visual(idx,self._linha_visual(reg))
                    self._atualizar_linha_visual(idx,self._linha_visual(reg,com_cns=True),True)
                    self._atualizar_linha_hospital(idx)
                    fichas_completas=sum(r.consulta_hospitalar in ('FICHA_CONFERIDA','PROCEDIMENTO_DIVERGENTE')
                        for r in self.sessao.registros) - self.hospital_aproveitados
                    fichas_completas=max(0,min(self.hospital_previstos,fichas_completas))
                    self.resumo_hospital.set('Solicitações hospitalares · '+
                        resumo_progresso(self.hospital_universo,self.hospital_aproveitados,
                            self.hospital_previstos,fichas_completas).resumo()+
                        f' · sem divergência na sessão: {self.acertos_hospital}; pendências: {self.tentativas_hospital-self.acertos_hospital}')
                    self.tempo_hospital.set(
                        f'Tempo decorrido: {self._duracao(time.perf_counter()-self.inicio_hospital)} · Manual hipotético: {self._duracao(total*10)} (10s/AIH).')
                    self.barra_hospital.configure(value=100*contador/max(1,total))
                    self.progresso_hospital.set(f'{contador}/{total} consultadas · última: {rotulo_situacao(reg.situacao)} · '
                                               f'{self._duracao(duracao)} nesta AIH')
                elif evento=='hospital_pausa_tecnica':
                    self.status.set(str(dado))
                    self.estatisticas.diagnosticar('HOSPITAL_PAUSA_TECNICA','PENDENCIA',
                                                  categoria='FALHA_NAVEGACAO')
                elif evento=='hospital_pausa':
                    self.navegacao_falhou=True
                    self._salvar_checkpoint()
                    self.processando=False
                    self.btn_hospital.configure(state='normal')
                    self._resumir_historico()
                    self._atualizar_avanco()
                    # Retomada permitida com sessão ativa, sem modal de CAPTCHA.
                elif evento=='hospital_suspenso':
                    # Um lote pausado NÃO concluiu a auditoria. Salva o trabalho
                    # e aguarda a pessoa, mantendo a possibilidade de retomar.
                    self._salvar_checkpoint()
                    self.processando=False
                    self.navegacao_falhou=True
                    self.btn_hospital.configure(state='disabled')
                    self._resumir_historico()
                    self.status.set('Etapa 3 pausada. Resultados anteriores preservados; conclua a verificação no SISREG para retomar.')
                elif evento=='hospital_fim':
                    self.estatisticas.concluir('hospital',time.perf_counter()-self.inicio_hospital,
                        consultados=self.tentativas_hospital,encontrados=self.acertos_hospital,
                        pendencias=self.tentativas_hospital-self.acertos_hospital,
                        falhas=self.falhas_hospital,completa=(self.tentativas_hospital==self.estatisticas.etapas['hospital'].total
                        and not self.parar.is_set() and not self.navegacao_falhou))
                    self.tempo_hospital.set(self.estatisticas.comparativo('hospital'))
                    self._salvar_checkpoint()
                    self.processando=False;self.btn_hospital.configure(state='normal')
                    self._resumir_historico()
                    self._atualizar_avanco()
                    if self.persistencia_falhou:
                        self.status.set('FALHA de salvamento da etapa 3; não feche antes de recuperar os resultados.')
                    elif self.navegacao_falhou:
                        self.status.set('Etapa 3 suspensa por falhas consecutivas. Dados anteriores foram preservados.')
                    else:
                        self.status.set('Etapa 3: coleta automatizada encerrada. A análise fiscal das exceções permanece pendente.')
                    if not self.persistencia_falhou:
                        self._finalizar_relatorio()
                elif evento=='hospital_alerta':
                    self.navegacao_falhou=True
                    self.status.set(str(dado))
                elif evento=='lote_iniciado':
                    self.progresso.set(f'Iniciando pesquisas de {dado} pacientes...')
                elif evento=='lote_item':
                    idx,cns,motivo,contador,total=dado
                    self.consultas_cadastro+=1
                    self.consultas_acumuladas+=1
                    reg=self.sessao.registros[idx]
                    self.sessao.registrar_cadastro_em_lote(reg,cns,motivo)
                    self._evento_seguro('CADASTRO_OK' if reg.situacao == 'CNS_CONFIRMADO_SISREG' else 'CADASTRO_PENDENCIA','cadastro',contador)
                    self.motivos_cadastro[motivo]=self.motivos_cadastro.get(motivo,0)+1
                    if reg.situacao=='CNS_CONFIRMADO_SISREG':self.dados_atuais['cns']+=1
                    else:self.dados_atuais['pendentes']+=1
                    if motivo=='FALHA_DE_NAVEGACAO_OU_TEMPO':
                        self.dados_atuais['falhas']+=1
                        self._evento_seguro('ERRO_TECNICO','cadastro',contador)
                    # Checkpoint a cada 10 linhas, sempre depois da confirmação objetiva.
                    if contador%10==0:
                        self._salvar_checkpoint()
                    self._atualizar_linha_visual(idx,self._linha_visual(reg))
                    self._atualizar_linha_visual(idx,self._linha_visual(reg,com_cns=True),True)
                    self.barra.configure(value=100*contador/max(total,1))
                    identificados,elegiveis=self._cns_totais()
                    self.resumo_cadastro.set('Cadastro e CNS · '+
                        resumo_progresso(elegiveis,self.cns_aproveitados,self.cns_previstos,
                            contador).resumo()+
                        f' · CNS identificados no total: {identificados}/{elegiveis}')
                    self.tempo_cadastro.set(f'Tempo decorrido: {self._duracao(time.perf_counter()-self.inicio_cadastro)} · Manual hipotético: {self._duracao(total*10)} (10s por consulta).')
                    self.progresso.set(f'{contador}/{total} consultados nesta retomada · '
                                      f'{identificados} CNS acumulados · '
                                      f'{self.dados_atuais["pendentes"]} pendências nesta retomada')
                    pendencias=sorted(((n,m) for m,n in self.motivos_cadastro.items()
                                       if not m.startswith('CNS_CONFIRMADO')),reverse=True)
                    self.diagnostico_cns.set('Pendências por motivo: '+
                        ('; '.join(f'{rotulo_situacao(m)}: {n}' for n,m in pendencias[:3])
                         if pendencias else 'nenhuma até agora'))
                elif evento=='lote_fim':
                    processados,previstos=dado
                    identificados,elegiveis=self._cns_totais()
                    self.estatisticas.concluir('cadastro',time.perf_counter()-self.inicio_cadastro,
                        consultados=processados,encontrados=self.dados_atuais['cns'],
                        pendencias=self.dados_atuais['pendentes'],falhas=self.dados_atuais['falhas'],
                        completa=(processados==previstos and not self.parar.is_set() and not self.navegacao_falhou))
                    self.tempo_cadastro.set(self.estatisticas.comparativo('cadastro'))
                    self._salvar_checkpoint()
                    self.processando=False;self.btn_lote.configure(state='normal')
                    self._resumir_historico()
                    if not self.persistencia_falhou and not self.navegacao_falhou and not self.intervencao_pendente and processados==previstos and not self.parar.is_set():
                        self.cadastro_concluido=True
                        self.abas.tab(2,state='normal')
                        self._atualizar_avanco()
                        self.status.set('Etapa 2 concluída e salva. Iniciando consultas hospitalares na mesma sessão...')
                        # O worker ainda está ativo: apenas enfileira nova tarefa,
                        # sem reiniciar o login e sem clique extra na interface.
                        self.root.after(250, self._iniciar_hospital)
                    elif self.navegacao_falhou and not self.persistencia_falhou:
                        self.status.set('Sessão do SISREG pausada; progresso salvo. Aguarde a verificação humana no navegador.')
                    elif self.persistencia_falhou:
                        self.status.set('LOTE INTERROMPIDO: falha ao salvar. Feche o Excel e tente salvar novamente.')
                    else:
                        self.status.set(f'Lote interrompido após {processados}/{previstos} consultas. A etapa 3 permanece bloqueada.')
                elif evento=='lote_alerta':
                    self.navegacao_falhou=True
                    self.status.set(str(dado))
                elif evento=='diagnostico_navegacao':
                    self.status.set('Pesquisa SISREG não concluída (' + str(dado)[:48] + '). Registro encaminhado para pendências.')
                elif evento=='erro_login':
                    self.estatisticas.diagnosticar('LOGIN_SUBMETIDO','ERRO',categoria='SESSAO_NAO_AUTORIZADA')
                    self.browser_ready=False
                    self.status.set(str(dado))
                elif evento=='navegador_parou':
                    self._ocultar_verificacao()
                    self.estatisticas.diagnosticar('SESSAO_ENCERRADA','OK')
                    if self.navegacao_falhou and self.preparo_concluido:
                        self.status.set('Sessão interrompida. Informe novamente seu login para retomar somente os CNS pendentes. A planilha foi preservada.')
                    self.browser_ready=False
                    if self.login_pendente and not self.parar.is_set():
                        self.login_pendente=False
                        # Eventos são entregues antes de finalizar a thread: aguardar
                        # o término efetivo, sem bloquear o loop Tk.
                        self.root.after(250, self._retomar_login_pendente)
                    if self.processando:
                        self._salvar_checkpoint()
                        self.processando=False;self.btn_lote.configure(state='normal')
                        self.btn_hospital.configure(state='normal')
                        self._resumir_historico()
        except queue.Empty:pass
        self.root.after(140,self._ler_eventos)

    def _evento_seguro(self, evento, etapa='geral', indice=None):
        try:
            if self.historico:
                self.historico.evento(evento, etapa, indice)
        except OSError:
            pass  # Falha de log não bloqueia conferência; nenhuma informação livre é registrada.

    def _resumir_historico(self):
        if not self.historico:return
        regs=self.sessao.registros
        positivos=sum(r.situacao in ('SOLICITACAO_HOSPITALAR_CONFERIDA','DADOS_COLETADOS_SEM_DIVERGENCIA') for r in regs)
        cns=sum(r.situacao=='CNS_CONFIRMADO_SISREG' or bool(r.cns) for r in regs)
        consultas=sum(bool(r.consulta_hospitalar) for r in regs)
        pendencias=sum(bool(r.situacao) and (r.situacao.startswith('PENDENTE_') or 'AUSENTE' in r.situacao or
                         'DIVERGENTE' in r.situacao or 'CONFLITO' in r.situacao) for r in regs)
        try:
            self.historico.atualizar(cns_identificados=cns,consultas_hospitalares=consultas,
                sem_divergencia_identificada=positivos,pendencias=pendencias,
                erros_tecnicos=self.dados_atuais.get('falhas',0)+self.falhas_hospital)
        except (OSError,ValueError):pass

    def _registrar_falha_preparacao(self, segundos: float) -> None:
        """TXT diagnóstico seguro disponível mesmo sem arquivo XLSX concluído."""
        if not self.arquivo_planilha:
            return
        self.estatisticas.encerrar(segundos=segundos,situacao='PARCIAL')
        self.estatisticas.diagnosticar('FIM_EXECUCAO','ERRO',segundos=segundos,
                                     categoria='PREPARACAO_NAO_CONCLUIDA')
        if self.historico and not self.historico.termino:
            try:self.historico.encerrar('FALHA_TECNICA')
            except (OSError,ValueError):pass
        carimbo=datetime.now().strftime('%d%m%Y_%H%M%S')
        try:
            _analises,pasta=pastas_de_saida()
        except OSError:
            self.status.set('Sem permissão para criar a pasta Logs junto do executável; contate a TI.')
            return
        destino=pasta/f'RELATORIO_TECNICO_RPA_FALHA_{carimbo}.txt'
        if destino.exists():
            import uuid
            destino=pasta/f'RELATORIO_TECNICO_RPA_FALHA_{carimbo}_{uuid.uuid4().hex[:6]}.txt'
        relatorio_tecnico(self.estatisticas,self.historico,destino)
        self.estatisticas.relatorio=destino.name
        self.resultado_arquivo_log.set(f'Diagnóstico da falha: {destino.name}')
        self.relatorio_finalizado=True
        self.status.set(self.status.get()+f' Diagnóstico: {destino.name}')

    def _finalizar_relatorio(self):
        if self.relatorio_finalizado or not self.sessao.origem:
            return
        self._resumir_historico()
        # Inclui o tempo de espera entre etapas na medição total, sem escondê-lo.
        segundos=(time.perf_counter()-self.inicio_ciclo) if self.inicio_ciclo is not None else 0.0
        etapas=self.estatisticas.etapas
        completa=all(e.concluida for e in etapas.values()) and not self.persistencia_falhou
        self.estatisticas.encerrar(segundos=segundos,situacao='CONCLUIDA' if completa else 'PARCIAL')
        self.estatisticas.diagnosticar('FIM_EXECUCAO','OK' if completa else 'PENDENCIA',segundos=segundos)
        try:
            if self.historico and not self.historico.termino:
                self.historico.encerrar('CONCLUIDA' if completa else 'INTERROMPIDA')
        except (OSError,ValueError): pass
        try:
            _analises,destino_base=pastas_de_saida()
        except OSError:
            self.resultado_arquivo_log.set('Sem permissão de gravação na pasta Logs ao lado do executável. Acione a TI.')
            return
        carimbo=datetime.now().strftime('%d%m%Y_%H%M%S')
        # Não sobrescrever log de outra execução iniciada no mesmo segundo.
        nome=f'RELATORIO_TECNICO_RPA_{carimbo}.txt'
        destino=destino_base/nome
        if destino.exists():
            destino=destino_base/f'RELATORIO_TECNICO_RPA_{carimbo}_{self.historico.id[:6] if self.historico else "novo"}.txt'
        try:
            relatorio_tecnico(self.estatisticas,self.historico,destino)
            self.estatisticas.relatorio=destino.name
            self.resultado_arquivo_log.set(f'Análises/{self.sessao.origem.name} · Logs/{destino.name}')
        except (OSError,ValueError):
            self.resultado_arquivo_log.set('Não foi possível gerar o TXT em Logs. Verifique permissão de gravação.')
        n=len(self.sessao.registros)
        e2=etapas['cadastro'];e3=etapas['hospital']
        identificados,elegiveis=self._cns_totais()
        cpf_total=sum(bool(r.cpf) for r in self.sessao.registros)
        fichas_acumuladas=sum(r.consulta_hospitalar in ('FICHA_CONFERIDA','PROCEDIMENTO_DIVERGENTE')
                              and r.carater and r.autorizador for r in self.sessao.registros)
        sem_divergencia=sum(r.situacao=='DADOS_COLETADOS_SEM_DIVERGENCIA'
                           for r in self.sessao.registros)
        self.resultado_geral.set(f'{n} registros hospitalares · {cpf_total} CPFs disponíveis ({percentual(cpf_total,n)})\n'
            f'{identificados}/{elegiveis} CNS acumulados ({percentual(identificados,elegiveis)}) · '
            f'{fichas_acumuladas}/{n} fichas com dados coletados ({percentual(fichas_acumuladas,n)})\n'
            f'Sem diferenças nos campos consultados: {sem_divergencia} · '
            f'consultas hospitalares nesta execução: {e3.consultados}/{e3.total} · '
            f'erros técnicos: {sum(e.falhas_tecnicas for e in etapas.values())}.')
        manual=self.estatisticas.total_manual()
        dif=manual-segundos
        self.resultado_tempos.set(
            f'Tempo total decorrido (inclui esperas): {self._duracao(segundos)}\n'
            f'Etapa 1: {self._duracao(etapas["preparo"].segundos)} · Etapa 2: {self._duracao(e2.segundos)} · Etapa 3: {self._duracao(e3.segundos)}\n'
            f'Tempo manual hipotético: {self._duracao(manual)} (15s por AIH + 10s por consulta de CNS + 10s por consulta hospitalar).\n'
            f'Diferença hipotética: {"+" if dif>=0 else "−"}{self._duracao(abs(dif))}. Não demonstra economia comprovada.')
        self.relatorio_finalizado=True
        self.abas.tab(3,state='normal')
        self._atualizar_avanco()

    def _exportar_pendencias(self):
        if not self.preparo_concluido:
            self.status.set('Prepare a conferência antes de exportar pendências.');return
        destino=filedialog.asksaveasfilename(title='Exportar somente pendências',defaultextension='.xlsx',
             filetypes=[('Planilha Excel','*.xlsx')],initialfile='Pendencias_RPA_SISREG.xlsx')
        if not destino:return
        try:
            n=exportar_pendencias(self.sessao,Path(destino))
            self.status.set(f'Relatório mínimo de pendências gerado: {n} registros. Análise fiscal pendente.')
        except (OSError,ValueError) as exc:
            self.status.set('Não foi possível exportar as pendências. Escolha outra pasta/nome e tente novamente.')

    def _sobre(self):
        janela=tk.Toplevel(self.root)
        janela.title('Sobre a ferramenta — RPA SISREG')
        janela.geometry('730x720');janela.minsize(630,540)
        janela.transient(self.root)
        painel=ttk.Frame(janela);painel.pack(fill='both',expand=True)
        canvas=tk.Canvas(painel,highlightthickness=0)
        barra=ttk.Scrollbar(painel,orient='vertical',command=canvas.yview)
        canvas.configure(yscrollcommand=barra.set)
        barra.pack(side='right',fill='y');canvas.pack(side='left',fill='both',expand=True)
        frame=ttk.Frame(canvas,padding=18)
        janela_canvas=canvas.create_window((0,0),window=frame,anchor='nw')
        frame.bind('<Configure>',lambda e:canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.bind('<Configure>',lambda e:canvas.itemconfigure(janela_canvas,width=e.width))
        ttk.Label(frame,text='RPA SISREG · Sobre a ferramenta',font=('Segoe UI',15,'bold')).pack(anchor='w')
        ttk.Label(frame,text=rotulo_versao(),foreground='#52677a').pack(anchor='w',pady=(2,12))
        blocos=[
          ('Origem da demanda','Desenvolvida a partir de demanda da equipe de fiscalização contratual, diante do alto volume de conferências manuais de internações.'),
          ('Processo apoiado','Apoia a conferência das internações informadas pelo prestador, automatizando extração de espelhos e consultas ao SISREG.'),
          ('Dados utilizados','Nome, AIH, CPF, CNS, procedimento e dados administrativos estritamente necessários à conferência.'),
          ('Proteção e rastreabilidade','Os dados de pacientes permanecem nos arquivos institucionais locais. Credenciais não são salvas. Histórico técnico reúne horários, quantidades, versão e hashes, sem dados individuais.'),
          ('Retomada','As etapas ignoram CPF e CNS já preenchidos e preservam resultados hospitalares completos. O andamento mostra separadamente o total acumulado e a análise desta sessão; pendências técnicas podem ser repetidas.'),
          ('Conferência e status','A consulta hospitalar lê caráter, código da solicitação e procedimento. Procedimento divergente requer análise fiscal; campo ausente ou ficha não aberta significa consulta incompleta, não irregularidade do paciente.'),
          ('CAPTCHA e conexão','O SISREG pode exigir verificação humana ou apresentar indisponibilidade. O RPA pausa e preserva resultados; a operadora conclui a verificação no navegador. Não contorna CAPTCHA nem garante execução desassistida.'),
          ('Tempo de referência','Tempos manuais são estimativas de 15 s para PDF/AIH e 10 s por consulta SISREG, não produtividade manual aferida. É possível que o SISREG seja mais lento; requisições não são aceleradas para evitar restrições.'),
          ('Responsabilidade do fiscal','Esta ferramenta é um recurso de apoio à conferência. A identificação automática de dados não substitui a análise do fiscal. Divergências, inconsistências e decisões relacionadas ao atesto permanecem sob análise humana.'),
          ('Créditos','Desenvolvimento: Enf. Bruno Vinícius. Coautoria: Joice Correa Gomes e Heloisa Hoffmann.'),
          ('Suporte','bruno.vinicius@joinville.sc.gov.br')]
        for titulo,conteudo in blocos:
            ttk.Label(frame,text=titulo,font=('Segoe UI',10,'bold')).pack(anchor='w',pady=(7,1))
            ttk.Label(frame,text=conteudo,wraplength=560,justify='left').pack(anchor='w')
        ttk.Button(frame,text='Fechar',command=janela.destroy).pack(anchor='e',pady=(10,0))

    def encerrar(self):
        if getattr(self, '_fechamento_lento', False):
            from tkinter import messagebox
            sair=messagebox.askyesno('Encerrar com navegador sem resposta?',
                'O SISREG não respondeu à interrupção. A planilha será salva '
                'antes de sair, mas a consulta ainda em andamento pode ser '
                'perdida. Deseja encerrar a aplicação mesmo assim?')
            if not sair:
                return
            if self.preparo_concluido and self.sessao.origem and not self._salvar_checkpoint():
                if not messagebox.askyesno('Falha ao salvar a planilha',
                        'O checkpoint não pôde ser gravado. Deseja encerrar '
                        'e descartar as alterações ainda não salvas?'):
                    return
            self.navegacao_falhou=True
            self.processando=False
            self._fechar_aplicacao()
            return
        self.parar.set();self.pausa.clear();self.aguardar_humano.confirmar()
        self.login_pendente=False;self.usuario.set('');self.senha.set('')
        # Caso o processo esteja ativo, a janela aguarda a gravação de resultados recebidos.
        if self.persistencia_falhou and not self.processando:
            from tkinter import messagebox
            if not messagebox.askyesno('Alterações não salvas',
                  'Há resultados ainda não gravados na planilha. Deseja sair e descartá-los?'):
                return
        if self.processando or (self.thread_navegador and self.thread_navegador.is_alive()):
            self.status.set('Encerrando a sessão SISREG e concluindo eventuais salvamentos...')
            self._fechamento_lento=False
            self._prazo_fechamento = time.monotonic() + 15
            self.root.after(250,self._aguardar_encerramento)
        else:
            self._fechar_aplicacao()

    def _fechar_aplicacao(self):
        if self.preparo_concluido and not self.relatorio_finalizado and not self.persistencia_falhou:
            try: self._finalizar_relatorio()
            except (OSError,ValueError): pass
        try:
            self._resumir_historico()
            if self.historico and not self.historico.termino:
                self.historico.encerrar('INTERROMPIDA' if self.parar.is_set()
                        else 'CONCLUIDA' if self.preparo_concluido else 'INTERROMPIDA')
        except (OSError,ValueError):pass
        self.usuario.set('');self.senha.set('')
        self.root.destroy()

    def _aguardar_encerramento(self):
        ativo = self.processando or bool(self.thread_navegador and self.thread_navegador.is_alive())
        if not ativo:
            self._fechamento_lento=False
            self._fechar_aplicacao()
            return
        if time.monotonic() >= self._prazo_fechamento and not getattr(self, '_fechamento_lento', False):
            self._fechamento_lento=True
            self.status.set('O navegador não respondeu. Clique novamente em Encerrar '
                            'para confirmar a saída ou aguarde o encerramento normal.')
        self.root.after(500,self._aguardar_encerramento)


def main():
    # Teste real do executável empacotado sem iniciar consultas SISREG.
    # Só ativado pela opção explícita usada no GitHub Actions.
    if sys.argv[1:] == ['--smoke-test']:
        Path('rpa_sisreg_smoke.ok').write_text(APP_VERSION + ':OK', encoding='utf-8')
        return
    root=tk.Tk()
    Aplicativo(root)
    root.mainloop()


if __name__ == '__main__':
    main()
