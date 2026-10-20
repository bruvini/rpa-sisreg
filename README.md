# RPA SISREG · Conferência de internações (v0.7.3)

**Homologação institucional:** a automação coleta dados e evidencia pendências; a decisão sobre atesto pertence ao fiscal. As pesquisas no SISREG continuam iguais às da v0.7.1.

### Atualização v0.7.3 — planilha de entrega e ícone

- O XLSX conserva as sete colunas do modelo hospitalar e exporta somente **H:K**: `rpaSituacao`, `rpaAtualizadoEm`, `rpaProcedimentoSISREG` e `rpaNumeroSolicitacao`. Campos técnicos adicionais não são exportados; logs técnicos permanecem separados e sem dados pessoais.
- **H** mostra a situação final legível, distinguindo ausência no espelho, divergência no PDF, ausência/divergência cadastral, AIH não identificada, divergência hospitalar e **Consulta sem divergências**. Casos com erro ou consulta inacabada são apresentados como revisão pendente, nunca como ausência confirmada.
- **I** é uma data/hora real do Excel, com formato `DD/MM/AAAA HH:MM:SS`, evitando um texto ISO não formatado.
- **J** mostra `Compatível`, `Divergente` ou `Não conferido` conforme comparação de dois códigos de procedimento de 10 dígitos. Não considera um campo vazio como conformidade.
- **K** mantém o número da solicitação extraído da ficha após confirmação da AIH.
- **G (`codigoAutorizador`)**: a pedido da operação, quando está vazia e há ficha exata, recebe o **Código Solicitação** da ficha como identificador operacional. Trata-se de um mapeamento solicitado, **não de prova de um código autorizador independente**. Se G já estiver preenchida, seu valor nunca é substituído. Há comentário de procedência no cabeçalho. A duplicação em G/K é intencional para compatibilidade com o modelo existente.
- Novas colunas têm formatação, filtros, congelamento do cabeçalho e extensão das **Tabelas do Excel** do modelo original para A:K. Ao migrar esquema legado H:P, a rotina remove somente colunas reconhecidas; rejeita colunas extras desconhecidas para evitar perda de dados.
- O novo ícone do executável utiliza um **recorte ampliado da letra S do logotipo fornecido**, para melhor leitura nos tamanhos pequenos do Explorador, com múltiplas resoluções; o logo completo permanece no cabeçalho. O Windows pode usar ícone em cache, sendo necessário reabrir o Explorer ou extrair o novo EXE em outra pasta para visualizá-lo.
- A planilha de origem continua intacta, com escrita apenas na cópia de trabalho. Nenhum paciente real integra o repositório ou a compilação.

**Como testar:** abrir o EXE compilado, usar uma planilha de homologação sem dados reais, completar as três etapas, conferir H:K e os comentários em G/K. Validar G vazia e G já preenchida, procedimento divergente, consulta incompleta, filtros e data/hora, sem alterar o código de procedimento original. O `.txt` mantém o diagnóstico técnico sem CPF/CNS/AIH completos.

---

**Estado:** protótipo institucional em homologação. A publicação de código não significa autorização da Regulação ou da TI para automação em produção. Não é um sistema de atesto ou decisão fiscal.

> **Princípio:** a máquina executa o trabalho repetitivo; o fiscal analisa as exceções e toma a decisão.

### Etapas e acompanhamento v0.7.0

A etapa 1 exibe fases reais (planilha, indexação de todo o PDF, cruzamento, gravação). O custo fixo de indexar o PDF explica tempos próximos para 5 ou 784 linhas. A etapa 2 exibe completude de CNS e tempo medido, com 10 segundos hipotéticos por pesquisa. A etapa 3 possui tabela de AIH, paciente, CNS, caráter, procedimento, situação da solicitação **sem inventar número separado** e status; também contabiliza completude e tempo com 10 segundos hipotéticos por consulta.

A etapa 4 é um **resumo estatístico** desbloqueado no encerramento da etapa 3 e não é uma nova etapa operacional. Contém tempo total decorrido do processo, inclusive intervalos e autenticação, tempos das três etapas, completudes, erros e comparativo manual hipotético. Gera automaticamente `RELATORIO_TECNICO_RPA_DDMMAAAA_HHMMSS.txt` na pasta do XLSX de trabalho. O TXT só possui dados administrativos, eventos enumerados, ordinais e hashes SHA-256. Consulte `GUIA_v07.md` para detalhes, validação e limitações. As regras SISREG e a decisão humana permanecem inalteradas.

### Ajustes de interface e ficha cadastral v0.6.2

A tela de conclusão divide o resumo em três linhas (cobertura dos CPFs entre os registros do hospital, tempo estimado e identificação da **nova planilha**), sem dizer “0 acrescentados”. Para 750 CPFs em 784 registros, a cobertura é 95,7%; as 984 AIHs indexadas no PDF são um indicador distinto. O histórico de tempos mantém a hipótese manual de 15 segundos por AIH, não uma economia empiricamente comprovada. O painel de pendências usa rótulos em português. A janela adapta o tamanho ao monitor e, no Windows, abre maximizada para mostrar o rodapé.

