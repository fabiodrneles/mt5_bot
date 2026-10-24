# Estado da pesquisa ampla (rodada 3) — ponto de retomada

> Atualizado a cada etapa e enviado ao GitHub (branch `research/estrategias-conta-16`).
> Se o terminal fechar ou a cota da IA acabar, **nada se perde**: cada etapa grava em disco e pula o que já fez.

## Como retomar (qualquer pessoa ou IA)

Com o MT5 aberto e logado, na pasta `tools/quant_research`:

```
python universe.py 16 25        # 1. universo (só se data/universe.json não existir)
python fetch2.py                # 2. baixa H1/D1; pula os arquivos que já existem
python fetch2.py --meta-only    # 2b. OBRIGATÓRIO depois do 2: regrava custos (comissão de ações) em data/meta2.json
python research2.py run 3       # 3. grade completa; pula os símbolos já gravados em data/r2_<TF>.jsonl
python pairs2.py                # 4. família de pares
python seasonal2.py             # 4b. padrões de horário/dia/data (FDR) -> data/s2.json
python leadlag2.py              # 4c. lead-lag entre ativos (A antecipa B) -> data/ll2.json
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

## Correções feitas durante a rodada (antes de qualquer aprovação)

1. **Comissão de CFDs de ações.** O lote mínimo é 0,1–1 ação, então $1/lote seria irreal. Passou a ser estimada em 0,1% do valor por lado (a API não informa e a conta não tem trade de ações). Rota em ações exige confirmar a comissão real antes de ir ao vivo.
2. **Spread do rollover.** Os candles são *bid* e o campo spread subestima o pico da virada do dia (AUDCAD: 3 pts normalmente, 19 na hora 0, 6 na hora 1). Isso criava falsos lucros em "comprar na hora 1" e "gap fade" no forex H1. Agora a entrada paga o maior spread entre o candle anterior e o de entrada, a recompra de venda paga o spread do fechamento, e o D1 paga o spread típico da hora de abertura do dia. Teste: `test_entry_pays_rollover_spread_of_previous_candle`.

3. **Abertura irreal do pregão (artefato de dados).** No H1 das ações, a cotação de abertura do 1º candle do pregão (hora 16 do servidor) vem ~$1 abaixo do fechamento anterior e o candle "sobe" o mesmo valor (LKQCorp 2023: +1,053 no candle × −1,096 na abertura). Ninguém compra nesse preço. Confirmado com M1 recente: na 1ª hora real o bid sobe em média só $0,018. Correção: o 1º candle depois de qualquer pausa entra pelo pior entre a abertura e o fechamento anterior (`research2.simulate` e `seasonal2`). Teste: `test_first_candle_after_pause_enters_at_worse_of_open_and_previous_close`.

4. **Rollover não precificável.** Depois da correção 3, sobraram 3 "padrões": comprar EURUSD/EURGBP na quinta à 0h. Com **ticks reais**, o spread do EURGBP entre 0h00 e 0h10 de quinta fica em 82–224 pts, enquanto o candle registra ~30, porque o campo spread do candle guarda o **mínimo** da hora. O bid afunda e o ask fica parado: artefato. Regra: nenhuma entrada na hora 0 do servidor em H1/H4 (`research2.simulate`, `seasonal2`). O motor real seguirá a mesma regra. Teste: `test_no_entry_in_rollover_hour`.

Os resultados da primeira passada, anteriores às correções, ficaram em `data/old/` e não valem.

## Resultados parciais (após as 4 correções de custo/dados; ~107 ativos baixados)

### Grade de 28 famílias (31.709 configurações)
- **Aprovadas nos 7 critérios: 0.** Promissoras (1–3 ok, caíram em 4–7): 17. Todas falham no DSR, e quase todas as de forex/cripto também na viabilidade com $16 (risco de $2–7 por trade, ruína 10–32%).
- Mais perto: **LKQCorp D1, comprar na sexta**: DSR 0,919 (N = configurações) / ~0,99 (N = células); walk-forward 5/5 positivo; risco $0,33; ruína 0%. Contra: generaliza só em 20/55 ações; comissão estimada; sem explicação econômica. **Caso de fronteira.**
- Pendente: decisão do dono sobre a faixa "experimental" (DSR 0,80–0,95 → só `/study` até repetir em trades novos).

### Pares (15 pares D1): todos perdem depois dos custos.
### Lead-lag (46 ativos, 12.420 cruzamentos): 0 no FDR.
### Sazonalidade (68.134 células hora × dia × ativo e dia do mês): 40 no FDR do IS, **0 aprovadas**. Os 64 → 3 → 0 "padrões" das varreduras anteriores eram artefatos (correções 3 e 4).

### Falta
- Terminar o download (forex de NZD em diante, cripto e índices restantes) e rodar de novo `research2.py run 3`, `analyze2.py`, `seasonal2.py`, `leadlag2.py` e `report2.py` (todos pulam o que já fizeram, exceto analyze/seasonal/leadlag/report, que são rápidos).
