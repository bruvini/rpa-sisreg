"""SISREG III — automação autorizada de consultas em três etapas.

Lê PDF/XLSX localmente, busca CNS e dados da solicitação hospitalar no SISREG.
Não altera solicitações e não salva senha. Dados só são gravados na XLSX local.

USO CONDICIONADO À AUTORIZAÇÃO DA REGULAÇÃO/TI.
"""

from __future__ import annotations

import queue
import time
import os
from pathlib import Path
from tkinter import filedialog
from datetime import datetime
from sisreg_navigation import (consultar_cadastro, ler_resultado_cadastro, autenticao_ativa, NavegacaoInesperada)
from aih_extract import ler_espelhos_pdf, cpf_valido, cns_formato
from planilha import SessaoPlanilha
from sisreg_navigation import NavegacaoInesperada
from sisreg_hospital import consultar_solicitacao_hospitalar, ResultadoHospital
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

VERSAO = "0.5.0 — preparação, CNS em lote e auditoria hospitalar"
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
        root.title('RPA SISREG · Conferência em lote — v0.5')
        root.geometry('1080x750')
        root.minsize(900,640)
        root.configure(bg=FUNDO)
        root.protocol('WM_DELETE_WINDOW', self.encerrar)
        self.eventos=queue.Queue()
        self.comandos=queue.Queue()
        self.parar=threading.Event()
        self.pausa=threading.Event()
        self.thread_navegador=None
        self.sessao=SessaoPlanilha()
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
        self.motivos_cadastro={}
        self.atividade_preparo=tk.StringVar(value='Aguardando início.')
        self.resultado_titulo=tk.StringVar(value='')
        self.resultado_descritivo=tk.StringVar(value='')
        self.cronometro=tk.StringVar(value='Tempo: 00:00')
        self.inicio_preparo=None
        self.tipo_lote='cadastro'
        self.status=tk.StringVar(value='Selecione a planilha-padrão e o espelho PDF do hospital.')
        self.resumo=tk.StringVar(value='Nenhuma conferência carregada.')
        self.progresso=tk.StringVar(value='Aguardando preparação.')
        self.dados_atuais={'cpf':0,'cns':0,'pendentes':0,'falhas':0,'total':0}
        self._montar()
        self.abas.tab(1,state='disabled')
        self.abas.tab(2,state='disabled')
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
        topo=tk.Frame(self.root,bg=AZUL,height=77);topo.pack(fill='x');topo.pack_propagate(False)
        tk.Label(topo,text='RPA SISREG  |  Conferência em lote',bg=AZUL,fg='white',
                 font=('Segoe UI',17,'bold')).pack(anchor='w',padx=24,pady=(10,0))
        tk.Label(topo,text='v0.5 · CPF, CNS e solicitação hospitalar · atualiza XLSX com backup',
                 bg=AZUL,fg='#d4e8f7',font=('Segoe UI',10)).pack(anchor='w',padx=24)
        corpo=ttk.Frame(self.root,padding=13);corpo.pack(fill='both',expand=True)
        self.abas=ttk.Notebook(corpo);self.abas.pack(fill='both',expand=True)
        a=ttk.Frame(self.abas,padding=12);b=ttk.Frame(self.abas,padding=12);c=ttk.Frame(self.abas,padding=12)
        self.abas.add(a,text='  1  Planilha e PDF  ')
        self.abas.add(b,text='  2  Pesquisa em lote SISREG  ')
        self.abas.add(c,text='  3  Solicitações hospitalares  ')
        ttk.Label(a,text='Os CPFs do PDF são gravados diretamente na planilha. Um backup é criado antes da primeira alteração.',
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
                 font=('Segoe UI',10),wraplength=955,justify='left').pack(anchor='w',padx=12,pady=(0,10))
        grade=ttk.Frame(a);grade.pack(fill='both',expand=True)
        self.grade=grade
        cfg=[('aba','Aba',130),('linha','Linha',52),('aih','AIH',122),('paciente','Paciente',240),
             ('cpf','CPF',109),('cns','CNS',140),('situacao','Situação',260)]
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
        ttk.Label(b,textvariable=self.progresso,font=('Segoe UI',12,'bold')).pack(anchor='w',pady=(16,8))
        self.diagnostico_cns=tk.StringVar(value='O motivo das pendências será mostrado aqui após as consultas.')
        ttk.Label(b,textvariable=self.diagnostico_cns,wraplength=930).pack(anchor='w',pady=(0,8))
        self.barra=ttk.Progressbar(b,mode='determinate',maximum=100,value=0)
        self.barra.pack(fill='x')
        ttk.Label(b,text='O RPA pesquisa CPF por CPF. Só grava CNS quando o resultado mostra nome '
                  'inequívoco e um único CNS identificado. Resultados ambíguos viram pendência; '
                  'o robô segue para o próximo paciente. A etapa 3 pesquisa a AIH hospitalar.',
                  wraplength=930).pack(anchor='w',pady=(15,0))
        ttk.Label(b,text='A planilha é salva ao longo do lote. Feche-a no Excel antes de iniciar; '
                  'o programa interrompe a gravação se detectar edição externa ou bloqueio do arquivo.',
                  wraplength=930).pack(anchor='w',pady=(12,0))
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
        ttk.Label(c,textvariable=self.progresso_hospital,font=('Segoe UI',11,'bold')).pack(anchor='w',pady=(18,9))
        self.barra_hospital=ttk.Progressbar(c,mode='determinate',maximum=100,value=0)
        self.barra_hospital.pack(fill='x')
        ttk.Label(c,text='O tempo medido é real. A estimativa manual usa 15 segundos por AIH como premissa fixa '
                  'e não comprova economia de trabalho. Não são alteradas '
                  'solicitações no SISREG. Feche o Excel durante os lotes.',wraplength=920).pack(anchor='w',pady=(14,0))
        rodape=ttk.Frame(corpo);rodape.pack(fill='x',pady=(10,0))
        ttk.Label(rodape,textvariable=self.status,wraplength=910).pack(side='left',fill='x',expand=True)
        ttk.Button(rodape,text='Encerrar',command=self.encerrar).pack(side='right')

    def _escolher_xlsx(self):
        arq=filedialog.askopenfilename(title='Planilha-padrão',filetypes=[('Excel','*.xlsx')])
        if arq:
            self._invalidar_preparo()
            self.arquivo_planilha=Path(arq)
            self.lbl_xlsx.configure(text=self.arquivo_planilha.name)
    def _escolher_pdf(self):
        arq=filedialog.askopenfilename(title='Espelho de AIH',filetypes=[('PDF','*.pdf')])
        if arq:
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
        self.cartao_resultado.pack_forget()
        self.atividade_preparo.set('Arquivos alterados: execute a conferência novamente.')

    def _preparar(self):
        if self.carregando or self.processando:return
        if not self.arquivo_planilha:
            self.status.set('Selecione o XLSX hospitalar.');return
        self.preparo_concluido=False;self.cadastro_concluido=False
        self.abas.tab(1,state='disabled');self.abas.tab(2,state='disabled')
        self.cartao_resultado.pack_forget()
        self.carregando=True;self.inicio_preparo=time.perf_counter();self._atualizar_relogio();self.btn_preparar.configure(state='disabled')
        self.atividade_preparo.set('Lendo planilha, indexando PDF e criando backup...')
        self.status.set('Conferência em andamento. Não abra o Excel.')
        def tarefa():
            try:
                sessao=SessaoPlanilha()
                sessao.carregar(self.arquivo_planilha)
                informacao='PDF não informado.'
                if self.arquivo_pdf:
                    ix,avisos=ler_espelhos_pdf(self.arquivo_pdf)
                    sessao.complementar_pdf(ix,self.arquivo_pdf)
                    informacao=f'{len(ix)} AIHs indexadas no espelho.'
                    if avisos: informacao+=' Estrutura do PDF requer revisão.'
                gravacao=sessao.salvar_na_planilha(motivo='pdf')
                self.eventos.put(('preparado',(sessao,informacao,gravacao,time.perf_counter()-self.inicio_preparo)))
            except Exception as e:
                self.eventos.put(('erro_preparo',str(e)))
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
        itens=self.tabela.get_children()
        if itens:self.tabela.delete(*itens)
        for i,r in enumerate(self.sessao.registros):
            self.tabela.insert('','end',iid=str(i),values=(r.aba,r.linha,r.aih,r.nome,r.cpf,r.cns,r.situacao))

    def _iniciar_login(self):
        if not self.preparo_concluido or self.carregando:
            self.status.set('Conclua a etapa 1 antes de acessar o SISREG.');return
        if self.thread_navegador and self.thread_navegador.is_alive():
            self.status.set('Já há um navegador ativo.');return
        u=self.usuario.get().strip();s=self.senha.get()
        if not u or not s:
            self.status.set('Preencha usuário e senha para abrir o SISREG.');return
        canal='chrome' if self.navegador.get()=='Google Chrome' else 'msedge'
        self.usuario.set('');self.senha.set('');self.parar.clear()
        self.browser_ready=False;self.cadastro_concluido=False
        self.thread_navegador=threading.Thread(target=self._navegador_worker,args=(u,s,canal),daemon=True)
        self.thread_navegador.start();self.status.set('Abrindo SISREG...')

    def _navegador_worker(self,usuario,senha,canal):
        browser=None
        try:
            with sync_playwright() as p:
                browser=p.chromium.launch(channel=canal,headless=False)
                contexto=browser.new_context(accept_downloads=False)
                pagina=contexto.new_page()
                try:
                    pagina.goto(URL_SISREG,wait_until='domcontentloaded',timeout=45000)
                    submeter_login(pagina,usuario,senha)
                    self.eventos.put(('login_enviado',None))
                    # Detecção pós-login sem enviar segundo login; qualquer verificação manual mantém-se possível.
                    if autenticao_ativa(pagina,timeout=45000):
                        self.eventos.put(('autenticado',None))
                    else:
                        self.eventos.put(('erro_login','O menu autenticado não apareceu no prazo. Consulte o navegador; não iniciamos pesquisas.'))
                except Exception:
                    self.eventos.put(('erro_login','Login ou acesso indisponível. Verifique a página no navegador.'))
                finally:
                    usuario='';senha=''
                while not self.parar.is_set():
                    try: cmd,payload=self.comandos.get(timeout=0.2)
                    except queue.Empty:continue
                    if cmd == 'hospital':
                        indices=payload
                        self.eventos.put(('hospital_iniciado',len(indices)))
                        erros_seguidos=0
                        for j,idx in enumerate(indices,1):
                            if self.parar.is_set():break
                            while self.pausa.is_set() and not self.parar.wait(.25):pass
                            if self.parar.is_set():break
                            r=self.sessao.registros[idx]
                            inicio=time.perf_counter()
                            try:
                                validas=[pg for pg in contexto.pages if not pg.is_closed() and endereco_oficial(pg.url)]
                                if not validas:raise NavegacaoInesperada('Sessão SISREG encerrada.')
                                pagina=validas[-1]
                                resultado=consultar_solicitacao_hospitalar(pagina,r.cns,r.aih,r.procedimento)
                                erros_seguidos=0
                            except Exception as exc:
                                erros_seguidos+=1
                                resultado=ResultadoHospital('FALHA_NAVEGACAO',
                                              'Consulta não finalizada: '+type(exc).__name__+'. Revisar a tela do SISREG.')
                            self.eventos.put(('hospital_item',(idx,resultado,time.perf_counter()-inicio,j,len(indices))))
                            if erros_seguidos>=3:
                                self.eventos.put(('hospital_alerta','Três falhas seguidas; lote hospitalar suspenso.'))
                                break
                            self.parar.wait(1.8)
                        self.eventos.put(('hospital_fim',len(indices)))
                        continue
                    if cmd!='lote':continue
                    indices=payload
                    self.eventos.put(('lote_iniciado',len(indices)))
                    erros_seguidos=0
                    processados=0
                    for j,idx in enumerate(indices,1):
                        if self.parar.is_set():break
                        while self.pausa.is_set() and not self.parar.wait(0.25):pass
                        if self.parar.is_set():break
                        r=self.sessao.registros[idx]
                        identificador=r.cpf
                        try:
                            validas=[pg for pg in contexto.pages if not pg.is_closed() and endereco_oficial(pg.url)]
                            if not validas:raise NavegacaoInesperada('Sessão SISREG encerrada.')
                            # Pesquisa sempre no contexto oficial; nunca cadastra nem altera solicitações.
                            pagina=validas[-1]
                            consultar_cadastro(pagina,identificador)
                            cns,motivo=ler_resultado_cadastro(pagina,r.nome,identificador,espera=7500)
                            erros_seguidos=0
                        except Exception as exc:
                            cns,motivo=None,'FALHA_DE_NAVEGACAO_OU_TEMPO'
                            erros_seguidos+=1
                            self.eventos.put(('diagnostico_navegacao',type(exc).__name__ + ': ' + str(exc)[:180]))
                        self.eventos.put(('lote_item',(idx,cns,motivo,j,len(indices))))
                        processados=j
                        if erros_seguidos>=3:
                            self.eventos.put(('lote_alerta','Três falhas consecutivas de navegação. Lote suspenso para verificar tela/seletores.'))
                            break
                        # Intervalo deliberado para não sobrecarregar o sistema público.
                        self.parar.wait(1.8)
                    self.eventos.put(('lote_fim',(processados,len(indices))))
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
        selecionados=[i for i,r in enumerate(self.sessao.registros) if cpf_valido(r.cpf)
                     and r.aih and r.nome and not r.cns
                     and r.situacao not in ('CPF_CONFLITANTE_PDF','ESPELHOS_CONFLITANTES','NOME_DIVERGENTE_ESPELHO')]
        if not selecionados:
            self.status.set('Nenhum CPF elegível pendente. Etapa 2 concluída.')
            self.cadastro_concluido=True
            self.abas.tab(2,state='normal')
            return
        self.tipo_lote='cadastro';self.processando=True;self.persistencia_falhou=False;self.navegacao_falhou=False;self.pausa.clear();self.parar.clear()
        self.cadastro_concluido=False
        self.abas.tab(2,state='disabled')
        self.dados_atuais={'cpf':0,'cns':0,'pendentes':0,'falhas':0,'total':len(selecionados)}
        self.motivos_cadastro={}
        self.barra.configure(value=0)
        self.btn_lote.configure(state='disabled')
        self.comandos.put(('lote',selecionados))
        self.status.set(f'Lote iniciado com {len(selecionados)} pesquisas, sem interação linha a linha.')
    def _iniciar_hospital(self):
        if self.processando:
            self.status.set('Outro lote em execução; aguarde sua conclusão.');return
        if not self.preparo_concluido or not self.cadastro_concluido or not self.thread_navegador or not self.thread_navegador.is_alive() or not self.browser_ready:
            self.status.set('Aguarde o fim das etapas 1 e 2 antes da consulta hospitalar.');return
        candidatos=[i for i,r in enumerate(self.sessao.registros) if cns_formato(r.cns)
                    and r.aih and r.nome and r.consulta_hospitalar not in
                    ('FICHA_CONFERIDA','PROCEDIMENTO_DIVERGENTE')
                    and not r.situacao.startswith(('CNS_CONFLITO','CPF_CONFLITANTE','ESPELHOS_CONFLITANTES'))]
        if not candidatos:
            self.status.set('Não há solicitações hospitalares pendentes elegíveis com CNS na planilha.');return
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
        self.parar.set();self.pausa.clear()
        self.status.set('Solicitada interrupção; os resultados recebidos serão salvos.')

    def _salvar_checkpoint(self):
        try:
            saida=self.sessao.salvar_na_planilha(motivo='lote_cns')
            return True
        except Exception as e:
            self.persistencia_falhou=True
            self.parar.set()
            self.pausa.clear()
            self.status.set('FALHA DE SALVAMENTO: '+str(e)+'. A execução foi interrompida; não feche antes de recuperar os resultados.')
            return False

    def _tentar_salvar(self):
        if self._salvar_checkpoint():
            self.persistencia_falhou=False
            self.status.set('Alterações salvas na planilha hospitalar.')

    def _ler_eventos(self):
        try:
            while True:
                evento,dado=self.eventos.get_nowait()
                if evento=='preparado':
                    sessao,informacao,atualizacao,segundos=dado
                    self.sessao=sessao
                    self._atualizar_tabela()
                    self.cronometro.set('Tempo: '+self._duracao(segundos))
                    manual=len(sessao.registros)*MANUAL_SEGUNDOS_POR_AIH
                    self.resultado_titulo.set(f'✓ Conferência concluída — {len(sessao.registros)} AIHs em {self._duracao(segundos)}')
                    self.resultado_descritivo.set(
                        f'{atualizacao["cpf"]} CPF(s) gravados · {informacao}  |  '
                        f'Manual estimado: {self._duracao(manual)} (15 s/AIH, hipótese fixa). '
                        f'Diferença estimada: {self._duracao(max(0,manual-segundos))}. Backup criado/preservado.')
                    self.cartao_resultado.pack(fill='x',pady=(0,8),before=self.grade)
                    self.atividade_preparo.set('Concluído. Arquivo hospitalar atualizado.')
                    self.preparo_concluido=True
                    self.abas.tab(1,state='normal')
                    self.status.set('Etapa 1 concluída. Agora pode acessar o SISREG.')
                    self.carregando=False;self.btn_preparar.configure(state='normal')
                elif evento=='erro_preparo':
                    self.carregando=False;self.btn_preparar.configure(state='normal')
                    self.atividade_preparo.set('Falha na preparação; verifique o erro e tente novamente.')
                    self.status.set('Preparação não concluída: '+str(dado))
                elif evento=='login_enviado':
                    self.status.set('Login enviado; aguardando o menu autenticado para iniciar o lote automaticamente.')
                elif evento=='autenticado':
                    self.browser_ready=True
                    self.status.set('Acesso identificado. Iniciando automaticamente a pesquisa de todos os CPFs elegíveis...')
                    self._iniciar_lote()
                elif evento=='hospital_iniciado':
                    self.progresso_hospital.set(f'Iniciando {dado} consultas hospitalares...')
                elif evento=='hospital_item':
                    idx,resultado,duracao,contador,total=dado
                    reg=self.sessao.registros[idx]
                    self.sessao.registrar_hospital(reg,resultado,duracao)
                    if contador%15==0: self._salvar_checkpoint()
                    if self.tabela.exists(str(idx)):
                        self.tabela.item(str(idx),values=(reg.aba,reg.linha,reg.aih,reg.nome,reg.cpf,reg.cns,reg.situacao))
                    self.barra_hospital.configure(value=100*contador/max(1,total))
                    self.progresso_hospital.set(f'{contador}/{total} consultadas · última: {resultado.situacao} · '
                                               f'{self._duracao(duracao)} nesta AIH')
                elif evento=='hospital_fim':
                    self._salvar_checkpoint()
                    self.processando=False;self.btn_hospital.configure(state='normal')
                    if self.persistencia_falhou:
                        self.status.set('FALHA de salvamento da etapa 3; não feche antes de recuperar os resultados.')
                    elif self.navegacao_falhou:
                        self.status.set('Etapa 3 suspensa por falhas consecutivas. Dados anteriores foram preservados.')
                    else:
                        self.status.set('Etapa 3 encerrada: conferências verificáveis salvas. Confira as pendências.')
                elif evento=='hospital_alerta':
                    self.navegacao_falhou=True
                    self.status.set(str(dado))
                elif evento=='lote_iniciado':
                    self.progresso.set(f'Iniciando pesquisas de {dado} pacientes...')
                elif evento=='lote_item':
                    idx,cns,motivo,contador,total=dado
                    reg=self.sessao.registros[idx]
                    self.sessao.registrar_cadastro_em_lote(reg,cns,motivo)
                    self.motivos_cadastro[motivo]=self.motivos_cadastro.get(motivo,0)+1
                    if reg.situacao=='CNS_CONFIRMADO_SISREG':self.dados_atuais['cns']+=1
                    else:self.dados_atuais['pendentes']+=1
                    if motivo=='FALHA_DE_NAVEGACAO_OU_TEMPO':self.dados_atuais['falhas']+=1
                    # Checkpoint a cada 10 linhas, sempre depois da confirmação objetiva.
                    if contador%10==0:
                        self._salvar_checkpoint()
                    if self.tabela.exists(str(idx)):
                        self.tabela.item(str(idx),values=(reg.aba,reg.linha,reg.aih,reg.nome,reg.cpf,reg.cns,reg.situacao))
                    self.barra.configure(value=100*contador/max(total,1))
                    self.progresso.set(f'{contador}/{total} consultados · '
                                      f'{self.dados_atuais["cns"]} CNS identificados · '
                                      f'{self.dados_atuais["pendentes"]} pendências')
                    pendencias=sorted(((n,m) for m,n in self.motivos_cadastro.items()
                                       if not m.startswith('CNS_CONFIRMADO')),reverse=True)
                    self.diagnostico_cns.set('Pendências por motivo: '+
                        ('; '.join(f'{m}: {n}' for n,m in pendencias[:3]) if pendencias else 'nenhuma até agora'))
                elif evento=='lote_fim':
                    processados,previstos=dado
                    self._salvar_checkpoint()
                    self.processando=False;self.btn_lote.configure(state='normal')
                    if not self.persistencia_falhou and not self.navegacao_falhou and processados==previstos and not self.parar.is_set():
                        self.cadastro_concluido=True
                        self.abas.tab(2,state='normal')
                        self.status.set('Etapa 2 concluída: dados gravados na planilha. Etapa 3 liberada.')
                    elif self.navegacao_falhou and not self.persistencia_falhou:
                        self.status.set('Lote suspenso por falhas consecutivas do SISREG. Salvos os dados já obtidos; use Retomar quando disponível.')
                    elif self.persistencia_falhou:
                        self.status.set('LOTE INTERROMPIDO: falha ao salvar. Feche o Excel e tente salvar novamente.')
                    else:
                        self.status.set(f'Lote interrompido após {processados}/{previstos} consultas. A etapa 3 permanece bloqueada.')
                elif evento=='lote_alerta':
                    self.navegacao_falhou=True
                    self.status.set(str(dado))
                elif evento=='diagnostico_navegacao':
                    self.status.set('Pesquisa SISREG pendente: '+str(dado))
                elif evento=='erro_login':self.status.set(str(dado))
                elif evento=='navegador_parou':
                    self.browser_ready=False
                    if self.processando:
                        self._salvar_checkpoint()
                        self.processando=False;self.btn_lote.configure(state='normal')
                        self.btn_hospital.configure(state='normal')
        except queue.Empty:pass
        self.root.after(140,self._ler_eventos)

    def encerrar(self):
        self.parar.set();self.pausa.clear();self.usuario.set('');self.senha.set('')
        # Caso o processo esteja ativo, a janela aguarda a gravação de resultados recebidos.
        if self.persistencia_falhou and not self.processando:
            from tkinter import messagebox
            if not messagebox.askyesno('Alterações não salvas',
                  'Há resultados ainda não gravados na planilha. Deseja sair e descartá-los?'):
                return
        if self.processando:
            self.status.set('Interrompendo; aguarde o salvamento dos dados do lote...')
            self.root.after(500,self._aguardar_encerramento)
        else:
            self.root.destroy()

    def _aguardar_encerramento(self):
        if self.processando:self.root.after(500,self._aguardar_encerramento)
        else:self.root.destroy()


def main():
    root=tk.Tk()
    Aplicativo(root)
    root.mainloop()

if __name__=='__main__':main()
