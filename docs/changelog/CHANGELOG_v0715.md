# v0.7.15 — Leitura flexível da ficha e saída responsiva

- Caráter e procedimento são associados a rótulos próximos, inclusive com uma linha vazia intermediária ou valor na mesma célula. Valores conflitantes continuam pendentes.
- Procedimento aceita o código SIGTAP de dez dígitos com pontuação; a AIH continua confirmada antes e depois da leitura.
- No encerramento confirmado após navegador sem resposta, a gravação do checkpoint ocorre fora da interface. Falha ou demora no salvamento é apresentada antes de descartar alterações recentes.
- Testes sintéticos cobrem as variações de rótulos, linhas vazias e conflitos. A homologação no SISREG real ainda é necessária.
