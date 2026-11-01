# v0.7.20 — AIHs mascaradas, seleção e trocas aprovadas

- Mantém na leitura da tabela linhas com AIH mascarada ou ausente, permitindo abrir uma AIH exata nas demais linhas ou páginas. Não tenta abrir a linha mascarada.
- Ao esgotar as páginas confirmadas sem correspondência, registra `AIH não confirmada — revisão necessária` quando há números indisponíveis; conserva a distinção de ausência e falha técnica de paginação.
- Usa a mesma elegibilidade na seleção e no início da pesquisa. Exibe a contagem dos aptos/selecionados e motivos dos bloqueados; atualiza o resumo ao alterar filtro, seleção e resultados.
- Extrai somente a seção estruturada de troca de procedimentos, até a próxima seção. Aceita apenas status normalizado exatamente `Aprovada`. Um código aprovado único substitui o inicial na comparação; guarda código inicial e origem internamente.
- Deduplica aprovações repetidas; códigos aprovados conflitantes ou inválidos exigem revisão. Não compara códigos de observações nem de histórico da AIH.
- Exibe e grava `Compatível por troca aprovada` nas colunas existentes, reconhece o rótulo ao reabrir e preserva divergências dos demais campos. Novas ambiguidades não ficam escondidas pelo resultado da consulta anterior.
- Testes com navegador real e dados fictícios cobrem máscaras, segunda página, ausência, paginação quebrada, diferentes status de troca, confirmação final da ficha, filtros, elegibilidade, contagens e persistência/reabertura.
- Compilação pelo GitHub Actions. Ainda requer homologação de poucos casos reais, incluindo ficha com troca aprovada e busca paginada, antes de repetir um lote amplo.
