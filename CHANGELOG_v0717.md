# v0.7.17 — Retomada, fechamento e revisão de pendências

- Detecta a verificação humana também nos frames oficiais e retoma o lote hospitalar a partir do registro interrompido após confirmação manual.
- Repete uma vez falhas técnicas transitórias, sem repetir automaticamente AIH não localizada e sem consultar durante CAPTCHA ou indisponibilidade.
- Isola a automação do navegador em processo próprio. A saída confirmada preserva o checkpoint e, se necessário, encerra apenas a árvore de processos criada pelo RPA.
- Corrige a categoria de pausa técnica que podia interromper a atualização da interface e mantém a leitura de eventos ativa após erro inesperado.
- Adiciona indicação da etapa, barras horizontais nas tabelas, filtros de pendências e nova pesquisa de itens selecionados.
- O histórico mantém contagens da execução atual. A validação no SISREG real continua necessária.
