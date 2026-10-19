# RPA SISREG — v0.5 · Conferência em lote

**Homologação técnica:** execução local em Windows com aprovação da Regulação/TI. Não publicar ou sincronizar PDFs, planilhas hospitalares, CPFs, CNS, senhas ou relatórios em repositórios ou nuvem não autorizada. Nenhuma ação modifica as solicitações no SISREG; somente consultas nas telas autorizadas.

## Fluxo da operadora

1. **Planilha e PDF:** escolha o XLSX padrão e o espelho de AIH. Clique **Executar conferência**. O RPA lê o PDF pesquisável, localiza o espelho pela AIH e confirma o nome, faz backup e completa apenas células de CPF/CNS vazias e comprovadas. O tempo decorrido fica junto ao botão. Ao concluir, exibe um resumo destacado e libera a segunda aba.
2. **Pesquisa SISREG:** informe as credenciais no programa local e clique **Abrir SISREG e entrar**. Depois que o menu autenticado aparecer, o programa **inicia automaticamente a consulta de todos os CPFs elegíveis**, sem selecionar o tamanho de lote e sem marcar confirmação visual. O navegador permanece visível. A planilha é atualizada periodicamente com CNS identificados com segurança; motivos das pendências aparecem na tela. O botão **Retomar CPFs pendentes** fica como recuperação em caso de interrupção, não como etapa obrigatória.
3. **Solicitações hospitalares:** esta aba só fica acessível após a preparação e a conclusão do lote cadastral. A pesquisa de todos os CNS com AIHs pendentes pode ser iniciada pela operadora. A correspondência exige AIH exata; caráter, autorizador e procedimento são registrados somente com evidência suficiente.

O fechamento do Excel é obrigatório antes da atualização. O programa salva na planilha escolhida, depois de criar `*.backup_antes_RPA.xlsx`; alterações externas ou bloqueio durante a execução interrompem a persistência para evitar perdas.

## Melhorias desta versão

- Bloqueio das etapas 2/3 durante a preparação, e da etapa 3 enquanto a identificação de CNS está pendente/interrompida.
- Mensagem de progresso junto ao botão **Executar conferência** e cartão de conclusão com os tempos.
- **Premissa manual fixa de 15 segundos por AIH**: apenas estimativa demonstrativa, não economia medida. O cronômetro do RPA é real.
- Login dispara automaticamente a busca de **todos** os CPFs quando é reconhecido o menu autenticado. Sem botão de confirmação visual e sem escolha de tamanho do lote.
- Reconhecimento do CNS em `td[colspan="2"] font[size="3"] b`, mesmo que o SISREG deixe de exibir o CPF da consulta após a pesquisa. Exige nome correspondente, um único CNS, ausência de CPF divergente visível e busca pelo CPF inicialmente informado. Caso contrário, registra a pendência; não adivinha dados.
- O relatório de pendências identifica motivos específicos (`NOME_NAO_CONFIRMADO_RESULTADO`, `CPF_DIVERGENTE_CADASTRO`, `CNS_DESTACADO_AMBIGUO_OU_AUSENTE` etc.).
- Mantém registro periódico na mesma planilha hospitalar com backup, bloqueio contra edição externa e trilha de procedência.

## Validação e limites

Foram executados testes sintéticos dos módulos e da interface com Xvfb. O seletor do CNS foi exercitado também em HTML sintético real no Chromium (sem acesso ao SISREG). **Ainda é necessário testar a v0.5 no SISREG institucional**: se a tela de cadastro real apresentar outro padrão, o robô deve registrar pendências e não associar CNS incerto.

Os testes sintéticos não provam que um CNS está correto num cadastro real. Não foram realizadas consultas remotas ao SISREG durante a preparação desta versão.

## Gerar EXE no GitHub Actions

Em um repositório privado autorizado, acesse **Actions → Compilar RPA SISREG para Windows → Run workflow**. Após conclusão bem-sucedida, faça download do artefato `SISREG_Login_Windows`. O programa requer Chrome ou Edge já instalado e autorização da TI. O `.exe` pode ser bloqueado caso não seja assinado/homologado; não contorne políticas institucionais.

Para executar os testes em Windows sem interface gráfica, o workflow usa `python -m unittest discover -s tests -v` e ignora os testes opcionais que exigem Xvfb e Chromium local de Linux.
