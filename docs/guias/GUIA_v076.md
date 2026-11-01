# Guia de homologação da v0.7.6 — RPA SISREG

## Objetivo

Validar a pausa segura do RPA diante de verificação de acesso **real do
SISREG**, sem tentar contornar o CAPTCHA nem perder dados. Testes automatizados
usam HTML e dados fictícios; qualquer teste no SISREG deve ser feito somente por
operadores institucionais autorizados e observando seus termos.

## Homologação

1. Salve uma cópia de segurança do XLSX já enriquecido. Abra a v0.7.6,
   selecione esse arquivo e o PDF autorizado, e conclua a preparação.
2. Verifique no painel a quantidade **acumulada de CNS** (dados da cópia de
   trabalho) antes do login. Não confunda com o total de consultas da nova fila.
3. Realize o login. Se o SISREG exigir CAPTCHA ou um novo login, o RPA deve
   exibir um alerta nativo, parar as consultas e manter a janela do navegador
   disponível — inclusive após mais de 45 segundos.
4. Resolva manualmente no navegador oficial. Clique **Já concluí a verificação
   no SISREG**. Se a autenticação ainda não estiver pronta, o RPA continua
   aguardando sem reenviar a consulta.
5. Após confirmação do menu autenticado, verifique que ele retoma somente
   registros pendentes e mantém CNS anteriores. Ao terminar a etapa 2
   normalmente, inicia a etapa 3 usando a mesma sessão.
6. Faça um teste de fechamento **voluntário** do navegador e autentique-se de
   novo pelo RPA, sem reler o PDF durante a mesma execução.
7. Confirme que o arquivo em `Análises` mantém os dados, que o TXT/JSON em
   `Logs` não contêm nome, CPF, CNS, AIH ou senha, e que códigos de intervenção
   constam somente em registros técnicos enumerados.

## Limites

- Não provocar artificialmente centenas de consultas para gerar CAPTCHA.
- Não automatizar nem fornecer serviços de resolução do desafio.
- Interrupções por bloqueio da estação, rede ou expiração exigem suporte
  institucional e podem impedir continuidade desassistida.
- **Concluir CAPTCHA não garante que o SISREG autorize novas consultas.**
  Se o sistema persistir bloqueando, suspenda e informe Regulação/TI.

## Retorno à versão anterior

O executável da v0.7.5 permanece recuperável na compilação/artefato anterior.
Não sobrescreva planilhas anteriores; use a última cópia enriquecida de
`Análises` como entrada de uma nova execução após autorização.
