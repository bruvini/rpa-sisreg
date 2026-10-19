# Histórico de versões do RPA SISREG

## 0.4.0 — Consulta hospitalar em lote (homologação)
- Controles de seleção XLSX/PDF reposicionados lado a lado com estilo unificado.
- Preparação renomeada para **Executar conferência**, com cronômetro real e referência manual editável por AIH, explicitamente ilustrativa.
- Captura conservadora do CNS exibido no cadastro dentro de `td[colspan=2] font[size=3] b`, exigindo nome/CPF pesquisado e unicidade.
- Etapa 3 operacional para consulta hospitalar por CNS, correspondência de AIH na tabela e abertura de ficha única.
- Extração condicional de caráter, autorizador e código solicitado; atualização das colunas originais F/G e preservação de C, sem sobrescrita de conflitos.
- Colunas de rastreabilidade M:O para situação hospitalar, procedimento consultado e tempo gasto.
- Checkpoints de planilha, identificação de conflitos e suspensão por falhas consecutivas.
- 53 testes automatizados sintéticos. Login real, layout da ficha e executável Windows ainda pendentes de homologação.

## 0.3.0
- Preparação em lote, CPF do espelho, backup XLSX e pesquisa de cadastro CNS.
