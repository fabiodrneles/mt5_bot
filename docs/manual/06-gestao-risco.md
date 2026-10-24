# 6. Gestão de risco

Em trading algorítmico, o risco é o componente que decide se o sistema **sobrevive** tempo suficiente para que uma vantagem estatística se manifeste [Vince 1990; Tharp 2008]. O projeto aplica **defesa em profundidade**: várias camadas independentes, cada uma capaz de impedir uma perda grande mesmo que outra falhe. É o modelo do "queijo suíço" de [Reason 1990].

## 6.1 Dimensionamento de posição (caminho clássico)

`mt5bot/risk/risk_calculator.py:calculate_position_size`:

1. **Risco-alvo em dinheiro:** $R = \text{saldo} \times r\%$, com $r = 1\%$ por padrão (`MAX_RISK_PER_TRADE_PERCENT`), ou o Half-Kelly (§6.2).
2. **Perda por lote** no stop: $\ell = \frac{|E - S|}{\text{tick\_size}} \times \text{tick\_value}$, substituída por `order_calc_profit(lado, ativo, 1.0, E, S)` quando disponível. A API devolve o valor **na moeda da conta**, corrigindo o caso de ativos cotados em outra moeda (HK50 em HKD numa conta em USD).
3. **Lote:** $q = \lfloor (R/\ell)/\text{step} \rfloor \times \text{step}$, limitado a [volume mínimo, volume máximo]. Arredondar **para baixo** garante que o risco efetivo nunca passe do alvo, salvo pelo piso do volume mínimo.
4. **Risk Shield:** se $q \times \ell >$ 1,5% do saldo (`ABSOLUTE_MAX_TRADE_RISK_PERCENT`), a ordem é **rejeitada**. Isso cobre exatamente o caso do piso: quando o lote mínimo já arrisca demais, não opera.
5. **Spread trap:** rejeita se a distância do stop for menor que 1,5 × spread (`MIN_STOP_SPREAD_MULTIPLIER`), porque o stop seria atingido pelo próprio custo de entrada.

**Fundamentação.** É o **risco fixo fracionário** (*fixed fractional*): arriscar uma fração constante do capital torna a ruína teoricamente assintótica, já que a aposta encolhe junto com o saldo [Vince 1990; Tharp 2008].

## 6.2 Critério de Kelly (Half-Kelly)

Quando o modelo de ML fornece a probabilidade de acerto $p$ e o setup tem alvo (RRR $b$), `calculate_dynamic_kelly_risk` usa:

$$f^* = p - \frac{1-p}{b}, \qquad f_{\text{usado}} = \text{clamp}\Big(\tfrac{f^*}{2},\; 0{,}5\%,\; 2{,}0\%\Big)$$

$f^*$ é a fração de Kelly, que maximiza o crescimento logarítmico esperado do capital [Kelly 1956; Thorp 2006]. Usa-se **metade de Kelly** porque $p$ é uma estimativa com erro: apostar o Kelly cheio sobre um $p$ superestimado leva a *drawdowns* severos, enquanto meio Kelly preserva cerca de 75% da taxa de crescimento com variância muito menor [MacLean, Thorp & Ziemba 2011].

**Limitação (análise crítica).** O piso de 0,5% faz o sistema **arriscar mesmo quando $f^* \le 0$**, isto é, quando o próprio modelo diz que não há vantagem. Pela teoria de Kelly, a aposta ótima com $f^* \le 0$ é **zero**. Na prática o veto de ML (probabilidade < 0,40) bloqueia boa parte desses casos antes, mas não todos: com $b = 3$ e $p = 0{,}2$ (aprovado se o limiar fosse menor), $f^* = -0{,}067$. Uma correção seria rejeitar a operação quando $f^* \le 0$.

## 6.3 Travas das rotas quant

`quant_manager._scan_quant` não usa Kelly. Usa **lote mínimo fixo**, para reproduzir o teste, e duas travas próprias:

- **Risco por trade:** perda no SL com o lote mínimo ≤ `max_risk_pct` da rota (ou `QUANT_MAX_RISK_PCT` = 2%) × saldo. Com saldo de $16,26, o HK50 arrisca ~$0,21 (limite de $0,33) e opera; o US500 arrisca ~$1,62 e só opera porque a rota tem limite próprio de 12% ($1,95), por decisão explícita do dono.
- **Reserva de margem:** a margem livre restante precisa ser ≥ 3 × a margem da posição (`QUANT_MARGIN_RESERVE_MULT`). Isso evita usar toda a margem numa operação e ficar sem capacidade para as próximas.

