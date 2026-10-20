# RPA SISREG v0.6.2 — Relatório de testes

A implementação é um protótipo sujeito à homologação na estação institucional; os testes são offline e não autenticam no SISREG.

- **108 testes automatizados:** aprovados, incluindo testes gráficos com display virtual e HTML fictício no Chromium.
- CNS localizado na célula específica do cadastro, com nome e CPF alinhados em linhas diferentes: aprovado em cenário sintético.
- Nome diferente, CPF diferente, CPF ausente e CNS malformado: nenhum é vinculado automaticamente.
- Etapas, planilha original, backups, histórico de execução e convenções de nome: sem regressões nos testes existentes.
- Pendente: confirmar os seletores com a página real do SISREG, política de execução Windows, compilação .exe e a identificação dos CNS autorizados na estação da SMS.
- Nenhuma planilha, documento ou sessão de paciente real foi incluída em tests/fixtures, CI ou pacote.
