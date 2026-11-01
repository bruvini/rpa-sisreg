# v0.7.11 — Resiliência da ficha e encerramento (29/10/2026)

- Seletores originais confirmados preservados; nova releitura limitada e fallback por rótulos explícitos caso as linhas da tabela variem.
- Códigos múltiplos para o mesmo campo não são escolhidos automaticamente; AIH é revalidada depois da extração.
- Interrupção cooperativa das esperas da etapa hospitalar e ausência de pendência artificial em consultas canceladas.
- Encerramento deixa de esperar sem alternativa: após 15 segundos pode-se confirmar saída com tentativa de gravar checkpoint.
- Histórico da execução interrompida não será incorretamente identificado como concluído.
- Testes sintéticos de campos deslocados, ambiguidade e cancelamento.
