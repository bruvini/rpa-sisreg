# RPA SISREG — v0.3 · CPF e CNS em lote

**Protótipo de homologação institucional — acesso ao SISREG exclusivamente por conta autorizada pela Regulação/TI.** O robô faz apenas consultas, não insere nem altera solicitações. Não armazena senhas.

## O que foi implementado

1. **Planilha hospitalar como arquivo de trabalho:** lê `POA CIRURGICO`, `PT6`, `ALTA COMPLEXIDADE`, com cabeçalho fixo `nomePaciente, numeroAIH, numeroProcedimento, numeroCPF, numeroCNS, caraterInternacao, codigoAutorizador` nas colunas A:G.
2. **PDF em lote:** indexa o espelho por AIH; ignora hífen do dígito verificador (`9000000000123` = `900000000012-3`). Só associa identificador se **AIH e nome** corresponderem e não houver duplicidade conflitante. Distingue CPF (11 dígitos, dígitos verificadores válidos) de CNS (15 dígitos). A extração não faz OCR.
3. **Gravação na própria XLSX:** ao clicar **Preparar e atualizar CPFs na planilha**, preenche automaticamente **somente células vazias verificadas** e registra situação/observação em H:L. Preserva A:G e as 3 abas. Cria um backup `NOME.backup_antes_RPA.xlsx` **antes da primeira alteração**. A gravação usa temporário e substituição atômica, confirmando hash para evitar sobrescrita de alterações externas. Planilha precisa estar fechada no Excel.
4. **Login SISREG:** abre Chrome/Edge, envia login à origem oficial por HTTPS, sem salvar credenciais, e tenta identificar automaticamente o menu da página inicial. Caso haja CAPTCHA/MFA, a operadora conclui manualmente.
5. **Pesquisa de cadastro CPF → CNS em lote:** use **Iniciar pesquisa dos CNS em lote** com 5, 20, 50 ou todos. O robô procura um cadastro por CPF usando o menu `Solicitar → Ambulatorial` e o botão real `input[name="btn_pesquisar"][onclick*="pesquisarPaciente"]`; aguarda resultado e **somente associa CNS se detectar um nome exato e um único CNS explicitamente rotulado**. Se houver ambiguidade, não grava um CNS e passa à próxima AIH. Uma sequência de 3 erros de navegação suspende o lote.
6. **Salvamentos periódicos:** faz checkpoints a cada 10 consultas e ao encerrar, com opções Pausar/Retomar/Interromper; mantém backup original. Se outra pessoa alterar a XLSX ou ela estiver bloqueada, suspende e sinaliza falha.
7. **Próxima etapa mantida separada:** a consulta `Consulta Amb → Solicitações` **não é executada nesta versão**, conforme solicitado.

## Como testar com segurança

1. Em pasta institucional autorizada, faça uma **cópia de teste** da planilha real e mantenha o PDF local. Não coloque dados reais no GitHub.
2. Feche o XLSX no Excel, execute o EXE e, na aba 1, escolha XLSX e PDF. Clique **Preparar e atualizar CPFs na planilha**. Confira CPFs, situações e backup diretamente no XLSX.
3. Na aba 2, entre com o login autorizado. Verifique se a página principal do SISREG abriu e se o robô reconheceu o menu. Caso necessário, marque a confirmação manual do acesso.
4. Comece com **lote de 5 pacientes fictícios ou registros reais de homologação expressamente autorizados**. Confira cada CNS registrado. Se não for possível extrair dados da tela com segurança, a coluna E **permanece vazia**, com uma pendência explicativa.
5. Quando a pesquisa e as decisões estiverem corretas, amplie para 20/50/todos, respeitando os limites operacionais definidos pela TI. O robô não contorna limites, CAPTCHA ou bloqueios do sistema.
6. Se interromper, abra novamente o mesmo XLSX e prepare-o; CNS existentes não serão duplicados nem substituídos.

### O que ainda depende da tela real

O XPath fornecido para o **botão Pesquisar** foi incorporado pelo nome/`onclick`, mas **não foi fornecido um DOM validado da página após a consulta**. A v0.3 tenta ler somente resultados etiquetados como `Nome`, `CPF` e `CNS`, inclusive quando aparecem em campos visíveis de formulário. **Não é possível garantir captura de CNS na instalação real sem homologar esses seletores**. Em caso de dúvida, registra pendência e segue em lote. Nunca interpreta ausência/erro como inexistência de cadastro.

Se as colunas de CNS continuarem vazias, forneça **somente um recorte não identificável da estrutura da página de resultado (HTML sem valores pessoais, com `id`, `name` e etiquetas)** para ajustar o extrator. **Não forneça senha, cookies, tokens ou arquivos com dados reais ao repositório.**

## Segurança, atualização e recuperação

- Backup: fica na **mesma pasta protegida** da planilha, com os mesmos controles de acesso institucionais. Caso algo inesperado ocorra, feche o programa e recupere a cópia `*.backup_antes_RPA.xlsx`.
- Não salvamos senhas, screenshots, HTML ou prontuários no GitHub. O programa processa informações somente na estação institucional.
- O arquivo XLSX contém dados sensíveis e **não recebe criptografia automática**. A política de armazenamento/retensão depende da SMS.
- A rotina lê somente telas oficiais do SISREG; não altera solicitações nem ultrapassa mecanismos de controle de acesso.
- O EXE é não assinado. Caso bloqueado na estação, solicite liberação pela TI, **sem desativar antivírus ou contornar políticas**.
- O estado de homologação é **pendente**: testes automatizados são sintéticos, sem login real ou validação de layout pós-pesquisa.

## Compilação no Windows sem instalar Python na estação da Joice

GitHub Actions → **Compilar RPA SISREG para Windows** → execução da `main` → **Artifacts → SISREG_Login_Windows**. O runner Windows usa Python 3.12 + PyInstaller; a estação institucional usa somente o `.exe` e o Chrome/Edge existente.

## Testes

`python -m unittest discover -s tests -v`

33 testes automatizados em 19/10/2026: extração, normalização, identidade, escrita segura, preservação de backup, divergência CPF/CNS e navegação simulada. Testes no SISREG real continuam pendentes de autorização e homologação.
