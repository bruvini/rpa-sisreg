# v0.7.10 — Confirmação da ficha (29/10/2026)

- Seletores: solicitação (linha 1), caráter (linha 46), procedimento (linha 50).
- Após paginação, só lê campos quando a ficha aberta demonstra a AIH exata; verifica janela principal e popups oficiais da sessão.
- Novos CNS são pesquisados na página principal, não na última janela da ficha.
- Falhas de leitura somam para a pausa técnica após três ocorrências consecutivas.
- Procedimento hospitalar ausente ou inválido fica pendente, sem falso sucesso.
- Preservados resultados anteriores, salvamentos, paginação e CAPTCHA humano. Testes sintéticos adicionados; requer homologação institucional.
