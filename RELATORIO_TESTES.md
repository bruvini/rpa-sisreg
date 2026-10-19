# Relatório técnico — RPA SISREG v0.5

Execução local em 19/10/2026, com dados sintéticos. **Não houve acesso ao SISREG de produção**.

| Ensaio | Resultado |
|---|---|
| Regressão antiga + novas regras, sem interface gráfica | 65 testes descobertos, 62 executados e aprovados, 3 opcionais ignorados |
| Testes Tkinter com Xvfb (bloqueio de etapas, cartão de conclusão, backup) | 65 descobertos, 64 executados e aprovados, 1 opcional ignorado |
| Teste HTML de CNS em Chromium real (página sintética local) | 65 descobertos, 63 executados e aprovados, 2 de interface ignorados |
| CPF pesquisado já não visível na página; nome e CNS destacados | Aprovado na simulação |
| CPF explícito e divergente, nome divergente ou múltiplos CNS | Bloqueio de gravação aprovado |
| Tempo manual fixo de 15 segundos por AIH | Aprovado |
| Exposição da aba 2 antes de preparar e aba 3 antes de concluir a etapa 2 | Bloqueio testado |
| Captura de CNS em páginas autenticadas reais do SISREG | **PENDENTE DE HOMOLOGAÇÃO** |
| Geração do EXE Windows no GitHub Actions | **PENDENTE DE VERIFICAÇÃO DO WORKFLOW** |

Cuidado: os testes sintéticos validam o código e DOM fictício, não a acurácia em SISREG real nem os controles de acesso concedidos ao operador. O XLSX com dados reais fornecido na conversa foi inspecionado localmente e **não** foi incorporado ao pacote ou a repositórios.
