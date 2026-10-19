# Histórico de mudanças

## 0.2.0 — leitura do espelho e consulta ambulatorial assistida

- Mantém as mesmas funções de segurança da autenticação da v0.1.
- Inclui seletor da planilha hospitalar XLSX e do PDF SIHD2 textual opcional.
- Indexação da AIH removendo apenas pontuação do dígito verificador; exige 13 dígitos.
- Identidade confirmada por AIH e nome antes de usar documentos do PDF.
- Separação de CPF e CNS, sem inferir um a partir do outro.
- Pesquisa por CPF/CNS e, após confirmação da operadora, navegação até solicitações ambulatoriais.
- Salva cópia XLSX com campos e estado da auditoria, sem sobrescrever origem.
- Suspende a automação na página de resultados para homologação dos seletores e regras.
- Amplia a suíte para 24 testes locais sintéticos.

## 0.1.0 — login assistido

- Janela de usuário, senha e seleção Edge/Chrome; autenticação pelo formulário SISREG em navegador visível.
