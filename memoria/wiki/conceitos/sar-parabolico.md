# SAR Parabólico (Machado) — SAR + IFR(14) + MM13

Fonte: `raw/estrategias-operacionais.txt` (Machado) · Status: planejado para Fase 2

## Regras
1. **SAR Parabólico** (0.2, 0.02) usado como **filtro de direção** — pontos sob o preço = alta, sobre = baixa.
2. **IFR(14)** para confirmar força (evitar divergências).
3. **MM13** como referência de tendência.
4. **Stop**: pelo **cruzamento do IFR** (não pelo SAR).

## Ponto-chave
- O SAR é **parabólico** — acelera o stop conforme o preço se move.
- Palex usa o SAR como **confirmador**, não como gatilho.
- **Stop por cruzamento do IFR(14)** é a peculiaridade: o stop acompanha o sinal do oscilador.
- Parâmetros: aceleração inicial 0.02, máximo 0.2 (padrão Welles Wilder).

## No código (planejado)
- `indicators.py`: SAR parabólico (0.2, 0.02), IFR(14), MM13.
- `strategy.py`: `check_sar_buy/sell` na Fase 2.

## Observação de trading
- Ótimo para **gerenciamento de stop dinâmico** (trailing) combinado com setups de entrada.
- Não usar sozinho — ruidoso em mercado lateral.
