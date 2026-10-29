# v0.7.14 — Pesquisa e paginação baseadas no HTML do SISREG (29/10/2026)

- Abertura pelo menu Consulta Hosp > Solicitações, com âncora /cgi-bin/cons_aih direcionada ao iframe f_principal.
- Campo CNS identificado por name=cns, type=text, maxlength=15. Botão identificado por name=enviar, type=button e onclick pesquisar().
- Os controles de consulta precisam estar no mesmo iframe oficial HTTPS antes de enviar CNS.
- Apenas linhas selecionáveis da table_listagem com evento mostrarFicha(...) são analisadas. A AIH é lida da sexta coluna; se for exata e única na página, abre a linha inteira.
- Paginação via seta_direita.png, alt Proxima e exibirPagina(...). Confirma mudança da página pelos resultados e não confunde falha técnica com ausência de AIH.
- Mantém os campos da ficha por cabeçalhos/linha seguinte, sem nth-child, e mantém salvamento/revisão e controles de interrupção.
- Testes sintéticos criados com estrutura da tabela, formulário e navegação; confirmar em ambiente autorizado com poucos casos antes de lotes longos.
