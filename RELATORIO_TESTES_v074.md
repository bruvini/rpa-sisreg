# Validação técnica — RPA SISREG v0.7.4

**Ambiente de testes:** Linux, Python 3.12, Xvfb para Tkinter. Não houve
conexão real ao SISREG; todos os dados são fictícios.

**Comando executado:**

```bash
SISREG_GUI_TEST=1 PYTHONPATH=src xvfb-run -a python -m unittest discover -s tests -q
```

**Resultado:** 163 testes descobertos, 159 executados com êxito, quatro ignorados
por requisitos específicos do ambiente. **Nenhuma falha.**

## Verificações desta versão

- Senha incorreta: thread do navegador encerra e emite erro seguro; segunda tentativa
  na mesma instância cria sessão limpa sem tocar no preparo (testes offline/mocks).
- Fechamento da janela Chrome: a ausência de páginas/sessão encerra a thread
  e libera nova tentativa sem reiniciar aplicação.
- Código/compilação: versão central `0.7.4`, `RPA_SISREG.exe` e artefato
  `RPA_SISREG_Windows` configurados para PyInstaller no Windows.
- `Análises/` e `Logs/`: criadas ao lado do EXE; fonte XLSX idêntica após gravação
  da cópia em pasta distinta (testes sintéticos).
- Planilha: H:J, sem K; migração de H:K protege G preenchida e move o identificador
  antigo para G se estiver vazia; valor inesperado em K bloqueia alteração.
- README, SECURITY.md e LICENSE: revisão estática de versão, licença e créditos.
- Regressão do motor anterior: buscas, correspondência e saída sem alterações de
  critérios de auditoria (testes unitários e HTML sintético).

## Limites de homologação

- **EXE Windows ainda não compilado nesta validação local.** Confirmar o resultado
  de `GitHub Actions` após publicar o commit.
- **Sem login real:** recuperação deve ser verificada em sessão autorizada e
  em estação institucional, primeiro com uma autenticação inválida e depois válida.
- **Permissões:** execução em pasta institucional com ACL de escrita aprovada pela TI.
  Não modificar permissões do SO para contornar bloqueio.
- **Segurança:** Excel contém dados pessoais, não é criptografado pelo RPA; a
  gestão deve definir retenção e proteção de acesso às pastas.

**Não usar dados reais em issues, testes, documentação ou GitHub Actions.**
