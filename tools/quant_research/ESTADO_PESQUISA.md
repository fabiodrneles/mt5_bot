# Estado da pesquisa ampla (rodada 3) — ponto de retomada

> Atualizado a cada etapa e enviado ao GitHub (branch `research/estrategias-conta-16`).
> Se o terminal fechar ou a cota da IA acabar, **nada se perde**: cada etapa grava em disco e pula o que já fez.

## Como retomar (qualquer pessoa ou IA)

Com o MT5 aberto e logado, na pasta `tools/quant_research`:

```
python universe.py 16 25        # 1. universo (só se data/universe.json não existir)
python fetch2.py                # 2. baixa H1/D1; pula os arquivos que já existem
python research2.py run 3       # 3. grade completa; pula os símbolos já gravados em data/r2_<TF>.jsonl
python pairs2.py                # 4. família de pares
python analyze2.py              # 5. critérios 1–7 do PROTOCOLO2.md -> data/a2.json
python report2.py               # 6. gera RESULTADOS2.md (versionado) a partir de data/a2.json
```

Regras: o protocolo (`PROTOCOLO2.md`) foi registrado **antes** dos resultados e não muda. Nenhum script envia ordens.

## Etapas

| # | Etapa | Estado | Saída |
|---|---|---|---|
| 1 | Universo: 465 símbolos negociáveis, **337** com margem ≤ 25% de $16 | ✅ | `data/universe.json` |
| 2 | Download H1 + D1 (forex/índices/commodities/cripto primeiro, ações depois) | 🔄 em andamento | `data/*.npy`, `data/meta2.json` |
| 3 | Grade de 28 famílias × H1/H4/D1 | ⏳ | `data/r2_D1.jsonl`, `r2_H4.jsonl`, `r2_H1.jsonl` |
| 4 | Pares (15 pares, D1) | ⏳ | `data/r2_pairs.json` |
| 5 | Critérios 1–7 | ⏳ | `data/a2.json` |
| 6 | Relatório final | ⏳ | `RESULTADOS2.md` |

## Fatos já confirmados (não precisam ser refeitos)

- O simulador novo (`research2.py`) reproduz a pesquisa anterior: HK50 H4 PULLB 277 trades, +$9,93 (antes +$9,96); US500 D1 RSI2 54 trades, +$13,18 (antes +$13,19). A diferença vem da rolagem tripla do swap, agora correta.
- Testes: `tests/test_research2.py` (swap triplo, stop antes do alvo, *gap*, ausência de *look-ahead*).
- **Restrição da conta de $16 (medida no universo):** um ATR diário no lote mínimo custa $4–7 nos pares de forex principais (25–45% da conta). Forex só cabe em H1/H4 ou com stop curto. Índices como HK50 ($0,15 de margem) e JP225 ($0,40) e muitos CFDs de ações têm ATR diário abaixo de $1.

## Resultados parciais

(preenchido conforme as etapas terminam)
