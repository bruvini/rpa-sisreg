# RPA SISREG · Conferência de internações (v0.6.1)

**Estado:** protótipo institucional em homologação. A publicação de código não significa autorização da Regulação ou da TI para automação em produção. Não é um sistema de atesto ou decisão fiscal.

> **Princípio:** a máquina executa o trabalho repetitivo; o fiscal analisa as exceções e toma a decisão.

### Ajustes operacionais v0.6.1

A preparação apresenta registros e CPFs progressivamente, assim que o PDF termina de ser indexado. A primeira tabela mostra apenas os dados da etapa 1 e utiliza situações legíveis. O botão **Próxima etapa** no rodapé fica disponível ao concluir a preparação. A etapa 2 tem tabela própria que atualiza CNS e situação para cada consulta terminada. A fonte recebida segue intacta; a cópia gerada chama-se `Planilha_RPA_DDMMAAAA_HHMMSS.xlsx`, com sufixo se houver duplicata.

O resultado cadastral pode ser aberto pelo SISREG em uma segunda janela. A captura agora procura páginas oficiais abertas na sessão, sem aceitar páginas externas e sem presumir identidade pelo CPF de busca isolado. São necessários nome compatível e CNS único; nomes não confirmados ficam pendentes. Os campos e regras da terceira etapa não mudaram. A ausência de CNS no Excel após o teste real requer inspeção da estrutura da página de resultado pela equipe autorizada, sem publicar prints contendo dados de pacientes.

## Finalidade e origem

A ferramenta surgiu de demanda da equipe de fiscalização contratual da SMS para reduzir atividades manuais de pesquisa de centenas de internações informadas pelo prestador hospitalar. Atua como apoio: localiza AIHs nos espelhos, extrai identificadores quando inequivocamente correspondentes, consulta o SISREG de forma somente leitura e destaca pendências. **Concluir uma consulta automática não significa aprovação, regularidade da produção ou atesto.** Divergências e decisões permanecem com o fiscal.

## Fluxo existente preservado

1. **Planilha e PDF:** escolha o XLSX com as três abas `POA CIRURGICO`, `PT6` e `ALTA COMPLEXIDADE`, e opcionalmente o espelho PDF. Clique **Executar conferência**. O RPA cruza AIH, nome e documento, mostra contagem e tempo com referência manual de 15 s/AIH (hipótese, não medição).
2. **Consulta cadastral:** forneça credenciais somente na janela local do RPA, que abre Chrome ou Edge no domínio oficial do SISREG. Após detecção do menu de sessão autenticada, a consulta em lote pesquisa CPFs elegíveis; apenas CNS sem conflito e com identidade confirmável entram na planilha. Erros tornam-se pendências.
3. **Consulta hospitalar:** após a etapa cadastral, acione a pesquisa em lote das solicitações hospitalares. O robô procura a **AIH exata**, compara campos disponíveis e registra código autorizador e caráter apenas quando identificados com segurança. Procedimentos diferentes são encaminhados à análise.

A etapa 3 **não** atesta procedimentos, não altera solicitações no SISREG e depende da homologação de seletores reais e permissões da conta.

## Alteração de segurança v0.6: planilha original intocada

Ao preparar, o RPA lê o **XLSX selecionado somente para leitura** e cria automaticamente, na mesma pasta institucional, um arquivo `Planilha_RPA_DDMMAAAA_HHMMSS.xlsx` (sufixo numérico, se necessário). **Todos os CPFs, CNS, caráters e autorizadores enriquecidos passam a ser salvos nesse arquivo de trabalho**. Nenhuma confirmação adicional é pedida. O XLSX recebido e o PDF nunca são editados/excluídos. O controle SHA-256 detecta se o arquivo de trabalho foi alterado externamente. Caso precise retomar em outro dia, selecione uma cópia de trabalho existente, que gerará outra versão sem destruir a anterior. Backup antigo e arquivos existentes não são apagados pelo RPA.

A planilha enriquecida mantém as colunas originais e as colunas de rastreabilidade dentro do próprio XLSX, sob controles de armazenamento da instituição. **Não compartilhe esse arquivo por GitHub, issue ou ferramenta de IA.**

## Sobre a ferramenta

O botão discreto **ⓘ Sobre** no cabeçalho explica demanda, processo, categorias de dados (nome, AIH, CPF, CNS, procedimento e dados administrativos), proteção local, versão e responsabilidade humana. É informativo e não adiciona etapa operacional.

## Proteção das credenciais

- Usuário/senha ficam em campos Tkinter locais e são apagados dos widgets assim que o acesso é iniciado; cópias de strings na memória são transitórias e não há garantia de limpeza física de RAM no Python.
- Login é preenchido exclusivamente em `https://sisregiii.saude.gov.br/` com checagem de HTTPS/hostname. O navegador usa contexto novo sem diretório de perfil persistente configurado e downloads desabilitados.
- Não são armazenadas em TXT, JSON, banco, log, relatório, GitHub, GitHub Actions, telemetria nem serviços de terceiros. Não há salvamento de cookies/sessões.
- Erros de autenticação são exibidos de forma genérica. CAPTCHA e MFA não são contornados. O RPA encerra o navegador ao fechar a aplicação.
- O pacote é **não assinado digitalmente**. A TI deve homologar e, se necessário, assinar e liberar o aplicativo sem reduzir proteções institucionais.

## Dados pessoais e rede

