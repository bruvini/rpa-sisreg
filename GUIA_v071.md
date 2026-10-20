# Guia rápido — RPA SISREG v0.7.1

**Fluxo mantido:** 1. Planilha/PDF → 2. CNS → 3. Solicitações hospitalares → 4. Resultado.

## Novidades

- Na etapa 3, **Solicitação** apresenta o número encontrado na ficha hospitalar, quando a AIH exata foi confirmada.
- O número também é registrado na coluna técnica `rpaNumeroSolicitacao` (P) da cópia XLSX. As colunas originais A–G são preservadas.
- **Código da solicitação NÃO é código autorizador.** Por segurança, o campo `codigoAutorizador` da fonte hospitalar não será completado com o seletor da solicitação; requer origem independente comprovada para automação futura.
- O botão avulso de exportação de pendências foi removido da interface. As pendências continuam na planilha de trabalho e no relatório de execução.
- A última aba exibe três blocos discretos: cobertura, tempos e arquivos.
- PNG SISREG no cabeçalho e ICO do aplicativo no Windows, fornecidos pelo responsável pelo projeto.
- TXT técnico detalha operações, resultados, duração, classificação de falha e ordinal do registro, SEM dados dos pacientes.

## Como testar

1. Em computador autorizado, execute o aplicativo v0.7.1 e faça a conferência com um conjunto pequeno **fictício** ou expressamente autorizado.
2. Confirme CPF e CNS recuperados e abra a etapa 3.
3. Para uma AIH cuja ficha esteja disponível, verifique o número da solicitação na tabela, correspondendo ao **Código Solicitação** da ficha.
4. Abra a cópia de trabalho e verifique a nova coluna `rpaNumeroSolicitacao` (P). O `codigoAutorizador` (G) não deve ter sido preenchido com o número da solicitação.
5. Confira o relatório TXT na mesma pasta da planilha: etapas, UTC, ações codificadas, duração, ordinal e categorias de erro.
6. Confirme que o TXT não apresenta nomes, AIHs, CPFs, CNS, senha, cookies, HTML, parâmetros da URL ou stack traces.
7. Confira a aparência do cabeçalho e o ícone do executável em Propriedades do Windows.

**Segurança:** não enviar arquivos reais, capturas de tela de cadastro, log com conteúdo sensível ou credenciais ao GitHub. O TXT é administrativo/técnico; não substitui registro fiscal. O RPA não atesta produção. Não desative os controles de TI.

## Limitações

- As posições relativas dos campos no SISREG são sujeitas a mudanças; só o ambiente autenticado autorizado valida os seletores reais.
- O campo `codigoAutorizador` não será inferido de `Código Solicitação`. Uma fonte independente é necessária.
- Logs em memória são incluídos no TXT no encerramento normal ou parcial; queda abrupta pode perder o diagnóstico não persistido. Eventos administrativos permitidos continuam no histórico local.
- A estimativa de tempo manual é hipotética e não comprova produtividade/economia.
