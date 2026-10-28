# Homologação controlada — RPA SISREG v0.7.5

1. Use somente dados fictícios ou registros formalmente autorizados. Nunca publique dados de pacientes no GitHub.
2. Reabra a última planilha de `Análises/`. O sistema cria nova cópia e preserva CPFs e CNS existentes.
3. Após autenticar no SISREG, observe que somente cadastros pendentes elegíveis são consultados.
4. Ao concluir a etapa de CNS, a busca de solicitações hospitalares inicia automaticamente, sem clique adicional.
5. Simule quatro respostas consecutivas sem identidade confirmada: o lote deve suspender sem registrar falsas ausências.
6. Informe novamente o login após suspensão e confira que os resultados salvos permanecem.
7. Inspecione TXT e arquivos JSON de `Logs/` para verificar ausência de dados identificáveis.
8. Não contorne suspensão/bloqueio de estação, MFA ou controles de rede; valide uso noturno com TI/Regulação.
