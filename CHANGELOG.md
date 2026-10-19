# Changelog

## v0.3.0 — CPF e CNS em lote
- Preserva interface local com 3 etapas e simplifica o fluxo para operação por lote.
- Leitura do espelho e atualização automática da própria XLSX (não apenas cópia).
- Backup antes da primeira gravação, hashes, gravação atômica e controle de edição externa.
- Pesquisa múltipla por CPF no SISREG, com botão `btn_pesquisar` identificado pelo nome e `onclick`.
- Procura campo de pesquisa também em frames internos oficiais; verifica presença real do formulário antes de avançar.
- Só associa CNS quando o resultado mostrar nome inequívoco e CNS rotulado único; demais registros permanecem pendentes.
- Lotes de 5, 20, 50 ou todos, com pausa, checkpoints, retomada e pausa por 3 falhas consecutivas.
- Consulta Amb → Solicitações permanece fora do escopo desta versão.
- Testes com pacientes e AIHs **inteiramente fictícios**.

## v0.2.0 — PDF e consulta individual assistida
- Preservada no histórico do GitHub para rollback.
