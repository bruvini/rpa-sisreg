# v0.7.22 — Organização e diagnóstico da verificação humana

- Guias, históricos de versão, relatórios de testes e hashes antigos foram organizados em `docs/`, com índices e links relativos atualizados. README, SECURITY, LICENSE e o índice CHANGELOG permanecem na raiz.
- O auxiliar de compilação foi movido para `scripts/compilar_windows.ps1` e resolve a raiz do projeto a partir dessa pasta. O workflow mantém os caminhos de fonte, recursos e dependências e agora considera mudanças na documentação.
- Observação passiva do carregamento do reCAPTCHA, com categorias fechadas de HTTP, rede, API e presença do iframe. Não há novas sondagens, alteração da página oficial ou resolução automatizada do desafio.
- O aviso de pausa mostra o diagnóstico disponível e grava um TXT sanitizado em Logs, sem depender da conclusão do lote. HTTP 200 ou presença de iframe não implicam desafio exibido ou resolvido.
- O erro de origem informado aponta para o iframe da barra superior do SISREG. A causa do componente vazio permanece não comprovada; a falha também foi relatada em aba própria. Não foi aplicada uma correção especulativa no navegador ou na página oficial.
- Testes em navegador real com páginas fictícias verificam script bloqueado, HTTP 200, respostas de erro, iframe e erro de sandbox em outra área. Testes de privacidade verificam os diagnósticos; links locais e organização também são conferidos.
