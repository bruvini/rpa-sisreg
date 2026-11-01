# Segurança do RPA SISREG

Contato técnico: Enf. Bruno Vinícius — bruno.vinicius@joinville.sc.gov.br.

## Estado e escopo

A versão atual é a **v0.7.22**, em validação operacional assistida. A versão mantida é o fonte da `main` e seus artefatos aprovados no GitHub Actions. Testes automatizados e uso assistido não equivalem a homologação institucional de todas as situações reais.

O programa realiza consultas no SISREG III e processa PDF/XLSX localmente, em estação e sessão autorizadas. Não altera solicitações, cancela internações, aprova produção ou realiza atesto fiscal. Autorização de acesso, finalidade, perfil mínimo, guarda e descarte seguem a política da SMS/Regulação/TI. A licença do código não concede acesso ao SISREG.

## Dados, credenciais e arquivos

- Nome, AIH, CPF, CNS e dados de internação são processados no fluxo necessário à conferência. Trate dados de saúde como pessoais sensíveis conforme a LGPD (Lei nº 13.709/2018).
- A planilha recebida e o espelho PDF são preservados. Resultados e checkpoints ficam na cópia de trabalho em `Análises/`, junto ao executável. Essa pasta contém dados sensíveis e exige controle de acesso e retenção institucional.
- Credenciais são usadas transitoriamente em memória para autenticação em `https://sisregiii.saude.gov.br/`. O RPA não grava senhas, cookies ou tokens em configuração ou logs. O navegador roda em processo local próprio; os dados necessários trafegam por comunicação entre processos da mesma máquina.
- A validação de origem bloqueia o uso das credenciais em hosts não autorizados. O aplicativo usa uma sessão de navegador criada para a automação, sem precisar reutilizar o perfil pessoal.
- A gravação verifica o hash do arquivo de trabalho, detecta alterações externas e usa temporário no mesmo volume antes da substituição atômica. Mantenha o Excel fechado durante o lote. Falha de gravação deve permanecer visível e não equivale a conclusão salva.
- O RPA não incorpora analytics, telemetria remota ou serviços de IA. A consulta ao SISREG exige rede; PDF/XLSX e diagnósticos são processados localmente.

## Diagnósticos e divulgação

`Logs/` reúne relatórios e históricos JSON/JSONL com versão, horários, contagens, hashes, ordinais, etapa, duração e categorias controladas. Não deve registrar nomes, CPF, CNS, AIHs, valores do DOM, HTML, capturas, URLs de consulta, senhas, cookies ou tokens. Uma ocorrência pode aparecer em mais de uma operação; categorias de log não equivalem a pacientes distintos ou falhas finais.

O diagnóstico de reCAPTCHA observa passivamente as respostas e falhas dos recursos conhecidos do Google e consulta apenas a disponibilidade da API e a presença do iframe no documento oficial. O TXT específico usa categorias fechadas, versão e horário; não registra URLs completas, parâmetros, cabeçalhos, chave do site ou conteúdo do desafio. Não são emitidas sondagens adicionais, lidos tokens de resposta ou alteradas proteções do navegador.

Os arquivos de resultado são a referência para os dados coletados. Resumos administrativos antigos podem conter contagens incompletas; uma sessão interrompida pode ter resultados válidos já salvos. Não conclua perda dos dados ou execução completa apenas pelo estado do histórico.

O repositório e o GitHub Actions recebem **somente código, documentação e exemplos fictícios**. Não publique planilhas, PDFs, HTML de pacientes, capturas reais, credenciais ou logs sem revisão. Pastas de resultados e logs são ignoradas pelo Git, mas essa proteção não substitui a conferência do que será enviado.

## Limites e recuperação

- O programa exige correspondência exata da AIH e valida a ficha antes e depois da extração. AIH mascarada ou ausente impede concluir ausência quando não há correspondência. Erros de navegação não devem virar inexistência de solicitação.
- A comparação usa o procedimento inicial ou uma troca aprovada única na seção estruturada. Aprovações conflitantes ou inválidas ficam para análise humana. Nenhuma comparação constitui atesto ou prova de irregularidade.
- CAPTCHA, perda de sessão e indisponibilidade suspendem novas consultas. A pessoa regulariza o acesso e confirma a retomada; a sessão precisa ser validada antes de continuar pelo registro pendente. O SISREG pode pedir verificação sem exibir o desafio. O RPA não resolve, contorna ou força o carregamento de CAPTCHA.
- Ao encerrar, o aplicativo salva os resultados recebidos. Se o navegador ficar bloqueado, a saída confirmada pode terminar somente o processo de automação criado pelo RPA e seus descendentes, preservando outras sessões do computador. A consulta em andamento pode precisar de nova tentativa; falhas de salvamento são informadas.

## Compilação e atualização

O executável distribuído é compilado no GitHub Actions deste repositório. O pipeline testa dados fictícios, interface e navegação, verifica a inicialização do `.exe` e publica `RPA_SISREG_Windows`, com o executável e `SHA256.txt`. O hash permite conferir a integridade do arquivo baixado; não equivale a assinatura digital ou garantia contra todas as vulnerabilidades.

O executável **não é assinado digitalmente**. Distribuição, validação e implantação seguem a política da TI. Não desabilite antivírus, firewall ou controles institucionais para executá-lo. Preserve o executável anterior e a planilha de trabalho para recuperação. Confira poucos casos representativos na sessão autorizada antes de um lote amplo com uma nova versão.

## Relatar vulnerabilidades

Envie o relato pelo canal institucional ao contato técnico ou à TI/Segurança da Informação municipal. Não abra issue pública de segurança e não anexe dados pessoais, planilhas reais, HTML, cookies, senhas ou capturas não anonimizadas. Informe versão, condições, impacto e reprodução com dados fictícios.

Código sob [licença MIT](LICENSE). Marcas, brasões, logotipos e imagens permanecem sujeitos aos direitos dos respectivos titulares. A atribuição ao projeto não representa endosso oficial do Ministério da Saúde. Consulte também o [README](README.md).
