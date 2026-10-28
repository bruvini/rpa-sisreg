# v0.7.5 — Resiliência, retomada e continuidade de etapas (2026-10-28)

- Preserva CNS já existentes no XLSX e prioriza pendências ainda não pesquisadas ou falhas técnicas.
- Pendências de identidade de execução anterior permanecem para revisão humana.
- Diagnóstico periódico da sessão, repetição limitada em falhas transitórias, e suspensão após falhas consecutivas sem gerar falsas pendências.
- Salva resultados anteriores, libera login novo e retoma pendentes sem repetir extração da etapa 1.
- Inicia automaticamente a consulta hospitalar após concluir a etapa 2 na mesma sessão saudável.
- Mantém interface, credenciais apenas em memória e arquivos sensíveis somente no ambiente institucional.

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

---

## 0.7.3 — 20/10/2026 · Recuperação da preparação XLSX

- Corrige `AlteracaoExterna` ao receber planilhas legadas com oito colunas técnicas H:O; mantém suporte H:P e ao layout final H:K.
- Validar os cabeçalhos antes da indexação do PDF, preservando dados adicionais desconhecidos sem alterações.
- Corrige o descarte seguro de cópia de trabalho não gravada, com hash da fonte original separado do hash do arquivo salvo.
- Gera TXT técnico estruturado no caso de falha da preparação, sem informações identificáveis; não depende da conclusão das três etapas.
- Restaura o ícone ICO original completo fornecido pela fiscalização; o logotipo PNG permanece no cabeçalho.
- Não altera seletores de navegação, consultas hospitalares ou julgamento fiscal.
- Testes: 150 descobertos; 146 executados sem falhas, 4 ignorados.

## 0.7.2 — Entrega XLSX simplificada e ícone legível (20/10/2026)

- Mantidos os sete campos originais; exportação passa a ter quatro campos H:K, em vez de nove H:P.
- `rpaSituacao`: classificação legível de ponta a ponta; não declara atesto fiscal.
- `rpaAtualizadoEm`: data real do Excel formatada como `DD/MM/AAAA HH:MM:SS`.
- `rpaProcedimentoSISREG`: `Compatível`, `Divergente` ou `Não conferido`.
- `rpaNumeroSolicitacao`: código obtido da ficha hospitalar exata.
- G pode receber, quando vazia, o Código Solicitação da ficha, por regra operacional expressamente solicitada; comentários esclarecem que isso não comprova autorização independente. G preexistente é preservada.
- Aplicadas cores discretas, fonte, larguras, linhas, filtros e Tabelas A:K no modelo Excel.
- Migração defensiva das nove colunas antigas, sem sobrescrever cabeçalhos desconhecidos.
- Ícone multi-resolução refeito com recorte ampliado da identidade original; cabeçalho PNG permanece.
- Motor SISREG, consultas, critérios de identidade, logs sem PII e sequência das quatro abas preservados.
- Testes locais: 142/142 aprovados, inclusive GUI/DOM sintéticos em ambiente gráfico.

# v0.6.2 — CNS da ficha identificada e apresentação

- Consulta do CNS direcionada ao XPath cadastral `#main_div`, em vez de buscar qualquer número destacado.
- Validação estruturada de nome e CPF mesmo quando rótulos/valores estão em linhas separadas; falha fechada se documento ou identidade não confirmar.
- Resumo da etapa 1 organizado em três linhas, com percentual sobre registros hospitalares e cópia criada em destaque.
- Pendências humanizadas também no diagnóstico agregado.
- Janela dimensionada conforme tela e maximizada no Windows quando permitido.
- Testes sintéticos de DOM e segurança, sem acessar SISREG nem publicar dados de pacientes.

# Histórico de versões — RPA SISREG

## v0.6.1 — Usabilidade e identificação cadastral (20/10/2026)

- Preparação progressiva: tabela da etapa 1 aparece assim que o XLSX é lido e recebe atualizações em pequenos lotes durante o cruzamento com o PDF. A indexação textual do PDF ocorre antes das atualizações por AIH.
- Etapa 1 exibe **Aba, Linha, AIH, Paciente, CPF e Situação**; CNS permanece apenas na etapa 2. Situações ganham rótulos simples na interface; códigos técnicos permanecem na planilha para rastreabilidade.
- Botão **Próxima etapa** no rodapé, habilitado somente quando a etapa correspondente tiver sido concluída, sem alterar o bloqueio das abas.
- Etapa 2 tem tabela de pacientes com coluna CNS, atualizada a cada consulta realizada.
- Procura resultado de pesquisa cadastral também em outras janelas oficiais abertas na mesma sessão do navegador, além de quadros/iframes, e considera nomes em células de tabelas do SISREG legado. Continua bloqueando CPF/nome divergente ou CNS múltiplo.
- Cópia de trabalho no formato `Planilha_RPA_DDMMAAAA_HHMMSS.xlsx`, com sufixo `_2`, `_3` quando houver nome já utilizado, sem sobrescrever a fonte.
- Resumo de CPFs diferencia documentos disponíveis de campos preenchidos **nesta execução**, inclusive quando a entrada já contém os CPFs.
- Sem mudanças na consulta hospitalar ou nas regras de auditoria. Testes exclusivamente sintéticos.
- A associação automática do CNS depende de homologação no HTML da tela real; **não há garantia de CNS encontrado quando a identidade não está visível de forma inequívoca**.

# Histórico de versões

## v0.6.0 — Endurecimento, governança e rastreabilidade (19/10/2026)

