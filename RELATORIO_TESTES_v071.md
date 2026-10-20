# Testes v0.7.1 — registros fictícios

- Regressão automatizada: 125 cenários descobertos; 113 aprovados, 12 ignorados por configuração/ambiente. Sem falhas.
- Novos testes: AIH exata, solicitação extraída e separação de autorizador; coluna P em XLSX sintético; log codificado sem CPF/nome; categorias inválidas rejeitadas; sequência de observador BUSCA_HOSPITALAR → AIH_EXATA → LEITURA_FICHA.
- Testes não efetuados nesta etapa: autenticação em ambiente real, leitura do novo campo no SISREG ao vivo, compilação e uso do EXE na estação da SMS.
- Verificar build GitHub Actions após publicação e realizar homologação com pequeno conjunto autorizado.
