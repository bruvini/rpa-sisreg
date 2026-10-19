# Validação técnica v0.4

**Resultado local:** `53 tests / OK`. Composição: testes anteriores do fluxo v0.3, regras de CNS destacado, caráter, autorizador, códigos de procedimento, gravação segura no XLSX, divergências, AIH duplicada e AIH exata em linha variável. A interface Tkinter foi instanciada com display virtual e as três abas abriram.

**O que NÃO foi comprovado:** login oficial com credenciais reais; operação dentro da rede da SMS; presença estável dos XPaths de resultados e de ficha; interpretação da tabela do SISREG autenticado; build Windows do GitHub Actions. Essas verificações são mandatórias na homologação.

**Riscos tratados:** sem escolha arbitrária de primeira solicitação; arquivo XLSX atualizado somente com evidência; dado conflitante preservado; backup da fonte; saída sem senha; não modificar o SISREG; não registrar HTML ou dados de pacientes nos testes; campo inexistente não é inferido.

**Critérios mínimos para homologação:** testar um CNS encontrado, um CPF sem cadastro, uma AIH com duas solicitações, uma AIH não localizada, uma divergência de procedimento, um código autorizador com zeros iniciais, uma alteração externa da planilha, e 5 AIHs em sequência. Inspecionar manualmente células F/G e colunas M:O.
