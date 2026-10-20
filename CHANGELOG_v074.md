# v0.7.4 — Recuperação de autenticação, pastas portáteis e documentação

- Login com falha deixa de manter navegador zumbi: a thread encerra o contexto e
  permite repetição imediata na mesma execução, sem refazer PDF/CPF.
- Ao fechar janela do navegador, o RPA detecta a ausência de páginas e libera
  uma nova sessão; fila de repetição não persiste senha em disco.
- Remove coluna redundante K do XLSX; migra H:K de versões antigas para H:J
  preservando G (`codigoAutorizador`).
- `RPA_SISREG.exe` substitui `SISREG_Login.exe`, com metadados de versão mantidos.
- XLSX passa a ser criado em `Análises/` e TXT/histórico administrativo em `Logs/`,
  diretórios criados junto ao EXE; nenhum XLSX original é alterado.
- A janela Sobre incorpora créditos, coautoria e canal institucional de suporte.
- README reescrito com instruções de uso, compilação, responsabilidades e riscos.
- Adicionados `LICENSE` (MIT) e `SECURITY.md` para a política de segurança.
- Testes de regressão, recuperação, diretórios, ausência de sobrescrita e versão.

**Atenção:** a licença MIT cobre código e não transfere direito de uso das marcas,
logos ou dados de terceiros; automação depende de autorização institucional.
