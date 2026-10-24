# Guia técnico acadêmico (manual) — v3.1.0

Fonte: `docs/manual/` · Status: documentação de referência para estudo acadêmico

## Onde está e como gerar
- Capítulos em `docs/manual/` (README = índice). Arquivo único: `python tools/build_manual.py` → `dist/MT5Bot-Guia-Tecnico-<versão>.md`; a release publica esse arquivo junto com o instalador.
- `tests/test_manual.py` exige: toda citação `[Autor Ano]` existe em `referencias.md`, toda referência é citada, todo caminho de código citado existe.

## Estrutura
- **Cap. 0 Fundamentos teóricos:** microestrutura (CFD, spread, margem, swap), eficiência de mercado (Fama, Lo adaptativo), anomalias (reversão → RSI2MR; momento → PULLB), expectativa E = p·b − (1−p), equilíbrio p* = 1/(1+b), Kelly, ruína, evidência negativa do varejo. Tabela "da teoria às decisões".
- **Cap. 1–11:** arquitetura, Maestro, cérebro, indicadores, setups, risco, ML, metodologia quant, dados/interfaces, qualidade/entrega, RAG.
- **Cap. 12 Motores:** M1 orquestração … M12 conhecimento; vida de um trade; contratos (quant em distâncias, clássico em preços); núcleo funcional/casca imperativa; fail-open (ML) × fail-closed (risco); crítica aos vários simuladores (referência = `tools/quant_research/research.py`).
- **Cap. 13 Validade:** ameaças de conclusão/interna/externa/construto, limitações técnicas (Kelly com f* ≤ 0, ML fail-open, parcial 50% com lote 0,01, IS/OOS único), ética e regulação, trabalhos futuros.
- **Apêndices:** A glossário, B reprodutibilidade (comandos por resultado), C uso acadêmico (roteiros por área, perguntas de pesquisa, como citar).

## Lição do pacote Wine (issue #47)
O smoke do Wine "estourava o tempo", mas a causa era um crash: o Wine 9.0 do Ubuntu não implementa `ucrtbase.crealf`, usado pelo numpy, e o `winedbg` automático ficava parado até o timeout. Correção: Wine do WineHQ (≥ 10) no CI, depurador automático desligado no smoke (falha rápido) e `install.sh` recusa Wine < 10. Segundo problema: com o Wine 11, cada chamada levava 5 min esperando o diálogo do Mono/Gecko; `WINEDLLOVERRIDES="mscoree,mshtml="` + `wineserver -p` resolveram. Smoke verde em ~1,5 min (Python, 33 módulos, Modo Quant, `mt5bot`, Maestro). Terminal MT5 não é testado no CI; macOS não verificado.