A pesquisa cadastral tenta primeiro o XPath específico da ficha SISREG `//*[@id="main_div"]/form/center[1]/table/tbody/tr[3]/td`. A leitura da ficha suporta rótulos Nome:/CPF: acima dos valores, inclusive colunas paralelas. **Só grava o CNS se a ficha apresentar CNS único, nome exato e CPF correspondente à pesquisa.** Se qualquer um faltar ou divergir, registra pendência e não preenche o Excel. A estrutura da página real ainda precisa ser homologada na sessão institucional; os testes de navegação não usam contas nem dados reais.

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

O arquivo `.github/workflows/compilar-windows.yml` constrói no GitHub Actions com dependências fixadas em `requirements-build.txt`, sem dados reais. O workflow executa testes, gera `src/build_info.py` com data UTC da compilação e `versao_windows.txt` com recurso de versão Windows, depois compila `dist/SISREG_Login.exe` via PyInstaller. O EXE mostra `0.7.0` na interface e metadados de versão nas propriedades do arquivo.

Para compilar em Windows *autorizado* com Python de desenvolvimento, use `powershell -File .\compilar_windows.ps1`. A estação da Joice não precisa de Python. O workflow produz o artefato **SISREG_Login_Windows** com `SISREG_Login.exe` e SHA-256 para comparação.

Executar a aplicação na estação da SMS exige autorização, compatibilidade com o navegador e homologação real das telas do SISREG. Não há credenciais ou dados pessoais no processo de compilação.

## Testes e limitações

`python -m unittest discover -s tests -v` usa apenas PDFs/planilhas e telas **fictícios**, sem conectar ao SISREG real. Abrange regras das versões anteriores, SHA-256, original intacto, cópia de trabalho, logs sanitizados, limpeza seletiva, histórico, versão e exportação mínima. Execute também a homologação com cinco AIHs autorizadas no computador institucional; os testes sintéticos não provam correspondência da estrutura real.

**Não utilizar dados reais de pacientes em testes, issues, commits, GitHub Actions ou exemplos de documentação.** Não desativar antivírus, proteções de rede ou controles de acesso para fazer funcionar. O histórico administrativo não substitui log de auditoria autenticado/inviolável; caso se exija custódia institucional, a TI deve aprovar armazenamento protegido, retenção e ACLs.

## Atualização v0.7.1

O fluxo operacional permanece o mesmo. A coluna **Solicitação** da etapa 3 mostra o **Código Solicitação** extraído da ficha somente após comprovação de AIH exata, e é persistida em `rpaNumeroSolicitacao` (P) na cópia XLSX. O campo original `codigoAutorizador` (G) não será completado com esse valor: sua fonte precisa ser comprovada independentemente.

O botão de exportação avulsa de pendências foi retirado da interface; as situações e a trilha já são guardadas na planilha de trabalho. A última aba apresenta cobertura, tempo e arquivos com composição mais legível.

O relatório `.txt` agora possui seção **DIAGNÓSTICO DE AUTOMAÇÃO**: timestamps UTC, operações, status, ordinal, duração em segundos e categoria de erro estritamente enumerada. O histórico administrativo local continua separado. Não grava nome, AIH, CPF, CNS, senha, cookies, HTML ou URLs da sessão. Pode-se perder eventos em memória se o processo terminar abruptamente sem finalizar.

O GitHub Actions incorpora `assets/logo_sisreg_header.png` e `assets/Logo-SISREG.ico` no EXE via `--add-data` e `--icon`. A origem do PNG/ICO é material fornecido pelo responsável pelo projeto; não incluir fotos de pacientes ou documentos nos artefatos.

Não utilizar dados reais de pacientes em testes, issues, commits, GitHub Actions ou exemplos de documentação. A homologação da leitura de campos do SISREG permanece restrita à estação institucional autorizada. Consulte [GUIA_v071.md](GUIA_v071.md) para verificações e retorno à v0.7.0.


### Correção v0.7.3 — planilhas históricas e diagnóstico de falha

O RPA reconhece cabeçalhos conhecidos de 4, 8 ou 9 colunas RPA sem alterar colunas próprias do hospital. O esquema é conferido antes de indexar o PDF. Uma cópia de trabalho ainda idêntica à fonte é retirada se o salvamento falhar; cópias efetivamente gravadas jamais são descartadas por essa rotina. Se a preparação falhar, gera `RELATORIO_TECNICO_RPA_FALHA_*.txt` na pasta da planilha de entrada quando houver permissão. O relatório usa somente categorias permitidas, sem identificar pacientes. Veja `GUIA_CORRECAO_v073.md` para testes e recuperação.
