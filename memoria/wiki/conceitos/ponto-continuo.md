# Ponto Contínuo (MM21 como âncora)

Fonte: `raw/estrategias-operacionais.txt` · Status: planejado para Fase 2

## Regras (COMPRA)
1. **Contexto**: MM21 (média móvel simples de 21) **ascendente**.
2. **Toque**: o preço toca a MM21 (pullback na média).
3. **Ponto**: marca-se a **máxima do candle de toque** — este é o "ponto contínuo".
4. **Entrada**: rompimento da máxima do candle de toque + 1 tick.
5. **Deslocamento**: se o preço cair mais (tocar a MM21 de novo) **sem** romper abaixo da MM21, o ponto **desloca** para a máxima do novo candle de toque.
6. **Stop**: mínima do candle de toque.

## Regras (VENDA) — simétrico
- MM21 descendente; ponto na mínima do candle de toque; venda no rompimento da mínima − 1 tick; stop na máxima.

## Ponto-chave
- A MM21 funciona como **âmbar de suporte dinâmico** — não é uma média "mágica", é um nível onde o mercado tende a reagir.
- O setup é "contínuo": enquanto a MM21 não for rompida, cada toque gera um novo ponto.
- **Cancelamento**: rompimento da MM21 na direção oposta anula o setup.
- Funciona melhor em mercados **tendenciais**; em ranges gera muitos stops.

## No código (planejado)
- `indicators.py`: já existe `get_ema21` (MM21 exponencial) — avaliar necessidade de SMA21 pura.
- `strategy.py`: `check_ponto_continuo_buy/sell` na Fase 2.

## Observação de trading
- Palex: setup de "estar sempre no mercado" na direção da MM21.
- Combinar com filtro de tendência maior (MM200).
