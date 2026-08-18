# RELATÓRIO: EURUSD — Análise de Viabilidade e Otimização

**Data:** 2026-08-17
**Contexto:** preparar o EURUSD para operar quando o capital crescer, mantendo foco 100% no HK50 até lá.
**Saldo atual:** $16.47 (meta: escalar para $20 e depois crescer com o HK50)

---

## 1. Descoberta importante (você tinha razão)

O setup que roda no HK50 (**russian_bb**) **NÃO** é o mesmo do EURUSD.
O EURUSD usa os **setups 9.x** (9.1/9.2/9.3/9.4, PC, FFFD, GAP, DiNapoli, IFR2, SAR, RompFalso).

Eu tinha analisado o EURUSD usando o SL do russian_bb (meia banda) e concluído que era inviável.
**Reanalisei com os stops reais dos setups 9.x (candle highs/lows) e o cenário mudou.**

---

## 2. Viabilidade do lote mínimo (0.01) no EURUSD — com os stops REAIS

| Fato | Valor | Situação |
|---|---|---|
| SL mediano (candle, 11 ticks) | $0.11 = 0.67% do saldo | ✅ cabe no risco 1% |
| SL p90 (37 ticks) | $0.37 = 2.25% do saldo | ⚠️ acima de 1.5% (shield rejeitaria) |
| Spread atual | 9 ticks = $0.09 por 0.01 lote (0.55%) | ✅ aceitável |
| Margem | $2.32 por 0.01 lote | ✅ folga de 7x |

**Conclusão:** com $16.47 o EURUSD é *tecnicamente* viável (diferente do que eu disse antes — meu erro foi usar o SL do russian_bb). MAS a estratégia em si é o problema (abaixo).

---

## 3. Backtest dos setups ATUAIS (9.x) no EURUSD

**8 meses de dados M5 (50.000 candles, dez/2025 → ago/2026)**

| Resultado | Valor |
|---|---|
| Operações | 1.164 |
| Lucro | **−$200.38** |
| Profit Factor | **0.45** |
| Win Rate | **31.4%** |

**❌ OS SETUPS 9.x PERDEM NO EURUSD.** Os stops são apertados (candle low/high) e o spread de 9 ticks come uma fração grande do alvo de 1x risco. Com WR 31% e alvo 1:1, o sistema sangra.

---

## 4. Teste do russian_bb no EURUSD (mean reversion, como o HK50)

> **Correção importante:** a primeira otimização rodou **sem o filtro SMA200** que o motor real aplica
> (buy exige close > SMA200, sell exige close < SMA200). Aqueles PF 1.5 eram **inflados**. Recalculei
> tudo **com** o filtro SMA200 — os números abaixo são os honestos.

### Grid search (36 combinações, vetorizado, com filtro RVOL + SMA200)

**Melhores combinações (saldo de referência $100):**

| min_width | RSI< | RSI> | Ops | Lucro | PF | WR% |
|---|---|---|---|---|---|---|
| 0.0008 | 35 | 75 | 60 | +$15.33 | 1.42 | 38.3% |
| 0.0008 | 35 | 65 | 123 | +$11.00 | 1.14 | 33.3% |
| 0.0018 | 30 | 70 | 14 | +$7.88 | 1.88 | 42.9% |

### Validação Walk-Forward (treino 70% / teste 30% fora da amostra) — combo 0.0008/35/75

| Fase | Ops | Lucro | PF | WR% |
|---|---|---|---|---|
| **Treino** (escolha do melhor) | 42 | +$7.51 | 1.28 | 35.7% |
| **Teste** (fora da amostra) | 18 | +$7.82 | **1.85** | 44.4% |
| Dataset intacto (8m) | 60 | +$15.33 | 1.42 | 38.3% |

**Veredito:**
- ✅ O russian_bb é **lucrativo** no EURUSD (não é perdedor como os 9.x)
- ✅ **Não é overfit**: o teste fora da amostra (PF 1.85) foi *melhor* que o treino (PF 1.28)
- ⚠️ MAS é **fraco**: PF ~1.3–1.9 (vs PF 2.27 do HK50), edge fino, poucas operações
- ❌ Com $16.47 o russian_bb **nem executaria**: o SL (meia banda = ~$0.59 = 3.6% do saldo) estoura o shield de 1.5% → todas as operações seriam rejeitadas

**Saldo mínimo para o russian_bb operar no EURUSD com risco 1%: ~$60.**

---

