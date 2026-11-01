# CAPTCHA solicitado, mas sem componente visível

## O que foi confirmado

O HTML analisado inclui o script `https://www.google.com/recaptcha/api.js` e um elemento `.g-recaptcha` com chave pública, conforme a [exibição automática documentada pelo Google](https://developers.google.com/recaptcha/docs/display). Ter esse HTML não prova que o componente terminou de carregar ou ficou visível.

O erro `SecurityError` informado apontava para o ajuste de altura de `ifrm-barra-brasil`, a barra superior do governo. Esse iframe tem `sandbox`, enquanto o script do SISREG tenta ler seu documento com jQuery `contents()`. Essa leitura exige origem compatível, conforme a [documentação do jQuery](https://api.jquery.com/contents/) e a [política de mesma origem](https://developer.mozilla.org/en-US/docs/Web/Security/Defenses/Same-origin_policy). O erro identifica um problema nesse ajuste da barra; não demonstra, por si só, a causa da falha do reCAPTCHA em outro frame.

Na investigação assistida, foram informadas respostas HTTP `200 OK` para os recursos, mas o componente não apareceu. A abertura da própria página oficial de verificação em outra aba também ficou em branco, carregando. Esse resultado não sustenta uma correção apenas por altura ou recorte do iframe. A causa da falha visual continua sem comprovação; não foi feita alteração na página oficial.

## Diagnóstico disponível no RPA

A partir da v0.7.22, durante a pausa e após uma confirmação sem recuperação da sessão, o RPA observa:

- Disponibilidade da API `grecaptcha` no documento oficial.
- Presença do elemento de verificação e do iframe criado dentro dele. A presença do iframe não equivale a desafio visível ou resolvido.
- Respostas HTTP e falhas de carregamento dos recursos conhecidos do Google/reCAPTCHA, sem emitir requisições adicionais.
- Categorias de pendência de rede, timeout, DNS, conexão segura, bloqueio e erros HTTP, quando esses sinais forem informados pelo navegador.

O resultado aparece no aviso do RPA e é salvo em `Logs/DIAGNOSTICO_RECAPTCHA_<data_hora>.txt`, mesmo que o lote permaneça pausado. O arquivo contém versão, horário e categorias fechadas. Não contém nomes, documentos, HTML, URLs completas, parâmetros, chave do site, cookies, tokens ou conteúdo dos desafios. O RPA não lê a resposta do desafio e não o resolve automaticamente.

Uma resposta HTTP 200 informa sucesso de transporte, não sucesso visual ou validação humana. O diagnóstico também não substitui a investigação da TI no navegador e nos serviços envolvidos.

## Como proceder

1. Se o componente aparecer, resolva o desafio no navegador e clique em **Confirmar na própria página do SISREG**.
2. Volte ao RPA e clique em **Verificar sessão e retomar**. O aplicativo valida a sessão antes de continuar.
3. Se continuar vazio ou carregando, mantenha as consultas pausadas. Preserve a planilha e encaminhe o diagnóstico sanitizado ao suporte institucional.

Se forem necessárias informações do navegador, anote somente nome do recurso, código HTTP ou erro `net::ERR_...`. Evite copiar requisições completas como `fetch`, HAR, HTML ou cabeçalhos: podem conter dados da sessão. Não desative proteções do navegador, remova `sandbox`, altere o domínio do reCAPTCHA ou force a aprovação no SISREG como tentativa de correção.

[Voltar à documentação](README.md)