- Adicionado botão discreto **ⓘ Sobre** com finalidade, demanda, dados tratados e responsabilidade humana.
- Preservadas as três etapas e a navegação do RPA. Sem nova confirmação operacional.
- Originais XLSX/PDF somente leitura; enriquecimentos gravados em **cópia de trabalho automática** no mesmo diretório institucional.
- Implementado histórico local administrativo com UUID, início/fim, hashes das fontes, versão, contagens e duração. Eventos com vocabulário fechado, sem dados individuais.
- Mensagens de erro técnico da interface tornadas genéricas, sem caminhos, login, senha ou payload das páginas.
- Limpeza seletiva dos XLSX temporários e snapshots JSON interrompidos (somente prefixos próprios, mais de 48h). `finally` já fazia a limpeza normal de XLSX.
- Exportação opcional do relatório mínimo de pendências na terceira etapa.
- Normalização da classificação automatizada `DADOS_COLETADOS_SEM_DIVERGENCIA`, sem atribuir atesto ou aprovação fiscal.
- Centralizada `APP_VERSION=0.6.0` com data compilação gerada no build e metadados de versão Windows.
- Novo módulo `governanca.py`, `app_info.py`, script de build, **87 testes de regressão/segurança (3 ignorados)** e documentação.
- Não há integração com serviços externos além das consultas institucionais existentes.

### Atenção

- Mudança no arquivo de saída: **a fonte recebida não é mais modificada**. O trabalho vai para `*_RPA_conferencia_*.xlsx`, selecionado automaticamente.
- O projeto continua em homologação. Login real e seletores hospitalares dependem de teste autorizado.
- A proteção local depende de controles da TI, pasta institucional, integridade do Windows e autorização administrativa.

## v0.5.0 — Interface e CNS em lote

- Preparação, pesquisa cadastral sequencial e terceira etapa hospitalar preservadas na v0.6.0.

## v0.7.0 — Indicadores, acompanhamento hospitalar e relatório TXT (2026-10-20)

- Etapa 1 exibe as fases e tempos reais da leitura da planilha, indexação do PDF, cruzamento e gravação; não apresenta como trabalho concluído CPFs já presentes na entrada.
- Etapas 2 e 3 exibem completude com denominador definido, tempo medido e referência manual hipotética fixa de 10s por consulta efetivamente realizada.
- Etapa 3 ganhou tabela dinâmica: AIH, paciente, CNS, caráter, procedimento consultado, estado da solicitação e situação. Não inventa número de solicitação quando a fonte oferece somente a AIH.
- Adicionada aba 4 para estatísticas de encerramento, tempo global (incluindo intervalos entre etapas), totais e ressalva fiscal.
- TXT técnico sem nomes, AIHs, CPF, CNS, senhas ou páginas, criado junto da cópia XLSX após conclusão/encerramento e complementando o histórico administrativo já existente.
- Eventos de erro técnico do cadastro e hospital codificados e gravados sem conteúdo identificável.
- 117 testes descobertos, sem falhas no ambiente gráfico de testes (4 opcionais ignorados).
- Não houve mudança dos seletores da busca, da regra de correspondência nem da proteção da planilha original.

## 0.7.1 — Solicitação rastreável, identidade visual e log de diagnóstico

- Exibe código real da solicitação no campo Solicitação da tabela hospitalar, extraído exclusivamente da ficha com AIH exata.
- Cria coluna `rpaNumeroSolicitacao` (P) no XLSX, sem alterar os sete campos originais.
- Corrige confusão semântica: o primeiro `<b>` da ficha corresponde ao Código Solicitação, não ao autorizador; não utiliza esse seletor para completar `codigoAutorizador`.
- Remove o botão de exportação avulsa das pendências, mantendo dados na planilha e estatísticas.
- Redesenha a quarta aba com três painéis discretos (cobertura, tempo, arquivos).
- Inclui log técnico cronológico com etapa de pesquisa, seleção da AIH, leitura da ficha, resultado, duração, ordinal e categoria estritamente enumerada, sem PII.
- Incorpora cabeçalho SISREG PNG otimizado e ícone ICO ao EXE no workflow GitHub Actions.
- Preserva importação, indexação PDF, pesquisa CPF→CNS, busca de AIH, pausa e gravacão transacional de planilha.
- Acrescenta testes sintéticos da coluna P, campo autorizado e sanitização dos logs.

- Ajuste final de compatibilidade: valor preexistente em codigoAutorizador (G) não é tratado como conflito sem evidência independente de autorizador do SISREG.
# v0.7.4 — Recuperação de autenticação, pastas portáteis e documentação

- Login com falha deixa de manter navegador zumbi: a thread encerra o contexto e
  permite repetição imediata na mesma execução, sem refazer PDF/CPF.
- Ao fechar janela do navegador, o RPA detecta a ausência de páginas e libera
  uma nova sessão; fila de repetição não persiste senha em disco.
- `RPA_SISREG.exe` substitui `SISREG_Login.exe`, com metadados de versão mantidos.
- XLSX passa a ser criado em `Análises/` e TXT/histórico administrativo em `Logs/`,
  diretórios criados junto ao EXE; nenhum XLSX original é alterado.
- A janela Sobre incorpora créditos, coautoria e canal institucional de suporte.
- README reescrito com instruções de uso, compilação, responsabilidades e riscos.
- Adicionados `LICENSE` (MIT) e `SECURITY.md` para a política de segurança.
- Testes de regressão, recuperação, diretórios, ausência de sobrescrita e versão.

**Atenção:** a licença MIT cobre código e não transfere direito de uso das marcas,
logos ou dados de terceiros; automação depende de autorização institucional.
