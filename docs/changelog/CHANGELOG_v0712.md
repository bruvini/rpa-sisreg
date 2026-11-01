# v0.7.12 — Corrigir executável que não abre (29/10/2026)

A v0.7.11 removeu acidentalmente a chamada de entrada da aplicação ao substituir o final de `src/sisreg_login.py`. O executável iniciava e terminava sem abrir o Tkinter.

- Restaurada `main()` e a guarda `if __name__ == '__main__': main()`.
- Testes automatizados verificam a existência e execução do ponto de entrada da GUI.
- A pipeline Windows passa a executar o `RPA_SISREG.exe --smoke-test` e exige uma evidência criada pelo `main()`; sucesso do PyInstaller sem entrada executável deixa de ser suficiente.
- Sem modificações no fluxo de dados, planilhas ou seletores de consulta em relação à v0.7.11.
