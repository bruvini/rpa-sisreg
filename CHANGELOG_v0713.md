# v0.7.13 — Campos sem posição fixa, paginação e encerramento

- Leitura de caráter pela linha intitulada Caráter / Classificação de Risco e sua linha seguinte (primeira coluna).
- Leitura do procedimento pela linha intitulada Procedimento Solicitado / Código e sua linha seguinte (segunda coluna).
- Extração do Código Solicitação associado ao rótulo, sem presumir número de linha.
- Confirmação da AIH exata antes e depois da captura; códigos conflitantes ou ausentes continuam pendentes.
- Busca paginada otimizada com leitura de linhas em uma única consulta ao DOM, sem alterar limite, intervalos nem seleção de AIH.
- Correção do evento PAGINA_RESULTADOS, anteriormente não permitido no diagnóstico seguro, que interrompia o processamento de eventos na interface.
- Encerramento confirmado após tentativa de salvar o checkpoint não tenta executar relatório potencialmente bloqueante.
- Testes sintéticos de diferentes estruturas de ficha, paginação e encerramento. A homologação real exige teste no SISREG institucional.
