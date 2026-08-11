# Fonte: aprofundamento.md (arquitetura decidida)

> Arquivo: `raw/aprofundamento.md` (145KB) · Original no repo raiz (não rastreado)

## O que é
Registro da conversa de aprofundamento sobre a arquitetura do bot — decisões sobre Go/Python, design de princípios, e análise do setup 9.1 em Python.

## Decisões-chave
1. **Go = maestro (supervisor)**, fora do caminho da ordem, zero latência.
2. **Python = cérebro**: única linguagem com lib nativa MT5 (`MetaTrader5`), calcula e executa.
3. **Go não tem lib nativa de MT5** (L288-297) → não pode ser o executor.
4. **Princípios**: stateless, hydration 100 candles, MT5 = fonte da verdade, UTC, .env, log rotativo, heartbeat 1s/3s, crash-loop 3×2min, graceful shutdown.
5. **"Espera, o maestro não calcula"** — correção importante: Go supervisiona o fluxo, não os indicadores.

## Motor multi-sinal (aprofundado)
- Score + "juiz": elimina score 0, ordena `sorted(desc)`, executa só o 1º sinal.
- Filtros: RVOL, MTF, RRR ≥ 1.

## Observação
- O aprofundamento confirma a divisão de responsabilidades usada em `cebro-python.md` e `maestro-golang.md`.
- Reler `raw/aprofundamento.md` via RAG quando precisar do raciocínio completo (ex: "por que stateless", "por que 100 candles").
