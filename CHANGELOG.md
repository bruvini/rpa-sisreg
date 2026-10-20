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
