# RPA SISREG — Conferência automatizada de internações

![Versão](https://img.shields.io/badge/vers%C3%A3o-0.7.6-07436b) ![Python](https://img.shields.io/badge/Python-3.12-3776AB) ![Licença](https://img.shields.io/badge/c%C3%B3digo-MIT-555555)

> **A máquina executa o trabalho repetitivo; o fiscal analisa as exceções e toma a decisão.**

Ferramenta desktop Windows, destinada ao apoio à fiscalização de internações declaradas
por prestador hospitalar. Lê XLSX e espelho de AIH em PDF, identifica CPF, pesquisa o
cadastro do paciente no **SISREG III** e confronta solicitação hospitalar com AIH,
caráter e procedimento. **Não aprova produção, não realiza atesto e não altera o SISREG.**

**Status:** protótipo em homologação. A utilização depende de autorização da
Regulação/TI e do perfil institucional adequado. Nenhum usuário deve inserir
credenciais ou pacientes reais no repositório ou pipeline de testes.

## Créditos e contato

- **Desenvolvimento:** Enf. Bruno Vinícius.
- **Coautoria:** Joice Correa Gomes e Heloisa Hoffmann.
- **Suporte técnico institucional:** bruno.vinicius@joinville.sc.gov.br.

A demanda surgiu da fiscalização de contrato, diante da necessidade de conferir
centenas de registros de internação enviados pelo hospital, antes pesquisados
manualmente em PDFs e no SISREG. O código pode ser reutilizado sob os termos de
[LICENSE](LICENSE), preservando os créditos e o aviso de copyright.

## Funcionalidades e fluxo (sem confirmações adicionais)

1. **Planilha e PDF:** carregar a planilha nas abas `POA CIRURGICO`, `PT6` e
   `ALTA COMPLEXIDADE`, além do PDF de espelhos. O motor confere AIH, nome e
   documentos sem substituir valores discordantes; informa completude e tempo.
2. **Cadastro no SISREG:** o usuário informa o login na janela local e o navegador
   acessa o domínio oficial. Após menu autenticado, os CPFs são consultados em
   lote e os CNS inequívocos preenchidos no XLSX de trabalho. Uma senha incorreta
   **não exige reiniciar o RPA nem a conferência do PDF**: basta tentar novamente.
   Quando todos os CNS elegíveis estiverem processados e a sessão continuar
   saudável, o programa **inicia automaticamente a etapa hospitalar** no mesmo
   navegador, sem solicitar clique adicional.
3. **Solicitações hospitalares:** busca CNS, localiza AIH exata e consulta ficha,
   código de solicitação/autorizador, procedimento e caráter. Ambiguidades e
   diferenças exigem análise humana. Os resultados aparecem durante a execução.
4. **Resultados:** painel gerencial, tempos observados, hipóteses manuais
   (15 s/AIH na etapa PDF e 10 s por consulta nas etapas SISREG), pendências
   e relatório TXT de diagnóstico para desenvolvedores.

A planilha hospitalar de entrada e o PDF são **somente leitura**. A cópia enriquecida
é gerada automaticamente sem apagar o original. Na estação de trabalho, mantenha
o Excel fechado enquanto o lote é processado.

## Retomada e resiliência (v0.7.5)

- **Reimportação de um XLSX produzido anteriormente:** escolha a última cópia
  de `Análises/` como entrada. O sistema cria uma **nova cópia** e preserva a
  anterior. CPFs preenchidos são aproveitados; CNS já presentes não são
  pesquisados novamente. Um registro previamente conferido na etapa hospitalar
  também pode ser preservado quando a própria planilha contém as evidências
  mínimas (CNS, caráter, código e situação anterior compatível).
- **Priorização:** são consultados registros que aguardam pesquisa ou tiveram
  falha técnica. Pendências antigas de identidade ou incompatibilidades ficam
  para análise humana e não são repetidas automaticamente.
- **Sessão saudável:** o RPA verifica periodicamente o menu autenticado; diante
  de falha de navegação pode realizar **até uma repetição controlada** da
  pesquisa, respeitando pausa e intervalo entre solicitações. Quatro respostas
  seguidas sem identidade confirmável ou três falhas técnicas provocam
  **suspensão conservadora**. Os últimos resultados inconclusivos não são
  gravados como ausência do paciente quando a sessão está degradada.
- **Retomar após suspensão:** os dados já confirmados são salvos; informe
  novamente usuário e senha na mesma janela do programa. A senha não é salva
  nem reutilizada silenciosamente. Quando autenticado, o sistema reconstrói a
  fila somente com o que ainda pode ser consultado.
- **Passagem automática da etapa 2 para a 3:** acontece apenas quando o lote de
  CNS termina sem suspensão e a planilha é salva. Casos pendentes de revisão
  humana não impedem consultar as AIHs dos demais pacientes já identificados.
- **Execução prolongada:** é possível manter a janela aberta enquanto trabalha,
  mas **não existe garantia de execução ininterrupta durante a noite**:
  indisponibilidade do SISREG, expiração de sessão, suspensão do Windows,
  política de bloqueio de estação e manutenção de rede podem exigir nova
  autenticação. Não contorne bloqueio de tela, MFA, regras de rede ou política
  de energia; alinhe a operação prolongada com a TI/Regulação.
- **Logs:** eventos de suspensão são enumerados e sem identificadores;
  nenhuma senha, nome, CPF, CNS, AIH nem HTML de resposta é gravado.

## Interrupção pelo CAPTCHA e retomada humana (v0.7.6)

- O SISREG pode exigir um teste **CAPTCHA/reCAPTCHA** após muitas requisições
  ou por outra política de acesso. O RPA **não resolve, contorna, oculta nem
  automatiza** essas verificações.
- Ao detectar o desafio, ou quando a sessão deixa de responder de forma
  confiável, o programa **pausa as consultas, preserva a planilha e mantém
  o Chrome/Edge aberto**. Uma janela de alerta informa a necessidade de
  intervenção e um botão discreto na etapa 2 permite confirmar a conclusão.
- Resolva a verificação **diretamente no site oficial do SISREG**. Depois
  pressione **Já concluí a verificação no SISREG**. O RPA verificará uma única
  vez se o menu autenticado está acessível. Caso não esteja, continuará
  aguardando, sem reenviar consultas ou credenciais automaticamente.
- Se a janela do navegador foi fechada, informe novamente usuário e senha no
  próprio RPA para iniciar outra sessão. Os CPFs/CNS já gravados na cópia de
  trabalho não são descartados.
- Os indicadores diferenciam **CNS acumulados no XLSX** de **consultas desta
  retomada**. Por exemplo, 375 CNS identificados no total e 10/355 consultas
  realizadas no novo lote são grandezas diferentes; não houve perda de dados.
- Quando a sessão for comprovadamente recuperada, somente as consultas que
  permanecem elegíveis serão retomadas. A passagem automática para a consulta
  hospitalar continua condicionada ao término e salvamento seguro da etapa 2.
- Uma proteção de acesso **não é um erro técnico a ser superado com retries**.
  O RPA não tenta contornar o CAPTCHA, alterar características do navegador,
  trocar IP/conta, automatizar sua resolução nem distribuir requisições para
  disfarçar limites. O ritmo e os limites autorizados devem ser alinhados à
  Regulação/TI e ao operador do SISREG. O acesso pode voltar a ser exigido mesmo
  após a verificação humana.
- **Execução noturna:** o processamento só avança enquanto a sessão estiver
  apta e a estação autorizada. Se houver CAPTCHA, pausa e aguarda a pessoa;
  nunca é garantida execução integral sem supervisão. Não contorne as políticas
  de bloqueio de tela, energia ou expiração de sessão do ambiente institucional.

**Eventos técnicos seguros:** `VERIFICACAO_HUMANA_EXIGIDA`,
`VERIFICACAO_CONFIRMADA_OPERADOR` e `SESSAO_RECUPERADA`. O TXT e o histórico
registram apenas operações e contagens. Não capturam os dados do desafio,
credenciais, nomes, CPF, CNS, AIH ou HTML.

## Layout da planilha enriquecida

A:G preservam as colunas do modelo hospitalar, inclusive `codigoAutorizador`
(G), que recebe o Código Solicitação do SISREG quando vazio e com AIH exata.
H:J contêm somente `rpaSituacao`, `rpaAtualizadoEm` e
`rpaProcedimentoSISREG`. A coluna K redundante foi retirada. O RPA reconhece
e migra o layout H:K das versões anteriores, preservando em G um código
legado de K quando G estiver vazia, sem alterar valores preexistentes de A:G e sem apagar
campos adicionais desconhecidos do hospital.

## Pasta de instalação e saídas (Windows)

Descompacte o artefato do GitHub Actions em uma pasta de sua escolha e execute
**`RPA_SISREG.exe`**. O Python não precisa estar instalado na estação.

```text
RPA_SISREG/
├── RPA_SISREG.exe
├── SHA256.txt
├── Análises/
│   ├── Planilha_RPA_DDMMAAAA_HHMMSS.xlsx
│   └── Planilha_RPA_DDMMAAAA_HHMMSS_2.xlsx
└── Logs/
    ├── RELATORIO_TECNICO_RPA_DDMMAAAA_HHMMSS.txt
    ├── RELATORIO_TECNICO_RPA_FALHA_DDMMAAAA_HHMMSS.txt
    ├── execucao_<id>.json
    └── eventos_seguros.jsonl
```

`Análises/` e `Logs/` são criadas automaticamente **ao lado do executável**,
nunca ao lado da planilha recebida. O TXT de falha também vai para `Logs/`, mesmo
quando o processo não chega à etapa 2. Se o diretório for protegido para escrita
pela TI, o programa **não desvia silenciosamente** os resultados para outro
local: solicite autorização de escrita em pasta institucional apropriada.

**Privacidade:** arquivos dentro de `Análises/` têm dados de pacientes e exigem
ACL, retenção e descarte aprovados pela instituição. `Logs/` registra apenas
códigos de operação, durações, ordinais, versão, hashes e contagens; não inclui
CPF, CNS, AIH completa, nomes, senhas, cookies nem HTML de páginas. A segurança
do diretório é responsabilidade da instituição; o app não criptografa o XLSX.

## Requisitos

- Windows 10/11, navegador Microsoft Edge ou Google Chrome instalado e autorizado.
- Acesso à rede institucional e ao SISREG III com conta/perfil habilitado.
- Permissão de **leitura** na pasta dos arquivos de origem e **escrita** na pasta
  do executável, para criar `Análises/` e `Logs/`.
- Execução de programas PyInstaller permitida pela TI; **não** desabilitar
  SmartScreen, EDR, antivírus, proxy ou autenticação adicional.

## Instalação e compilação

Para operadores: acesse **GitHub → Actions → Compilar RPA SISREG para Windows**;
após o job verde, faça download do artefato **`RPA_SISREG_Windows`** e extraia
`RPA_SISREG.exe` e `SHA256.txt`. Verifique o SHA-256 antes de distribuir.

Para desenvolvedores, use Python 3.12 em Windows autorizado:

```powershell
python -m pip install -r requirements-build.txt
python -m unittest discover -s tests -v
powershell -File .\compilar_windows.ps1
```

O workflow `.github/workflows/compilar-windows.yml` executa testes exclusivamente
com pacientes e páginas SISREG **fictícios**, gera metadados de versão e compila
com PyInstaller. **Não incluir dados reais em testes, issues, commits, GitHub
Actions ou exemplos de documentação.** Uma execução de CI aprovada não
substitui homologação na estação institucional.

## Projeto técnico

| Componente | Responsabilidade |
|---|---|
| `src/sisreg_login.py` | Interface Tkinter, sessões de navegador, orquestração em lote |
| `src/aih_extract.py`, `src/planilha.py` | Leitura, normalização, validação AIH–espelho |
| `src/sisreg_navigation.py` | Cadastro CPF→CNS, restrição a HTTPS oficial |
| `src/sisreg_hospital.py` | Consulta hospitalar pela AIH, leitura segura da ficha |
| `src/persistencia.py`, `src/saida_xlsx.py` | Hashes, gravação atômica, integridade e formatação XLSX |
| `src/diretorios.py` | Caminhos `Análises/` e `Logs/` relativos ao EXE |
| `src/estatisticas.py`, `src/governanca.py` | Métricas, log sanitizado e histórico administrativo |
| `src/app_info.py`, `scripts/preparar_compilacao.py` | Versão central e metadados Windows |

A navegação não contorna CAPTCHA/MFA; pesquisa apenas dentro do SISREG
institucional, sem transmitir dados clínicos a serviços externos. Seletores
podem mudar e a extração depende das permissões da conta e da interface real.
Números de AIH e CNS não são usados como autorização para decisões fiscais.

## Tratamento de falhas e testes

- **Senha incorreta:** aguarde a mensagem de falha; digite novamente e clique
  **Abrir SISREG e entrar**. O programa libera uma sessão nova e preserva a
  planilha preparada. Fechar somente a janela do navegador também permite nova
  tentativa na mesma interface do RPA.
- **Arquivo XLSX em uso/alterado:** feche o Excel e corrija a divergência.
  O salvamento usa arquivo temporário, verificação SHA-256 e `os.replace`.
- **Campos/AIH não encontrados:** ficam pendentes de revisão; o programa não
  escolhe registro ambíguo nem inventa autorização.
- **Falha na preparação:** consulte o TXT na pasta `Logs/`. Não use uma cópia
  incompleta como resultado.
- **Pasta sem permissão:** verifique autorização da TI para criar os diretórios
  perto do executável; não execute como administrador para burlar política.

Teste completo: `python -m unittest discover -s tests -v` (somente dados
sintéticos). Homologue também 5 AIHs autorizadas, comparando Excel e tela,
verificando logs e recuperação de login. Os testes de UI requerem ambiente
gráfico com `SISREG_GUI_TEST=1`. Revise `CHANGELOG.md` e `RELATORIO_TESTES_v074.md`.

## Segurança e licença

A política de divulgação responsável, LGPD, limites de automação, arquitetura
sem telemetria e responsabilidades de segurança está em [SECURITY.md](SECURITY.md).
O **código** está licenciado sob [MIT](LICENSE): cópia, modificação e reprodução
são permitidas com manutenção do aviso de copyright e licença. **Não** se
licenciam aqui bases de pacientes, dados SISREG, logos, imagens, brasão municipal
ou marcas do Ministério da Saúde/SUS, nem se concede autorização institucional
para automação pela mera distribuição do software.

O desenvolvimento do RPA não transforma dados coletados em produção aprovada:
**a decisão fiscal pertence ao servidor competente.**
