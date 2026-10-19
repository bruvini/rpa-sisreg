# Relatório de validação técnica — RPA SISREG v0.2

- 24 testes automatizados **aprovados** em execução Linux isolada (nenhum acesso ao SISREG).
- PDF fictício textual gerado no teste: leitura por AIH `422650033029-4` e correspondência com `4226500330294`.
- Confirmação negativa: nome divergente, espelho conflituoso e CPF inválido não promovem dados automaticamente.
- Importação da planilha de três abas/cabeçalhos e exportação de uma cópia XLSX testadas.
- Teste do browser por mocks: abertura das opções do menu ambulatorial e submissão de CNS, sem leitura de resposta.
- Janela Tkinter aberta em display gráfico isolado (Linux, sem navegador conectado).
- Não foi fornecido PDF SIHD2 real para validação; sua leitura depende de teste de homologação.
- Não foi efetuada consulta em sessão SISREG real; credenciais e dados de pacientes **não** foram utilizados.
- EXE Windows ainda precisa de compilação no GitHub Actions e autorização/execução local pela TI.
