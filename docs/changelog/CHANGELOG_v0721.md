# v0.7.21 — Filas por etapa e acompanhamento da execução

- A etapa 2 mostra apenas CPF válido e ainda sem CNS no início dessa etapa. Resultados novos continuam no acompanhamento; registros sem CPF ou com CNS previamente disponível ficam fora da fila.
- A etapa 3 oculta registros sem CNS válido em todos os filtros. A fila padrão conserva consultas por fazer e falhas recuperáveis. Fichas completas anteriores com divergência permanecem nos filtros explícitos; compatibilidades anteriores são aproveitadas.
- Resultados hospitalares não inserem linhas nas tabelas de PDF ou cadastro. Resultados de cadastro não inserem linhas na tabela de PDF.
- Ao iniciar consultas hospitalares, inclusive após conclusão automática ou ausência de pendentes na etapa 2, a interface seleciona a aba 3.
- Sobre, README e SECURITY descrevem o estado de validação operacional assistida, filas, trocas aprovadas, checkpoints, encerramento e limites da verificação humana.
- O aviso de intervenção explica quando o SISREG pede verificação sem exibir o desafio. A retomada exige validação da sessão; não há automação de CAPTCHA.
- Novos testes de interface com dados fictícios cobrem filas, planilha reaberta, resultados por etapa, mudança automática de aba e conteúdo do Sobre. Compilação e teste de inicialização pelo GitHub Actions.
