# Guia de atualização — RPA SISREG v0.7.8

**Sem mudança na sequência:** Planilha/PDF → Cadastro/CNS → Solicitações hospitalares → Resultados.

Selecione a última planilha preenchida em `Análises`. O sistema gera **outra cópia**, preservando o arquivo recebido. O PDF será processado apenas se faltarem CPFs para localizar. No SISREG, as pesquisas de CNS já preenchidos são ignoradas; as consultas hospitalares comprovadamente completas também são reaproveitadas.

Os indicadores são separados: **total de registros**, **aproveitados da planilha anterior** e **consultados na sessão**. No Excel, os estados de divergência e de falha técnica são distintos; passe o mouse sobre a situação para ler a orientação de revisão. Nenhum resultado é atesto fiscal.

Se aparecer CAPTCHA ou o SISREG ficar indisponível, o robô pausa. Conclua o desafio diretamente no Chrome/Edge, quando houver, e clique em **Verificar sessão e retomar** na janela do RPA. Se o serviço não estiver disponível, aguarde a normalização e confirme novamente. Não tente abrir múltiplas sessões nem contornar o limite de acesso do SISREG.

O programa mantém `Análises/` e `Logs/` junto de `RPA_SISREG.exe`. A senha não é persistida. Não feche o Excel durante a execução. O funcionamento com os servidores reais precisa ser homologado pela operadora autorizada e pela TI.
