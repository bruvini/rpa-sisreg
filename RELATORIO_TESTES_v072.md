# Testes v0.7.2 — cenário sintético

- Suite: `python -m unittest discover -s tests -v`.
- Execução gráfica/DOM: `SISREG_GUI_TEST=1 SISREG_DOM_TEST=1 xvfb-run -a python -m unittest discover -s tests`.
- **142 testes executados, 0 falhas, 0 ignorados** na execução gráfica com Xvfb; incluindo validação HTML fictício do CNS e GUI.
- Cobertura adicional: sete categorias de situação fiscal-operacional, tratamento de timeout como inconclusivo, procedimento compatível/divergente/não conferido, G vazia e preenchida, salvamento da data, A:G intactas, H:K formatadas, migração defensiva e Tabelas Excel A:K.
- Sem acesso a SISREG real; sem dados pessoais reais no pipeline. Os XPaths oficiais da interface devem continuar homologados na estação da SMS.
