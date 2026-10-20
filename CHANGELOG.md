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
