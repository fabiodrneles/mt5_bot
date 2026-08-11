# MM21 e MM200 — Filtros e Contexto de Tendência

Fonte: `raw/estrategias-operacionais.txt` (médias móveis) · Status: parcialmente no código (`get_ema21`)

## MM21 (média de 21)
- Usada no **Ponto Contínuo** como suporte/resistência dinâmica (ver `ponto-continuo.md`).
- **Retorno à MM21**: compra no pullback (tendência de alta tocando a média).
- **Fura-teto**: rompimento da máxima anterior com preço acima da MM21.
- **Cruzamento de médias**: MM21 cruzando MM50/MM200.

## MM200 (média de 200)
- **Filtro maior de tendência**: preço acima da MM200 = viés de alta; abaixo = viés de baixa.
- No bot: `MTF_FILTER_ENABLED` — blocos de setup com viés contrário.
- Se o preço está **abaixo da MM200**, compras ficam restritas a correções fortes (ou são bloqueadas).
- MM200 atua como **suporte/resistência de longo prazo** — níveis de reversão importantes.

## MM50
- Tendência intermediária; usada no **IFR2** como filtro de direção (ver `ifr2.md`).
- Blocos de setup contra a MM50.

## MM13 e MM28
- Médias de **curto prazo** do Palex — referência para o IFR2 e o SAR (Machado).
- MM28 = aproximadamente o dobro da MM13 (relação harmônica).

## No código (estado atual)
- `indicators.py`: `get_ema21`, `get_ema9`, slopes, MM200 em MTF.
- `config.py`: `MTF_FILTER_ENABLED` — filtro de time frame maior habilitado.
- **Diferença a validar**: código usa EMA21 (exponencial); livro fala MM21 (simples). Confirmar qual usar no Ponto Contínuo.

## Observação de trading
- As médias funcionam melhor em **mercado tendencial**; em range geram whipsaw.
- Palex: "MM21 = ponto contínuo", "MM200 = mapa do território".
