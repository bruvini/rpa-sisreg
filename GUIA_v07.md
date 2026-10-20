# RPA SISREG v0.7.0 — acompanhamento, estatísticas e log técnico

## Propósito

Automatizar atividades repetitivas de localização de CPF em espelho de AIH, consulta de CNS e pesquisa hospitalar por AIH exata, mantendo **o juízo fiscal exclusivamente humano**. A ferramenta não atesta nem aprova produção.

## Fluxo da operadora (inalterado até o encerramento)

1. **Planilha e PDF:** selecionar os mesmos arquivos e executar. A tabela carrega os registros já presentes no XLSX, enquanto o RPA informa separadamente leitura da planilha, indexação do PDF, cruzamento e gravação. A leitura do PDF inteiro pode durar aproximadamente o mesmo tempo para 5 ou 784 linhas porque o custo principal é processar o PDF de centenas de páginas. São apresentados o tempo total da etapa e a completude real dos CPFs.
2. **Pesquisa em lote SISREG:** após login autorizado, a pesquisa de CNS continua automática. Agora apresenta taxa de CNS identificados no **universo elegível para pesquisa**, tempo da etapa e comparação manual **hipotética de 10 s por consulta efetivamente realizada**.
3. **Solicitações hospitalares:** permanece pesquisa por CNS e AIH exata. Uma tabela na própria aba atualiza **AIH, Paciente, CNS, Caráter, Procedimento, Solicitação e Situação** ao concluir cada pesquisa. A coluna *Solicitação* informa *AIH localizada na ficha* ou *ainda não confirmada*: a fonte atual **não fornece um número separado de solicitação**, portanto o programa não inventa esse número. Também são exibidos completude, pendências, tempo medido e referência manual hipotética de 10 s por AIH efetivamente consultada. Um resultado sem divergência nos campos disponíveis **não equivale a atesto**.
4. **Resultados da execução:** desbloqueada após encerrar a etapa 3 (inclusive quando ela termina parcialmente, se as alterações puderem ser salvas). Mostra totais, completude por fase, erros técnicos, tempo individual de cada etapa e **tempo total de parede**, que inclui espera entre as fases e durante login. Compara com a referência manual hipotética das consultas realizadas. A diferença não é economia cientificamente comprovada.

## Log técnico `.txt`

Ao finalizar ou encerrar uma execução preparada, é gerado automaticamente, **na pasta da cópia de trabalho**, um `RELATORIO_TECNICO_RPA_DDMMAAAA_HHMMSS.txt`. O sistema cria nome alternativo em caso de colisão, sem sobrescrever.

O TXT registra apenas: versão, ID de execução aleatório, horários, status, durações, totais, resultados por etapa, hashes SHA-256 de entradas, eventos codificados e ordinais de registro. Nunca registra nome, CPF, CNS, AIH completa, usuário/senha, cookies, conteúdo do navegador ou mensagens livres de exceção. O histórico administrativo JSON e eventos JSONL continuam no diretório local governado da versão anterior; o TXT é um resumo adicional.

Erros como timeout e falha de navegação são eventos `ERRO_TECNICO` codificados. Para investigação por paciente, use apenas a **cópia XLSX institucional** e a fila de pendências, sem publicar dados em issues ou logs.

## Referenciais e limites

- Etapa 1: **15 s por AIH hospitalar** (total de registros da planilha, antes de extrair CPF).
- Etapa 2: **10 s por pesquisa cadastral efetivamente realizada**.
- Etapa 3: **10 s por consulta hospitalar efetivamente realizada**.
- As taxas de completude têm denominadores explícitos: CPFs por registros hospitalares; CNS por pesquisas cadastrais elegíveis; fichas sem divergência nos campos consultados por AIHs elegíveis à etapa hospitalar.
- As três hipóteses são fixas e **não demonstram economia real nem eficiência medida do fluxo manual**. Validação de produtividade exige estudo observacional separado.
- Tempo total é contado do clique inicial na etapa 1 até o encerramento da etapa 3, inclusive pausas, autenticação e tempo ocioso da operadora. A soma dos tempos das três etapas pode ser menor que o tempo total.
- O SISREG exige acesso autorizado; não executar indiscriminadamente em produção sem aprovação da Regulação e da TI. O RPA não contorna segurança e não altera dados SISREG.
- Um quadro aparentemente completo pode ter ressalvas assistenciais que necessitam avaliação. Estatísticas de captura automática não implicam regularidade de faturamento.

## Privacidade

O XLSX recebido e o PDF ficam intactos; o RPA cria e atualiza uma **cópia de trabalho**. Logs e TXT usam somente contagens, identificadores de execução e códigos pré-aprovados; logs de erros não recebem tracebacks livres. O GitHub Actions usa apenas dados sintéticos e não recebe planilhas hospitalares. Feche o Excel durante as gravações.

**Não utilizar dados reais de pacientes em testes, issues, commits, GitHub Actions ou exemplos de documentação.**

## Como testar / compilar

```
python -m pip install -r requirements-build.txt
python -m unittest discover -s tests -v
```

Para testes gráficos, usar `SISREG_GUI_TEST=1` com ambiente gráfico autorizado. No Linux de desenvolvimento, `xvfb-run -a env SISREG_GUI_TEST=1 python -m unittest discover -s tests -v` pode realizar o teste sem exibir dados reais. A compilação Windows permanece sob `.github/workflows/compilar-windows.yml`. O artefato Windows contém o `SISREG_Login.exe` e SHA-256 após GitHub Actions bem-sucedido. Reversão: usar a versão anterior `0.6.2` preservada no GitHub, sem editar XLSX de produção de forma retroativa.

## Alterações de fonte

- `src/estatisticas.py` — agregação de estatísticas, taxas, tempo e relatório técnico sem PII;
- `src/sisreg_login.py` — 4ª aba, tabela dinâmica hospitalar, tempos e indicadores das etapas, fechamento e eventos técnicos;
- `src/app_info.py` — versão centralizada `0.7.0`;
- `tests/test_estatisticas_v07.py` e `tests/test_interface_v07.py` — testes novos;
- três testes antigos — atualizados para a nova versão, preservando cenários anteriores;
- `README.md`, `CHANGELOG.md`, `RELATORIO_TESTES.md` — documentação operacional, limites e regressão.

**Compatibilidade:** motor de correspondência, requisitos de consentimento/credenciais e seletores SISREG **não foram alterados**. As mudanças são de interface, agregação de resultados e reporte técnico.
