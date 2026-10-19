# RPA SISREG — Preparação e consulta assistida v0.2

**Status:** protótipo de homologação, não aprovado para produção. **Não** faz extração de solicitações ambulatoriais nem captura automaticamente CNS/nome da página de resultados. A execução no SISREG real exige autorização da Regulação e TI.

## O que já funciona

1. Importa o XLSX padronizado do hospital, com **exatamente** as abas `POA CIRURGICO`, `PT6` e `ALTA COMPLEXIDADE`, e os sete cabeçalhos informados na linha 1.
2. Aceita espelho de AIH em PDF **textual/pesquisável**, opcional. Indexa as AIHs uma única vez e trata `4226500330294` = `422650033029-4` (número de 13 dígitos).
3. Confere **AIH e nome** antes de anexar documentos do PDF. `CNS/CPF` com CPF válido (11 dígitos) é tratado como CPF; documento de 15 dígitos é tratado como CNS. Se houver divergência, identificador inválido, espelhos conflitantes ou campo ausente, não preenche silenciosamente.
4. Abre o Edge/Chrome, faz login com usuário e senha da sessão local, mas **não salva credenciais**. A operadora confirma que o login foi aceito.
5. Para uma AIH selecionada, navega pelo menu **Ambulatorial** e pesquisa o cadastro por CPF ou CNS.
6. A operadora **confere visualmente o nome** e informa/valida o CNS com 15 dígitos. O robô não afirma ter lido o CNS da página: os XPaths enviados para nome/CNS coincidem com o botão de pesquisa e não são seletores de resultado comprovados.
7. Após essa confirmação, navega em **Consulta Amb → Solicitações**, informa o CNS e aciona a pesquisa. **Para aí**; a lista resultante não é coletada nem interpretada.
8. Gera uma **nova cópia XLSX**, preservando as abas, as sete colunas e o arquivo original; registra situação, detalhe, página do PDF, pesquisa aberta e horário. Não atesta solicitação nem autenticidade.

## Como operar (estação de homologação)

1. Abra `SISREG_Login.exe` e entre na aba **1 Arquivos e AIHs**.
2. Escolha a planilha XLSX e, se existir, o espelho PDF. Clique **Preparar conferência**.
3. Selecione uma linha e entre em **2 Consulta SISREG**.
4. Informe usuário/senha **somente no aplicativo local**, escolha Edge ou Chrome, abra o SISREG e confirme no próprio navegador que o login funcionou.
5. Clique **Pesquisar cadastro do paciente**. Confirme visualmente o paciente no SISREG, digite o CNS visto e marque a confirmação de identidade; clique **Confirmar CNS**.
6. Clique **Pesquisar solicitações pelo CNS**. O navegador abre a pesquisa, sem classificar seus resultados.
7. Ao finalizar ou pausar, abra **3 Planilha de saída** e salve uma cópia XLSX em pasta institucional autorizada.

## Limitações que não foram ocultadas

- **Não foi fornecido o PDF real**, apenas uma captura de tela do espelho. O parser foi testado contra PDF **fictício textual**, mas o PDF SIHD2 real ainda precisa ser homologado. Se o PDF for imagem, a versão não tenta OCR.
- Os XPaths de SISREG foram fornecidos para esta tela; são **provisórios** e devem ser testados na sessão autorizada. Se a estrutura mudar, a automação para sem insistir.
- Os XPaths informados para o CNS/nome na tela de resultado são **iguais ao botão de pesquisa**; por isso o CNS não é capturado automaticamente nesta versão.
- A pesquisa de solicitações é **ambulatorial**, não a consulta de internações/AIHs. Apenas abrir a pesquisa não confirma a existência de solicitação correspondente à AIH.
- A segurança de PDF/planilha depende também do diretório de salvamento e dos controles institucionais. O XLSX **não é criptografado automaticamente**.
- Não há automação em lote, sincronização em rede, armazenamento de senha, contorno de CAPTCHA/MFA ou alteração do SISREG.
- O robô não compara CPF/CNS de forma definitiva caso não haja campos SISREG confirmados.

## Compilar EXE sem instalar Python no computador da SMS

O repositório contém o workflow `.github/workflows/compilar-windows.yml` para compilar num runner Windows do GitHub Actions, usando PyInstaller. Ele executa testes sintéticos antes do empacotamento e publica um artefato `SISREG_Login_Windows` com `SISREG_Login.exe` e `SHA256.txt`. Também é possível compilar em uma estação Windows autorizada com `compilar_windows.ps1`.

A TI deve avaliar e autorizar a execução do programa não assinado. **Não desative antivírus nem políticas de segurança** para executá-lo. O navegador Edge/Chrome precisa estar instalado e liberado.

Não coloque credenciais, planilhas com dados reais, PDFs com informações de pacientes ou relatórios no GitHub, inclusive no repositório privado. O código-fonte utiliza somente dados sintéticos nos testes.

## Dependências do ambiente de compilação

- Python 3.12 no **runner de compilação**, não na estação SMS
- Playwright + PyInstaller
- PyMuPDF para PDF textual
- openpyxl para entrada e geração de cópia XLSX

## Testes

```sh
python -m pip install -r requirements-build.txt
python -m unittest discover -s tests -v
```

Os 24 cenários incluem seleção por AIH com/sem hífen, PDF textual sintético, conflitos e duplicidades, CPF válido/inválido, XLSX padrão, preservação do original, navegação SISREG simulada e verificações de origem/credenciais. **Não equivalem a um teste de acesso real ao SISREG**.