A leitura de PDF/XLSX é local. O único destino externo operacional previsto é o **SISREG oficial**, acessado pelo navegador autorizado; não há APIs de IA, análise de uso, crash reporting, GitHub ou telemetria na execução. O HTML do SISREG e os dados pessoais não são capturados em logs locais. Dependências instaladas no **ambiente de compilação** são baixadas por `pip`/GitHub Actions; isso não envia dados hospitalares (não são distribuídos ao CI).

Nunca carregar dados reais em ambiente não homologado. CPFs/CNS em relatórios e no arquivo de trabalho são **dados pessoais protegidos**; a pasta de saída é responsabilidade da unidade e precisa de controle de acesso/retensão.

## Histórico técnico e logs (sem dados individuais)

O RPA registra automaticamente em `%LOCALAPPDATA%\RPA_SISREG` (Windows) ou `~/.local/state/RPA_SISREG` (Linux de desenvolvimento):

- `execucao_<id>.json`: identificador aleatório; início, término, versão, status, duração; nome resumido e SHA-256 do XLSX/PDF de origem; números de registros, consultas, pendências, erros.
- `eventos_seguros.jsonl`: data/hora UTC, ID de execução, etapa, evento de lista fechada e número **ordinal** de registro, quando informado.

**O histórico não contém nomes de pacientes, AIH, CPF, CNS, procedimento, senha, cookie, resultado clínico ou conteúdo de páginas.** Não grava nomes de caminhos completos. Nomes de arquivos potencialmente identificadores numéricos são mascarados; ainda assim, evite nomes de arquivos com nomes de pessoas. Os dados do histórico **não são enviados automaticamente**.

Quando o processo termina normalmente, é marcado `CONCLUIDA`; erros e interrupções podem ser marcados `FALHA_TECNICA`/`INTERROMPIDA`. Se o programa encerrar abruptamente, o último snapshot permanece com `EM_ANDAMENTO`. Uma conclusão automática nunca indica atesto fiscal.

## Temporários

- A rotina de Excel cria `.rpa_sisreg_*.xlsx` **na pasta do arquivo de trabalho** e remove-o no `finally`, inclusive quando há exceção durante salvamento. `os.replace` faz a troca atômica.
- Ao escolher o XLSX, o RPA remove **somente** `.rpa_sisreg_*.xlsx` com mais de 48 horas no diretório selecionado. Não remove arquivos originais, backups, cópias de trabalho nem itens recentes, protegendo outras instâncias.
- Snapshots `.historico_*.tmp` são retirados no `finally`. Resíduos com mais de 48 horas são removidos ao abrir novo histórico.
- Perfil temporário do Chromium/Edge/Chrome e extração `_MEI*` do PyInstaller são gerenciados pelas bibliotecas/sistema operacional. Após interrupção abrupta ou desligamento forçado podem sobrar resíduos fora do escopo seguro de limpeza do RPA. **Não executamos limpeza genérica em diretórios do Windows.**

## Erros e relatórios

Mensagens no aplicativo são breves e não incluem `str(exception)` não filtrado. Eventos técnicos aceitam somente códigos enumerados, nunca mensagens livres ou stack traces. A consulta sem confirmação não preenche campos automaticamente. A planilha de trabalho contém estados de extração; `DADOS_COLETADOS_SEM_DIVERGENCIA` significa **ausência de divergência identificável pelos campos consultados**, não regularidade fiscal.

Na etapa 3, existe **Exportar somente pendências (XLSX)** opcional. Contém apenas aba, linha, AIH, código do motivo e indicação `REVISÃO PENDENTE`, sem CPF, CNS ou nome. Esse arquivo ainda deve ficar em pasta institucional porque contém AIH; não possui criptografia nativa.

## Compilação Windows

O arquivo `.github/workflows/compilar-windows.yml` constrói no GitHub Actions com dependências fixadas em `requirements-build.txt`, sem dados reais. O workflow executa testes, gera `src/build_info.py` com data UTC da compilação e `versao_windows.txt` com recurso de versão Windows, depois compila `dist/SISREG_Login.exe` via PyInstaller. O EXE mostra `0.6.1` na interface e metadados de versão nas propriedades do arquivo.

Para compilar em Windows *autorizado* com Python de desenvolvimento, use `powershell -File .\compilar_windows.ps1`. A estação da Joice não precisa de Python. O workflow produz o artefato **SISREG_Login_Windows** com `SISREG_Login.exe` e SHA-256 para comparação.

Executar a aplicação na estação da SMS exige autorização, compatibilidade com o navegador e homologação real das telas do SISREG. Não há credenciais ou dados pessoais no processo de compilação.

## Testes e limitações

`python -m unittest discover -s tests -v` usa apenas PDFs/planilhas e telas **fictícios**, sem conectar ao SISREG real. Abrange regras das versões anteriores, SHA-256, original intacto, cópia de trabalho, logs sanitizados, limpeza seletiva, histórico, versão e exportação mínima. Execute também a homologação com cinco AIHs autorizadas no computador institucional; os testes sintéticos não provam correspondência da estrutura real.

**Não utilizar dados reais de pacientes em testes, issues, commits, GitHub Actions ou exemplos de documentação.** Não desativar antivírus, proteções de rede ou controles de acesso para fazer funcionar. O histórico administrativo não substitui log de auditoria autenticado/inviolável; caso se exija custódia institucional, a TI deve aprovar armazenamento protegido, retenção e ACLs.