**Por que limite por rota?** Rotas diferentes têm stops com magnitudes muito diferentes (1 ATR no H4 contra 2 ATR no D1). Um limite global único ou bloqueia a rota de stop largo ou é frouxo demais para a de stop curto.

## 6.4 Perda diária máxima

`MAX_DAILY_LOSS_PERCENT` = 2%. Quando o resultado do dia (realizado + flutuante) chega a −2% do saldo:
- **novas entradas** ficam bloqueadas (clássico e quant);
- no caminho clássico, a posição aberta é **liquidada** (`DAILY_MAX_LOSS_CLOSE_ENABLED`).

Funciona como um disjuntor diário: limita os dias catastróficos, como uma sequência de stops num regime adverso, ao custo de eventualmente perder a recuperação no mesmo dia.

## 6.5 Gestão da posição aberta (caminho clássico)

`execution_manager._manage_position`:

| Mecanismo | Regra | Parâmetro |
|---|---|---|
| Saída parcial | Fecha 50% quando o lucro chega a 1 ATR (se o volume permitir) | `PARTIAL_EXIT_PERCENT`, `PARTIAL_EXIT_TARGET` |
| Breakeven | Com lucro ≥ 1 ATR, move o SL para entrada ± (spread × 1 + 1 tick) | `BREAKEVEN_ATR_RATIO`, `BREAKEVEN_LOCK_SPREAD_MULT` |
| Trailing | Modo `atr`: SL = fechamento ∓ 1,5 ATR, só a favor | `TRAILING_MODE` |
| EMA9 contra | SL vai para a mínima do candle; se o preço já passou dela, fecha a mercado | — |
| Fim de sessão | Liquida fora da janela do ativo | `SYMBOL_TRADING_HOURS` |

**Por que o breakeven tem "trava"?** Com o stop no preço exato de entrada, a saída devolve o spread e paga a comissão: o "empate" vira um prejuízo pequeno e sistemático. A trava de spread + 1 tick faz o empate sair no positivo (correção da v2.9.1).

**Limitação.** Com o lote de 0,01, a saída parcial de 50% (0,005) fica abaixo do lote mínimo e **nunca acontece**. Essa limitação está documentada desde a auditoria da v2.9.1.

## 6.6 Confirmação de conta REAL

Uma conta REAL só abre posições depois que o usuário roda o assistente (`bot.bat setup`), vê o risco de cada rota no próprio saldo e digita `CONFIRMO`; a confirmação fica em `live_confirmed = true` (spec 006). É uma **barreira de consentimento informado** contra o erro mais caro possível, que é operar dinheiro real por engano achando que era demo. Contas DEMO operam direto.

## 6.7 Proteções de execução

- **Spread máximo:** a ordem é abortada se o spread passar do limite do ativo (`SYMBOL_MAX_SPREAD_POINTS`; HK50 = 500 pontos).
- **SL/TP do lado errado:** no envio a mercado, `executor.place_market_order` aborta se o preço andou além do SL ou do TP calculados, porque a corretora recusaria a ordem (*invalid stops*).
- **Stops level:** a rota quant rejeita o sinal se o stop estiver mais perto que o mínimo da corretora.

## 6.8 Botões de emergência

`tools/panic.py` (`bot.bat panic`) e `shutdown_manager` (`/quit close-all|wait-flat|cancel-open`) fecham ou cancelam **apenas** o que tem o *magic* do robô (`config.MAGIC`). Antes da v2.12/2.13, o pânico procurava uma configuração inexistente e não fechava nada, e o `close-all` fecharia também as posições manuais. Ambos os defeitos são hoje cobertos por testes (`test_panic`, `test_shutdown_manager`).

## 6.9 Referencial teórico

[Kelly 1956] critério de Kelly; [Thorp 2006; MacLean, Thorp & Ziemba 2011] Kelly fracionário; [Vince 1990; Tharp 2008] dimensionamento de posição; [Reason 1990] defesa em profundidade; [Leveson 2011] engenharia de segurança de sistemas (restrições de segurança como requisitos de controle).
