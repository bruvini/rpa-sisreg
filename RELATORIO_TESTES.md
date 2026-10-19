# Relatório de testes v0.3

Data: 19/10/2026. Nenhum acesso ao SISREG real foi realizado nesta homologação automatizada.

- **33 testes unitários e de integração sintéticos: aprovados**.
- Arquivo XLSX simulado, PDF textual de espelho simulado, AIH com e sem hífen.
- Backup e alterações na planilha original testados; persistência de CPF/CNS e conservação das abas A:G.
- Alteração externa antes de salvar detectada e bloqueada; CNS divergente não substituído.
- Texto de resposta simulado: CNS único com nome/CPF compatíveis aceita; CNS múltiplos, nome distinto ou CPF diferente resultam pendentes.
- Navegação simulada com botão real por `name`/`onclick`; sem login no sistema de produção.
- Interface Tkinter instanciada em ambiente gráfico virtual.
- **Pendente:** autenticação real, retorno da pesquisa no SISREG, valores e seletores da tela pós-pesquisa, execução Windows via GitHub Actions e aprovação institucional.

Não afirmar que a captura do CNS real está homologada até o teste assistido da Regulação/TI.
