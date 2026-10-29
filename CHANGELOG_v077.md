# Changelog — v0.7.7 (29/10/2026)

- Corrige finalização prematura da etapa hospitalar em suspensão por CAPTCHA ou falhas consecutivas.
- Introduz evento `hospital_suspenso`, checkpoint antes de intervenção e retomada após autenticação confirmada, sem refazer fichas concluídas.
- Evita contabilizar suspensão como encerramento bem-sucedido da análise; preserva log final/parcial e histórico na saída.
- Ajusta histórico de erros técnicos para incluir falhas da etapa hospitalar.
- Distingue “cadastro não confirmado” de cadastro inexistente e “AIH não confirmada” de inexistente.
- Inclui orientação de fiscalização em comentários da coluna H, sem colunas adicionais.
- Mantém o ritmo conservador de consultas; comparativo de 10s por consulta manual permanece **hipotético**.
- Normaliza a codificação explícita UTF-8 dos testes e `PYTHONUTF8=1` no GitHub Actions.
- Apenas testes sintéticos; nenhum dado de paciente ou credencial incluído.
