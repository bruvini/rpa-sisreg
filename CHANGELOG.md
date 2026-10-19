# Alterações do RPA SISREG

## v0.5 — Fluxo automático da preparação à identificação de CNS

- Mostra a situação da leitura/indexação próximo do botão e substitui o resumo textual por cartão de conclusão.
- Mede tempo real e fixa o cenário comparativo manual em **15 segundos por AIH** (hipótese, não ganho medido).
- Bloqueia acesso às etapas seguintes até a anterior ficar concluída.
- Reconhece o menu de login e dispara automaticamente a busca de **todos** os CPFs pendentes, sem checkbox de confirmação ou seleção de tamanho.
- Mantém botões de pausa/interrupção e opção de retomar pendências para recuperação de falhas.
- Ajusta leitura do CNS destacado em TD/FONT/B quando CPF deixa de aparecer na página após a busca; restringe gravação a identificação sem conflitos visíveis.
- Expõe no painel os motivos quantitativos das pendências por tipo.
- Impede desbloquear etapa 3 após lote interrompido antes da conclusão.
- Corrige escape de novas linhas no JavaScript de captura DOM, validado em Chromium com HTML sintético local.
- Preserva gravação com backup, original de entrada e regras conservadoras de identidade e AIH.

## v0.4 — Consulta hospitalar em lote

- Pesquisa solicitação pela AIH exata e registra caráter, autorizador e código de procedimento sem substituir conflitos.
