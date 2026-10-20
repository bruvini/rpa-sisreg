# Guia de homologação — v0.7.4

1. Extraia o ZIP do artefato `RPA_SISREG_Windows` numa pasta institucional com
   permissão de escrita. Execute `RPA_SISREG.exe`.
2. Com planilha sintética, selecione XLSX e PDF, conclua a etapa 1 e confira
   se `Análises/Planilha_RPA_*.xlsx` apareceu **sem modificar** o XLSX original.
3. Em acesso real **autorizado**, tente um login propositalmente incorreto.
   Quando aparecer falha, informe as credenciais corretas e clique no mesmo botão;
   a etapa 1 deve permanecer concluída. Repita após fechar somente o Chrome.
4. Use dados autorizados mínimos para conferir CNS, AIH e procedimento. Cheque
   as colunas A:J da nova planilha; o código da solicitação fica em G, K inexistente.
5. Confira o TXT técnico e o histórico em `Logs/`, sem dados individuais.
6. Verifique a janela ⓘ Sobre: autoria, coautoria, suporte e decisão fiscal.
7. Confira o nome nas propriedades do arquivo: `RPA_SISREG.exe`, versão `0.7.4`,
   e o SHA-256 com o manifesto obtido do GitHub Actions.

Em caso de falha: preserve o TXT sanitizado e encaminhe ao suporte institucional;
não anexe planilhas com dados clínicos nem telas com pacientes a uma issue pública.
Não contorne as medidas de segurança da estação.
