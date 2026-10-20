# Relatório de testes — RPA SISREG v0.6.1

Data: 20/10/2026. Execução sintética e local, sem autenticação nem requisições ao SISREG real.

- Descobertos: **96 testes**; testes-padrão: **OK**, 4 ignorados por depender de display/teste DOM; execução com display virtual: **OK**, 1 ignorado (Chromium offline não habilitado nesta passagem).
- Chromium offline: teste anterior de HTML do CNS destacado (`td > font > b`) aprovado.
- Regressões v0.2 a v0.6: continuidade dos controles de CPF/CNS, cópia de trabalho e trilha administrativa.
- Novas verificações: callback progressivo do PDF, situação legível, coluna CNS exclusiva da etapa 2, botão Próxima etapa, nome dinâmico com colisão, vínculo ao resultado em popup oficial, proibição de página externa e bloqueio de CNS divergentes.
- Janela 1080×750: tabela CNS com 209 pixels de altura no display virtual; avaliada a navegação entre etapas.
- **Não homologado:** extração efetiva do CNS na página autenticada SISREG; um nome em DOM diferente ou um resultado ambíguo seguirá como pendência. Também não foi executada a compilação Windows nesta sessão.

A aplicação não toma decisão fiscal nem substitui o julgamento do servidor. Não inserir dados de pacientes reais nos testes, issues ou GitHub Actions.
