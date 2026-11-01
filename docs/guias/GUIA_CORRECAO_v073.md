# RPA SISREG v0.7.3 — Correção da preparação e recuperação

## O que motivou a revisão

Foi identificada uma falha em uma planilha oriunda de versão anterior que continha **oito** colunas técnicas entre H e O. A v0.7.2 reconhecia apenas quatro colunas novas ou nove colunas antigas completas; com oito, lançava `AlteracaoExterna` depois de já ter criado a cópia de trabalho. A tabela mostrava CPFs em memória, mas a gravação não se concluía. Isso não representa falha na indexação do PDF.

## Como ficou o uso

1. Selecione a planilha hospitalar e o PDF como antes. Não há nova confirmação ou tela.
2. Clique **Executar conferência**. A compatibilidade dos cabeçalhos é conferida **antes** da leitura demorada do PDF.
3. O RPA aceita a planilha limpa, o layout atual (H:K) e os dois layouts legados conhecidos: H:O (oito colunas) ou H:P (nove colunas). Só migra colunas sob controle conhecido do próprio RPA.
4. Após o salvamento, a planilha de trabalho contém as sete colunas originais e quatro de auditoria formatadas (H:K). A planilha selecionada é preservada.
5. Em caso de falha, o RPA não autoriza avançar a etapa; a cópia de trabalho inicial que continuar idêntica à fonte é descartada, e o diagnóstico `RELATORIO_TECNICO_RPA_FALHA_DDMMAAAA_HHMMSS.txt` é criado ao lado da planilha selecionada, quando a pasta permite escrita.

## Diagnóstico e limites

O TXT de falha registra dados técnicos estruturados e classificados, como `LAYOUT_XLSX_INCOMPATIVEL` ou `PREPARACAO_NAO_CONCLUIDA`. Não inclui nome, CPF, CNS, AIH, credenciais ou conteúdo HTML do SISREG. Layouts desconhecidos e dados adicionais sem cabeçalho **não são removidos automaticamente**.

O novo executável usa a arte completa original do arquivo ICO fornecido pelo usuário, sem a versão recortada da letra S. O fluxo de consultas ao SISREG, as três etapas de trabalho e a responsabilidade fiscal **não sofreram alterações**.

## Homologação segura

- Faça a primeira execução com cópia autorizada ou dados sintéticos.
- Confira as colunas A:K das três abas e o número de registros esperados. Verifique que L em diante não contenha colunas antigas após migração bem-sucedida.
- Verifique que a origem permaneceu inalterada (mesmo SHA-256).
- Em caso de erro, observe o TXT de falha na mesma pasta, sem compartilhar dados pessoais em issues, commits ou suporte público.
- Depois do sucesso na etapa 1, teste a pesquisa SISREG com autorização institucional.

## Testes

150 testes descobertos: 146 aprovados e quatro ignorados no ambiente gráfico de teste. Incluem migração H:O, migração H:P, bloqueio de dados desconhecidos, descarte apenas da cópia não gravada, preservação da cópia salva, TXT sem dados pessoais e regressão das consultas.
