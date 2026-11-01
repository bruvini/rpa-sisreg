# RPA SISREG v0.7.3 — Relatório da correção

## Diagnóstico reproduzido

A planilha institucional recebida foi inspecionada exclusivamente no ambiente de trabalho local. Ela apresentava 8 cabeçalhos legados H:O, enquanto a v0.7.2 esperava 9 no layout antigo, lançando `AlteracaoExterna`. A saída incompleta era uma cópia criada antes da validação, não evidência de que somente um CPF foi encontrado.

## Correções e verificações

- Pré-validação do esquema antes da leitura do PDF;
- Migração sintética de 8 e 9 colunas antigas para H:K;
- Teste local com a cópia recebida: 7 registros de teste da ocorrência, três abas, quatro cabeçalhos H:K após o salvamento, sem modificação da fonte;
- Colunas novas formatadas segundo identidade do modelo; nenhuma coluna RPA legada além de K após migração;
- Descarte conservador de cópia de trabalho **somente** quando os bytes ainda corresponderem à fonte original;
- Retenção de cópia quando já gravada;
- TXT com categoria técnica emitido mesmo em falhas precoces, sem nome, CPF, CNS ou senha;
- Ícone integral restituído a partir do arquivo enviado;
- 150 testes encontrados, 146 executados e aprovados, 4 ignorados (condições ambientais específicas) em Xvfb.

## Limites

Não foi feita nova consulta ao SISREG de produção. A compilação Windows e a aplicação no posto institucional dependem de validação externa. Os arquivos clínicos e a planilha recebida não acompanham o pacote/repositório.
