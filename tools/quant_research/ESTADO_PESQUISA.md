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

Os resultados da primeira passada, anteriores às correções, ficaram em `data/old/` e não valem.

## Resultados parciais

### Grade de 28 famílias (93 ativos já baixados, 27.148 configurações)
- **Aprovadas nos 7 critérios: 0.** Passaram 1–3: 13; todas caíram no DSR (filtro de sorte) e/ou na viabilidade com $16. Detalhe em `RESULTADOS2.md`.
- Mais perto de passar: **LKQCorp D1, comprar na sexta-feira** (t 3,9; 5/5 dobras do walk-forward positivas; risco $0,33; DSR 0,865 < 0,95). Comissão de ações estimada.
- O "efeito segunda-feira" do AUDJPY/AUDCAD **era artefato** do spread de reabertura (62 pts × 3 normais) e sumiu com o custo real.

### Pares (arbitragem estatística, 15 pares D1)
- **Todos perdem depois dos custos** (ex.: USOIL/UKOIL −$44 OOS; FR40/EU50 −$33). Família descartada.

### Sazonalidade (48.804 células hora × dia × ativo e dia do mês)
- 254 passaram o FDR no IS; 64 também no OOS, estabilidade e custo 1,5×.
- **Quase todos estão na abertura de uma sessão** (hora 16 do servidor = abertura de Nova York nas ações; hora 0 de segunda nos pares AUD). Suspeita forte de artefato do *bid* deprimido por spread largo na abertura, o mesmo já visto no rollover. **Em verificação com ticks reais (bid/ask) antes de qualquer conclusão.**

### Lead-lag entre ativos (46 ativos, 12.420 cruzamentos A → B)
- **Nenhum passou no FDR.** Só 164 cruzamentos têm movimento médio maior que o spread, e nenhum é estatisticamente distinguível do acaso. O movimento de um par na última hora **não** antecipa outro par a ponto de pagar o custo.

### Sazonalidade (refazendo com a correção 3)
- Os 64 "padrões de horário" da primeira varredura eram, na maioria, o artefato da abertura irreal (correção 3). Recalculando.
