# RPA SISREG v0.4 — Identificação e consulta hospitalar em lote

**Situação:** protótipo de homologação institucional. Não foi testado com login real pelo desenvolvedor; os XPaths e a interpretação da ficha devem ser conferidos pela Regulação/TI e pela operadora. Não altera solicitações do SISREG.

## Fluxo da Joice

1. **Arquivos:** selecione XLSX do hospital (abas `POA CIRURGICO`, `PT6`, `ALTA COMPLEXIDADE`) e, opcionalmente, PDF textual de espelho SIHD2. Clique **Executar conferência**. A AIH com e sem hífen é a mesma após normalização. O aplicativo verifica AIH e nome, localiza o CPF (quando realmente for CPF) e escreve valores faltantes na planilha hospitalar. A primeira alteração cria `*.backup_antes_RPA.xlsx`. Cronometra a operação e apresenta estimativa manual *apenas com a premissa informada* (padrão ilustrativo: 60 segundos/AIH).
2. **Cadastro SISREG:** faça login na janela local, confirme visualmente o acesso e inicie lote de 5, 20, 50 ou todos os elegíveis. O programa pesquisa CPF, tenta reconhecer CNS no resultado (inclusive formato `<td colspan="2"><font size="3"><b>...</b></font></td>`) e exige nome coincidente, CPF ainda na pesquisa e CNS único. Só CNS seguro é escrito na planilha. Se falhar, sinaliza e segue.
3. **Solicitações hospitalares:** com CNS, clique **Pesquisar solicitações hospitalares em lote**. O robô navega pelo menu de consulta hospitalar, pesquisa o CNS, procura a **AIH exata** em cada linha do resultado (não assume posição da linha), abre a ficha, confirma a mesma AIH e tenta extrair **caráter**, **código autorizador** e **procedimento solicitado**. Completa somente os campos F/G vazios; não substitui `numeroProcedimento` (coluna C). Procedimento diferente gera pendência com código solicitado numa coluna própria.

O XLSX é atualizado localmente, com backup, hash e salvamento atômico. O Excel deve permanecer **fechado** durante os lotes. O aplicativo não armazena senhas e não envia planilhas/PDF para a internet. Ele pode fazer consultas autorizadas ao SISREG, enviando os identificadores necessários, sem modificar solicitações.

## O que precisa de homologação no SISREG real

- O resultado de cadastro mostra CNS em negrito, mas isso não comprova sozinho a identidade. O sistema exige correspondência de nome e CPF pesquisado; resultados ambíguos não são gravados.
- O menu de solicitações hospitalares foi informado como `//*[@id="barraMenu"]/ul/li[5]/ul/li[1]/a` e a pesquisa por CNS usa `//*[@id="main_page"]/form/center[1]/table/tbody/tr[3]/td[2]/input` e `input[name="enviar"][onclick*="pesquisar"]`.
- A tabela pode ter várias solicitações. A AIH deve estar numa única linha antes de abrir. O programa **nunca** usa o índice fixo `tr[4]` para decidir qual solicitação abrir.
- Na ficha, os campos de caráter, autorizador e procedimento foram informados em `tr[44]/td[1]`, `tr[1]/td[1]/b` e `tr[48]/td[2]`. O programa exige que a AIH da ficha corresponda e que os valores sejam legíveis. Layout diferente = pendência.
- Nenhuma correspondência é atesto automático de faturamento ou autorização válida. Um procedimento diferente vira revisão.
- A pesquisa pelo CNS é **hospitalar** nesta etapa, e não ambulatorial. É necessária autorização institucional expressa antes de operar em produção.

## Compilar sem Python na SMS

O GitHub Actions `.github/workflows/compilar-windows.yml` instala dependências **somente no runner Windows**, executa `python -m unittest discover -s tests -v` e empacota `SISREG_Login.exe`. O artefato é `SISREG_Login_Windows`. A compilação deve ser verificada na aba Actions; testes locais não comprovam que o build Windows terminou.

Não coloque bases clínicas, senhas, documentos de usuários ou telas autenticadas no GitHub. Mantenha o repositório privado. O executável não é assinado e depende da aprovação da TI. Não desative as políticas do Windows.

## Recuperação e controle

O primeiro backup preserva a versão original da planilha. Se a planilha for modificada por outra pessoa durante a execução, o RPA interrompe o salvamento. Lotes de CNS e solicitações aceitam pausa; o arquivo é salvo em checkpoints. Os campos de auditoria adicionais indicam motivo, consulta hospitalar, procedimento visto no SISREG e tempo medido por AIH.

## Testes

```bash
python -m pip install -r requirements-build.txt
python -m unittest discover -s tests -v
```

Os testes são inteiramente fictícios e não executam login real. Concluir a homologação no PC da Joice com alguns registros **autorizados** antes de iniciar processamento de centenas de pessoas.
