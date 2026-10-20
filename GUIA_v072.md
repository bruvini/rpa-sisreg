# RPA SISREG v0.7.2 — validação da planilha e ícone

A rotina continua: 1. Planilha/PDF → 2. CPF/CNS → 3. Solicitações hospitalares → 4. Indicadores.

## Planilha XLSX

- A:G: planilha do hospital, preservando identificadores, zeros e valores pré-existentes.
- H `rpaSituacao`: motivo principal em português. **Consulta sem divergências** significa comparação automatizada, não atesto.
- I `rpaAtualizadoEm`: data e hora brasileira formatada como data real de Excel.
- J `rpaProcedimentoSISREG`: `Compatível`, `Divergente` ou `Não conferido`.
- K `rpaNumeroSolicitacao`: código da solicitação mostrado na ficha do SISREG.

**Coluna G:** quando não preenchida e a AIH foi confirmada na ficha, recebe o valor do Código Solicitação como regra operacional solicitada pelo responsável. Esse uso não comprova código autorizador distinto. Caso o hospital tenha preenchido G, o RPA preserva esse valor. A origem está documentada nos comentários de G/K.

As colunas H:P das versões anteriores são substituídas por H:K **somente quando têm os cabeçalhos RPA reconhecidos**; outra coluna adicional desconhecida bloqueia a atualização para evitar perda de informação.

## Ícone

O Windows escolhe o tamanho visual do ícone. A v0.7.2 amplia o símbolo S do logotipo em arquivos de 16, 24, 32, 48, 64, 128 e 256 pixels; o logo completo segue visível no programa. O Explorador pode usar cache de ícones, sobretudo se o nome do EXE não mudou.

## Teste de homologação

1. Faça uma cópia sintética do modelo e execute as etapas, sem pacientes reais em computadores não autorizados.
2. Confira os cabeçalhos H:K, formato de I, filtros A:K e comparação J.
3. Valide AIH encontrada, ausente no PDF, cadastro sem retorno e procedimento divergente.
4. Verifique G vazia/G preexistente. G preexistente **nunca** deve ser substituída.
5. Confirme que o TXT continua sem identificadores e que o PDF/planilha original permanecem intactos.
6. Compare os resultados com a v0.7.1. Não distribua em produção antes do aceite institucional.

**Regra de ouro:** a máquina coleta; o fiscal analisa e decide.
