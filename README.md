# SISREG III — Login assistido (protótipo 0.1.0)

**Objetivo:** testar somente a abertura do SISREG III e o preenchimento autorizado do formulário de autenticação em um navegador visível. Este projeto **não pesquisa pacientes, não acessa AIHs e não modifica solicitações**.

## O que a janelinha faz

1. Solicita **usuário**, **senha** e navegador (**Microsoft Edge** ou **Google Chrome**).
2. Abre `https://sisregiii.saude.gov.br/` em uma sessão nova, visível e temporária do navegador já instalado.
3. Confirma que a página continua no host HTTPS oficial antes de inserir credenciais.
4. Aguarda os três controles identificados pelos XPaths informados em 19/10/2026:
   - Usuário: `/html/body/div[1]/div/div[4]/form/div/div[1]/div[1]/div[2]/input`
   - Senha: `/html/body/div[1]/div/div[4]/form/div/div[1]/div[1]/div[5]/input`
   - Botão: `/html/body/div[1]/div/div[4]/form/div/div[1]/div[1]/div[8]/input`
5. Preenche os dois campos e aciona o botão. **A confirmação de que o login foi aceito deve ser feita pela pessoa operadora no navegador.**
6. Mantém a janela aberta enquanto o aplicativo estiver em execução. Encerrar o programa fecha o navegador automatizado.

## Segurança e limitações

- **Não executar sem autorização da Regulação e da TI.** A existência de RPA anterior não equivale a autorização para um novo robô.
- O programa **não armazena senha em arquivo, log, cookie persistente, registro do Windows ou localStorage**. As credenciais são mantidas transitoriamente na memória do processo apenas para envio ao endereço oficial. Como em qualquer programa, não existe garantia de sobrescrita física da memória RAM.
- Não introduzir credenciais em repositórios, CI ou arquivos de teste. A compilação na nuvem **não recebe contas/senhas de produção**.
- Não contorna CAPTCHA, MFA, bloqueios ou controles de acesso. Se o site exigir etapa manual, concluir no navegador.
- Os XPaths podem mudar sem aviso. Se o formulário divergir do esperado, o robô **não deve** preencher a senha.
- O EXE gerado é **não assinado**. A política de aplicações da prefeitura pode impedir sua execução; nesse caso, solicitar avaliação/assinatura ou instalação assistida à TI — **não desabilitar antivírus ou políticas de segurança**.
- Não foi efetuado login no portal real durante o desenvolvimento. Testes feitos com páginas simuladas e verificações do código, sem dados de produção.

## Como obter o EXE sem instalar Python no computador da SMS

Este pacote inclui os fontes e uma **rotina de compilação automática em Windows via GitHub Actions**. A compilação precisa ocorrer em Windows; o ambiente no qual este pacote foi produzido não é Windows, então **não há um `.exe` pré-compilado no ZIP**.

1. Em uma conta GitHub autorizada, crie um **repositório privado** para o protótipo. Não envie planilhas hospitalares, credenciais ou arquivos de pacientes.
2. Extraia este ZIP e adicione ao repositório os arquivos e as pastas, incluindo `.github/workflows/compilar-windows.yml`.
3. Ao enviar os arquivos à branch `main`, a compilação inicia automaticamente. Se preferir, abra **Actions → Compilar login SISREG para Windows → Run workflow**.
4. Quando a execução terminar com sucesso, abra a execução e baixe o artefato **SISREG_Login_Windows**.
5. Extraia o ZIP do artefato; ele contém `SISREG_Login.exe` e `SHA256.txt`.
6. Peça à TI a aprovação do executável na estação institucional, antes de usar uma conta real.
7. Abra o executável, escolha Edge ou Chrome e teste as credenciais **diretamente no aplicativo local**, nunca no GitHub.

> O EXE gerado pelo PyInstaller contém Python, Playwright e suas dependências, mas **usa o Edge ou Chrome já instalado**. Ele não precisa de Python instalado na estação de uso. A primeira execução pode demorar devido à extração do pacote único.

### Compilação alternativa em máquina Windows de desenvolvimento autorizada

Em um Windows que já possua Python e acesso à internet para dependências, abra PowerShell na raiz do projeto e execute:

```powershell
powershell -ExecutionPolicy RemoteSigned -File .\compilar_windows.ps1
```

O resultado será `dist\SISREG_Login.exe`. **Não altere a política de execução do computador institucional para contornar restrições impostas pela TI.**

## Testes

```bash
python -m unittest discover -s tests -v
```

Testes de unidade sem acessar o SISREG: validação da origem HTTPS, tipos dos campos, preenchimento e clique, recusa de páginas indevidas. **Uma homologação no computador institucional continua necessária** para comprovar funcionamento real do login.

## Próxima etapa (fora do escopo deste protótipo)

Somente após autorização e confirmação do login: pesquisa individual por AIH/CNS, comparação de dados, integração com o Conferidor SISREG e relatório de execução. Nenhum desses recursos foi incluído nesta versão.
