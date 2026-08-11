# Expectativa Matemática — Pay Off e Regra de Ouro

Fonte: `raw/fundamentos.txt` (p.317-318) · Status: fundamento do `risk_calculator.py`

## Fórmulas
```
E = (%acerto × GanhoMédio) − (%erro × PerdaMédia)

Pay Off = GanhoMédio / PerdaMédia

E = ((1 + PayOff) × p) − 1
```
onde `p` = probabilidade de acerto.

## Interpretação
- **E > 0**: sistema lucrativo no longo prazo.
- **E = 0**: empate (apenas recupera perdas).
- **E < 0**: sistema perdedor — **nunca operar**, não importa quão bons pareçam os setups.

## Regra de ouro (dita pelo Palex)
> **"Nunca opere com expectância negativa."** Todo sistema com E < 0 será destruído pela variância e pelo tempo.

## Aplicação no bot
- `risk_calculator.py`: calcula risco por operação com base no **risco por trade** (% do capital).
- `metrics.py` (Fase 1, planejado): acumular estatísticas reais → computar E real do sistema → **só dar sinal se E observado > 0**.
- Expectância é **métrica de sistema inteiro**, não de trade individual.

## Conceitos derivados
- **Stop barato/alta rentabilidade**: sistemas com muitas perdas pequenas e poucos ganhos grandes têm E alto.
- **Sistema perfeito não existe** — o objetivo é E positivo consistente, não 100% de acerto.
- **Espera** (ver `plano-de-trade.md`): pular operações de E marginalmente positivo melhora o resultado global.

## Observação
- Pay Off de 2 com 40% de acerto → E = (3×0.4)−1 = +0.2 (positivo).
- Pay Off de 1 com 50% → E = 0 (empate) — sem valor após custos.
