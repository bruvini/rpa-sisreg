# Segurança | RPA SISREG

**Responsável por contato técnico:** Enf. Bruno Vinícius — bruno.vinicius@joinville.sc.gov.br.

## Escopo e dados protegidos

Este projeto automatiza atividades **somente de consulta** no SISREG III, em ambiente
institucional autorizado. Processa AIH, nome, CPF, CNS e dados de internação na
estação autorizada. Não conclui atestos e não altera solicitações no SISREG.

- Trate dados de saúde como pessoais sensíveis conforme a **LGPD (Lei nº 13.709/2018)**.
- Autorização de acesso, finalidade, acesso mínimo, guarda e descarte devem seguir
  a política da SMS/Regulação/TI. A licença do código **não autoriza** acesso ao SISREG.
- Planilhas de resultado ficam em `Análises/` na pasta do executável; são **sensíveis**.
  Conceda leitura apenas a pessoas autorizadas, com retenção institucional definida.
- `Logs/` contém TXT técnicos e histórico JSON/JSONL administrativo, sem identificadores
  de pacientes ou credenciais. Logs técnicos NÃO devem incluir URLs de consulta, cookies,
  páginas HTML, screenshot, nomes ou documentos completos.
- Usuário e senha ficam transitoriamente em memória e são usados somente no domínio
  `https://sisregiii.saude.gov.br/`. Após falha de login, a sessão de navegador
  é encerrada e uma nova sessão limpa deve ser iniciada. O RPA não persiste senhas.
- O aplicativo não incorpora telemetria, analytics nem serviços externos de IA.
  O GitHub Actions recebe **somente código e amostras fictícias**, nunca dados reais.

## Relatar vulnerabilidade

Envie relato por canal institucional ao contato acima ou à TI/Segurança da Informação
municipal, **sem anexar dados pessoais, planilhas hospitalares, cookies, senhas ou
capturas não anonimizadas**. Não crie uma issue pública de segurança. Informe versão,
passos de reprodução com dados sintéticos, impacto e condições de execução.

## Versões

A versão mantida é a `main` e artefatos gerados por GitHub Actions. Atualizações
necessitam homologação em estação autorizada; rollback por cópia do EXE anterior.
A compilação **não assina digitalmente** o executável. Implantação e verificação de
hashes/assinatura dependem de aprovação da TI. Não contorne CAPTCHA/MFA ou bloqueios
operacionais; nunca desabilite antivírus, firewall ou controles institucionais.

## Licença e identidade visual

Código sob **MIT**, exigindo preservação do aviso de copyright e licença na redistribuição.
O uso do nome SISREG, marcas/brasões oficiais, logotipos, imagens de terceiros e dados
do SUS não é licenciado pelo repositório. Direitos desses materiais permanecem com seus
titulares. Atribuição ao projeto não significa endosso oficial do Ministério da Saúde.

Leia também [README.md](README.md) e [LICENSE](LICENSE).
