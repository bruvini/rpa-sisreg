# v0.7.19 — Pesquisa hospitalar e seleção em lote

- Aguarda o recarregamento do frame após pesquisar o CNS e confirma o campo pesquisado antes de ler resultados.
- Confirma a primeira página, a navegação e o número de cada página, distinguindo paginação inconclusiva de AIH não localizada.
- Reconhece a mensagem visível `Nenhum registro encontrado.` e o cabeçalho de zero resultados após pesquisa confirmada.
- Permite selecionar os registros elegíveis visíveis no filtro e limpar a seleção.
- Novos testes usam formulário POST sintético, atraso na resposta, iframe e paginação com navegador real.
- Resultados "AIH não encontrada" obtidos com versões anteriores exigem nova conferência; a homologação no SISREG real permanece necessária.
