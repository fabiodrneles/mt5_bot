# Constituição do MT5Bot

Princípios que toda spec e todo PR devem respeitar. Mudá-los exige uma spec própria.

1. **Capital primeiro.** Nenhuma mudança pode abrir posição sem SL gravado na corretora, nem mexer em posição ou ordem sem o MAGIC do bot. Verificável por teste (`test_panic`, `test_shutdown_manager`, `test_quant_routes`).
2. **Só opera ao vivo o que foi validado.** Estratégia nova entra no modo ao vivo somente com validação fora da amostra registrada na wiki (custos reais, IS × OOS, teste de sorte). O resto roda em `/study`.
3. **Honestidade nos números.** Resultados exibidos ao usuário usam o lucro real do MT5 (comissão e swap incluídos) e dizem o que é histórico e o que é ao vivo. Nenhuma promessa de lucro.
4. **CI verde é pré-condição.** Nada entra na `main` com CI vermelho. Gates nunca são enfraquecidos para passar.
5. **Testado.** Todo critério de aceite tem teste automatizado; o MT5 é simulado nos testes (`tests/conftest.py`).
6. **Uma fonte da verdade.** Telemetria em `mt5bot/core/telemetry.py`; configuração em `config.py` + `config.toml` do usuário; nada de lógica duplicada entre interfaces.
7. **Leve.** Roda em i3 de 4ª geração com 4 GB de RAM. Dependência nova pesada só com justificativa em spec.
8. **Instalável por leigos.** O caminho principal de uso não exige git, Python, Go nem edição de código.
9. **Reprodutível.** Binários vêm do CI a partir do código da tag, com checksums; nenhum binário versionado no git.
