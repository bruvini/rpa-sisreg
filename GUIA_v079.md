# RPA SISREG v0.7.9 — Paginação e recuperação da etapa hospitalar

1. Use normalmente o XLSX mais recente de **Análises** como fonte, caso esteja retomando uma execução. O RPA cria outra cópia; não apague a anterior.
2. As etapas 1 e 2 permanecem iguais. A etapa 3 agora procura a **AIH exata em todas as páginas** de resultados da pesquisa pelo CNS, em vez de consultar somente a primeira página.
3. Quando nenhuma página restante puder ser identificada e a AIH não aparecer, o resultado será **AIH não encontrada após pesquisar todas as páginas — revisar**. Isso exige análise do fiscal; não é atesto nem declaração de inexistência.
4. Se a página seguinte falhar ou não puder ser confirmada, a consulta será **inconclusiva** e recuperável. Se a sessão estiver autenticada, falhas técnicas consecutivas produzirão uma **pausa técnica** (sem a janela de CAPTCHA). Verifique o SISREG e use o botão existente **Pesquisar solicitações hospitalares em lote** para continuar depois que estiver normalizado.
5. Se o SISREG efetivamente solicitar CAPTCHA ou a autenticação não puder ser confirmada, resolva manualmente no navegador oficial e confirme a recuperação dentro da janela do RPA.
6. **Não** aumente artificialmente a frequência de consultas para compensar páginas extras. O RPA respeita as proteções do SISREG. O processamento continuado depende de condições de rede e autorização da Regulação/TI.

Testes de homologação: caso fictício/expurgado com AIH na primeira página, outro na segunda, outro ausente após a última e cenário de falha de paginação. Compare a saída XLSX e o TXT em `Logs`, sem compartilhar dados identificáveis ou imagens de pacientes em issues e commits.
