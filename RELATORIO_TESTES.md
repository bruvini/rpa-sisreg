# Relatório de testes — RPA SISREG v0.7.0

**Ambiente local sintético (sem autenticação SISREG real).**

- 117 testes descobertos; 113 executados com sucesso e 4 opcionais ignorados, conforme configuração de ambiente (`SISREG_GUI_TEST=1` em display virtual).
- Testes novos: `estatisticas` (denominador e soma manual de consultas tentadas, tempos, logs, hashes, dados pessoais proibidos, arquivo TXT sem sobrescrita), tela gráfica (quarta aba, tabela, sem inferência de número de solicitação), finalização idempotente e geração de TXT na pasta do XLSX sintético.
- Regressão pré-existente mantida: extração PDF, XLSX, cadastro/CNS, hosp/AIH, leitura da ficha, segurança de credenciais, logs administrativos e testes de interface.
- Sem acesso real à plataforma SISREG; a rede e a precisão dos seletores continuam exigindo homologação na estação institucional.
- O arquivo de relatório e a apresentação da economia hipotética devem ser revisados pela equipe fiscal antes de uso gerencial.
