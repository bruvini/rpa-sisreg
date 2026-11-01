# v0.7.9 — Paginação hospitalar e pausas técnicas sem falso pedido de login (29/10/2026)

- **Etapa 3**: percorre as páginas de resultados da consulta hospitalar até localizar a AIH exata, usando o seletor de avanço informado pela fiscalização. Verifica que a tabela mudou após cada avanço, evita ciclos e limita a busca a 100 páginas por segurança.
- **Consulta incompleta não é ausência**: falha ao abrir próxima página, tabela indisponível, paginação ambígua ou repetida gera pendência técnica recuperável. Só registra “AIH não encontrada após pesquisar todas as páginas — revisar” quando não houver mais página seguinte identificável. Isso não comprova inexistência no SISREG.
- O registro com busca paginada integralmente esgotada fica destinado à revisão fiscal, sem repetição automática em cada sessão. Falhas técnicas de paginação permanecem na fila de retomada.
- **Sessão e CAPTCHA**: três erros técnicos com sessão ainda autenticada agora geram uma pausa técnica, sem abrir automaticamente a janela de verificação humana. CAPTCHA visível ou autenticação não confirmada continuam requerendo intervenção humana. Falha do servidor (502/503/upstream) não é tratada como CAPTCHA.
- **Aproveitamento de dados**: planilha e dados anteriores permanecem preservados; a interface mantém as quatro abas e não adiciona confirmações obrigatórias.
- **Logs**: eventos de visita a páginas e de pausa técnica registram apenas códigos de operação, sem AIH, CNS, CPF, nomes ou HTML da página.
- **Testes**: cenários sintéticos para AIH somente na segunda página, ausência após última página, paginação sem avanço, ausência não tratada como falha técnica e retomada após pausa técnica.

## Limitações

O controle de paginação é baseado na estrutura da tela informada em 29/10/2026. Caso o SISREG altere o HTML ou a sinalização da última página, a automação deixará a consulta inconclusiva. Não foi realizada homologação ao vivo do seletor no SISREG; somente testes locais e do pipeline. A automação não contorna CAPTCHA nem limites institucionais de acesso.
