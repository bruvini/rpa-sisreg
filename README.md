# RPA SISREG — Conferência de internações em lote

![Versão](https://img.shields.io/badge/vers%C3%A3o-0.7.21-07436b) ![Python](https://img.shields.io/badge/Python-3.12-3776AB) ![Licença](https://img.shields.io/badge/c%C3%B3digo-MIT-555555)

Aplicação desktop para Windows que lê planilhas XLSX e espelhos de AIH em PDF, complementa CPF, consulta CNS no SISREG III e confere os dados da solicitação hospitalar. A automação consulta o SISREG e organiza os resultados localmente. **Não altera solicitações, não aprova produção e não realiza atesto fiscal.**

O projeto está em **validação operacional assistida**, com resultados conferidos em uso autorizado e testes de regressão com dados fictícios. A utilização exige autorização institucional e perfil adequado no SISREG. Novas versões e variações da página oficial continuam exigindo homologação local.

## Filas por etapa

As abas mostram o trabalho correspondente à etapa, aproveitando os dados já existentes na planilha reaberta.

| Etapa | Fila de trabalho | Dados aproveitados |
| --- | --- | --- |
| 1. Planilha e PDF | Registros sem CPF na entrada, para pesquisa no espelho de AIH | CPF existente não é reprocessado; conflitos de identidade ficam para revisão |
| 2. Cadastro e CNS | Registros com CPF válido e ainda sem CNS após a preparação | Sem CPF e CNS já preenchidos não aparecem nessa fila |
| 3. Solicitações hospitalares | Registros com CNS válido e consulta hospitalar pendente | Registros sem CNS ficam nas etapas anteriores; fichas completas anteriores não entram na fila padrão |
| 4. Resultados | Resumo da execução, arquivos salvos e exportação de pendências | A planilha de trabalho mantém todos os registros e classificações |

Resultados produzidos durante uma etapa permanecem disponíveis no seu acompanhamento. Uma consulta hospitalar não reinsere o paciente nas tabelas de PDF ou cadastro. Ao concluir a etapa 2, a etapa 3 começa na mesma sessão e **a interface muda automaticamente para a aba hospitalar** quando há consultas a executar.

Caráter e solicitação preenchidos, sem uma comparação de procedimento reconhecida, não comprovam uma consulta hospitalar completa. O RPA mantém esse caso para conferência.

## Consulta hospitalar e revisão

- Abre Consulta Hosp > Solicitações, pesquisa o CNS e aguarda a resposta do mesmo frame antes de examinar os resultados.
- Compara a AIH normalizada com a sexta coluna de cada linha selecionável. O hífen não altera a comparação; uma AIH mascarada nunca comprova identidade.
- Percorre as páginas necessárias, confirmando a navegação. Uma linha mascarada ou vazia não impede localizar uma AIH exata nas demais linhas ou páginas.
- Abre a linha correspondente e confirma a AIH antes e depois da extração. Solicitação, caráter e procedimento são lidos pelos rótulos, sem posições fixas.
- Na seção **Troca de Procedimentos**, um código único com status exatamente **Aprovada**, após normalização, passa a ser o procedimento vigente. Repetições do mesmo código são deduplicadas. Códigos aprovados diferentes ou inválidos exigem revisão. Observações e histórico do número da AIH não entram nessa comparação.
- Quando a planilha corresponde ao procedimento vigente aprovado, mostra e salva **Compatível por troca aprovada**. Divergências de caráter ou solicitação continuam sinalizadas.

Uma busca completa sem registros, ou sem correspondência com todas as AIHs comparáveis, resulta em **AIH não encontrada**, para revisão. Se existem números mascarados ou ausentes que impedem concluir, o resultado é **AIH não confirmada — revisão necessária**. Uma falha de navegação ou leitura permanece uma falha técnica; não vira ausência ou irregularidade do paciente.

A tabela da etapa 3 começa em **Por pesquisar**, incluindo falhas recuperáveis. Os filtros **Divergências**, **Falhas técnicas**, **AIHs não encontradas** e **AIHs não confirmadas** permitem pesquisar novamente casos selecionados. Fichas já lidas com divergência continuam nesses filtros explícitos. Registros sem CNS não aparecem em nenhum filtro hospitalar. **Todos** se refere aos registros dessa etapa, incluindo resultados da consulta atual, não a toda a planilha.

Para repetir várias consultas: escolha o filtro, clique em **Selecionar todos do filtro** e em **Pesquisar selecionados novamente**. O resumo mostra quantos estão selecionados e aptos e os motivos dos bloqueados. Resultados completos são reconhecidos ao reabrir a planilha, inclusive o rótulo de troca aprovada.

## Pausa, CAPTCHA e retomada

Falhas técnicas transitórias recebem uma tentativa adicional. Falhas consecutivas ou indisponibilidade podem pausar o lote para evitar resultados incorretos.

1. Diante de verificação humana ou perda de sessão, o RPA pausa novas consultas, preserva os resultados recebidos e mantém o registro em andamento pendente.
2. Regularize o acesso no navegador oficial e clique em **Verificar sessão e retomar** no RPA.
3. O aplicativo valida a sessão e continua pelos registros pendentes, sem repetir os já concluídos.

O SISREG pode pedir verificação sem conseguir exibir o desafio. Aguarde a disponibilidade do serviço; o RPA não cria nem resolve CAPTCHA. Confirmar não força a retomada se a sessão ainda estiver indisponível. Se o navegador tiver fechado, entre novamente na etapa 2; as etapas concluídas e a seleção de revisão são preservadas.

**Interromper**, **Encerrar** e o **X** iniciam o encerramento com salvamento dos resultados recebidos. Se o navegador não responder, uma confirmação permite encerrar apenas o processo criado pelo RPA. Uma consulta ainda sem resultado pode precisar de nova pesquisa. Falhas de salvamento aparecem na interface e impedem apresentar a execução como concluída com segurança.

## Arquivos e proteção dos dados

- Use o modelo com as abas `POA CIRURGICO`, `PT6` e `ALTA COMPLEXIDADE`, preservando os cabeçalhos A:G.
- A fonte recebida e o PDF são preservados. A cópia enriquecida é criada em `Análises/`, ao lado do executável, com checkpoints durante o processamento.
- As colunas existentes `rpaSituacao`, `rpaAtualizadoEm` e `rpaProcedimentoSISREG` registram classificação, data e comparação. Campos de origem discordantes não são substituídos silenciosamente.
- Mantenha o Excel fechado durante o lote. A gravação verifica alterações externas e usa substituição atômica do arquivo de trabalho.
- `Logs/` contém diagnósticos por operação, duração e categoria e históricos administrativos. Não deve conter nomes, CPF, CNS, AIHs, credenciais, HTML ou capturas de pacientes.
- Totais da planilha incluem resultados anteriores. Os eventos da execução e o último lote são apresentados separadamente; tentativas repetidas não equivalem a pacientes distintos.

Os tempos manuais de referência são **hipóteses**: 15 segundos por registro de PDF e 10 segundos por consulta SISREG. Não representam produtividade manual medida ou economia comprovada.

Leia [SECURITY.md](SECURITY.md). Nunca envie arquivos reais de pacientes ao repositório, ao GitHub Actions ou a uma issue pública.

## Executável e verificação

O fonte e as alterações são publicados neste repositório. O executável distribuído é compilado pelo workflow [Compilar RPA SISREG para Windows](https://github.com/bruvini/rpa-sisreg/actions/workflows/compilar-windows.yml).

Na execução aprovada, abra **Artifacts > RPA_SISREG_Windows** e extraia `RPA_SISREG.exe` e `SHA256.txt`. O pipeline executa testes unitários, de interface e de navegação real com páginas e dados fictícios, compila o programa e verifica a inicialização do `.exe`, incluindo seu processo de automação. O executável não tem assinatura digital; confira o SHA-256 publicado e siga a política de distribuição da TI.

Antes de um lote amplo, confira poucos casos na sessão autorizada: AIH na primeira página, outra em página posterior, troca aprovada e, quando ocorrer, retomada após verificação humana. Testes sintéticos e inicialização do executável não substituem essa conferência.

Últimas alterações: [v0.7.21](CHANGELOG_v0721.md), [v0.7.20](CHANGELOG_v0720.md) e [v0.7.19](CHANGELOG_v0719.md).

## Créditos e licença

- Desenvolvimento: Enf. Bruno Vinícius.
- Coautoria: Joice Correa Gomes e Heloisa Hoffmann.
- Contato técnico institucional: bruno.vinicius@joinville.sc.gov.br.

O projeto nasceu da fiscalização de contrato, para apoiar a conferência de internações informadas pelo prestador. Código sob [licença MIT](LICENSE), com preservação dos créditos e do aviso de copyright. Marcas, imagens e identidade visual de terceiros permanecem sujeitas aos direitos dos respectivos titulares. A ferramenta não implica endosso oficial do Ministério da Saúde.
