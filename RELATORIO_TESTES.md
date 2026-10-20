# Verificação técnica — v0.6.0

- Baseline v0.5 executado **antes das alterações**: 65 testes, 0 falhas e 3 skipped.
- Após alterações: consultar resultado registrado pelo executor de testes; os testes de governança usam apenas dados fictícios.
- **Não** houve login real no SISREG nesta execução nem compilação Windows em ambiente local Linux.
- Lista de aceite: fonte intacta, PDF lido localmente, histórico sem CPF/CNS/nome/senha, eventos fechados, limpeza temporária seletiva, arquivos de trabalho separados, pendências mínimas, compilação com versão, ausência de chamadas externas novas, sem decisão de atesto.

## Limites da validação

- `pip` e GitHub Actions baixam dependências no **ambiente de compilação**, sem arquivos hospitalares.
- Não é possível garantir que estação, navegador, proxy, antivirus e pasta de rede institucional cumpram integralmente requisitos apenas com testes locais.
- Logs e arquivo de trabalho são locais e não automaticamente criptografados. Controlar permissões/retensão com a TI.
- Compilação e execução real do novo EXE devem ser homologadas; metadados Windows ainda dependem de CI.