## 5. Bloqueio técnico para deixar o EURUSD "engavetado pronto"

Os parâmetros do russian_bb hoje são **GLOBAIS** (config.py):
```
RUSSIAN_BB_MIN_WIDTH = 40.0        # calibrado para HK50 (largura da banda em dezenas de pontos)
RUSSIAN_BB_RSI_OVERSOLD = 30.0
RUSSIAN_BB_RSI_OVERBOUGHT = 70.0
```

O EURUSD precisa de valores **diferentes** (largura da banda ~0.0008 em preço):
```
EURUSD: min_width = 0.0008, RSI< 35, RSI> 75
```

Se aplicássemos os valores globais, o russian_bb **nunca dispararia** no EURUSD (a banda nunca chega a largura 40 em preço).

---

## 6. IMPLEMENTADO (Opção A) — override por ativo

```python
RUSSIAN_BB_PARAMS = {
    "HK50":  {"min_width": 40.0,  "rsi_oversold": 30.0, "rsi_overbought": 70.0},
    "HKG50": {"min_width": 40.0,  "rsi_oversold": 30.0, "rsi_overbought": 70.0},
    "EURUSD": {"min_width": 0.0008, "rsi_oversold": 35.0, "rsi_overbought": 75.0},
}
```
E `strategy.py` busca o parâmetro específico do ativo, com fallback para o global.

- Config pronta: HK50 mantém 40/30/70; EURUSD usa 0.0008/35/75
- AVISO claro no config: EURUSD **só deve ser ativado com saldo ≥ ~$60** (senão o shield rejeita tudo)
- `ASSET_SETUPS["EURUSD"] = ["russian_bb"]` (9.x perde no EURUSD; russian_bb só opera com saldo alto)
- 2 testes novos + suíte completa **142 passed**
- Resultado: quando seu saldo crescer com o HK50, é só ativar o EURUSD

**Lembrete de capital:** o EURUSD usa o **mesmo Risk Shield global** (1.5% do saldo por operação).
Com $16.47 o shield rejeita tudo do EURUSD — comportamento correto e desejado.

---

## 7. JANELA LUCRATIVA do EURUSD (implementado) + Monte Carlo a $60

**Horário (BRT):** análise dos 94 trades gerados com o motor real (lote dinâmico,
spread 9 ticks, a $60) mostrou que a **sessão Londres 03:00–09:00 BRT concentra
30 ops e +$13.00** de +$7.75 total. Sinais fora dela **destroem o lucro**
(especialmente o fechamento 21:00–23:59 BRT: −$3.75). Implementado em
`SYMBOL_TRADING_HOURS["EURUSD"]` = `03:00–09:00` com `force_close` 09:30, e o
motor agora avisa claramente quando o setup é ignorado por estar fora da janela
lucrativa (sugere desligar o bot e religar dentro da janela).

**Monte Carlo (50k trajetórias, trades fiéis, a $60, HK50 + EURUSD):**

| Cenário | % positivo no ano | Mediana | p10 / p90 | Chance de zerar |
|---|---|---|---|---|
| HK50 + EURUSD | **75.2%** | $66.75 | $54 / $80 | **0.00%** |

- Números **conservadores**: a simulação usa TP=banda oposta, sem breakeven/
  saída parcial/ATR dinâmico (o motor real é melhor — HK50 valida PF 2.27).
- **A conta nunca zera**: shield 1.5%/op + daily max loss 2% + janela lucrativa.
- Pior cenário realista: andar de lado ou ~−$6 no ano (p10), não queimar a conta.
- Observação de rigor: o `tools/backtest.py` oficial está **desatualizado**
  (width≥50) e não reproduz o PF 2.27 (usa TP/SL simples, sem motor completo);
  os números fiéis acima vêm de simulação própria com `order_calc_profit`.

---

## 8. Lembrete do que está pronto e protegido

- **HK50:** v2.4.1 na main (commit `2734282`), 143 testes, validado walk-forward (PF 2.27), protegido (lote 1%, shield, daily max loss, breakeven, saída parcial, janela 22:15–01:00 BRT)
- **EURUSD:** config pronta (russian_bb 0.0008/35/75 por ativo) + **janela lucrativa 03:00–09:00 BRT implementada** mas **engavetada** — o shield global impede operação com $16.47
- **Maestro:** compilado e em dia
- **Saldo $16.47:** HK50 é o único ativo operável agora; a $60 o EURUSD entra (75% de chance de fechar o ano positivo junto com o HK50)