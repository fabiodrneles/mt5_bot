# Fonte: Fundamentos de Análise Técnica de Ações (Palex)

> PDF original: `palex-fundamentos-de-analise-tecnica-de-aoes_compress.pdf`
> Texto extraído: `raw/fundamentos.txt` (836KB, ~33.818 linhas)

## Sobre
Livro de **fundamentos** de análise técnica de Alexandre Fernandes (Palex). Foca no "porquê": gestão de risco, expectativa matemática, plano de trade, psicologia.

## Conteúdo (destilado)
- **Plano de trade** (p.301, ~L31882) → `conceitos/plano-de-trade.md`
- **Trading systems** (p.312, ~L32959) → `conceitos/plano-de-trade.md` (sistematização)
- **Expectativa matemática** (p.317-318, ~L33559) → `conceitos/expectativa-matematica.md`
- **Gestão de risco** (1%, breakeven, saída parcial) → `conceitos/gestao-de-risco.md`

## Pontos-chave do livro
1. **>90% dos traders perdem** porque não seguem plano de trade.
2. **Nunca operar expectância negativa** (regra de ouro).
3. **Proteja o capital primeiro** — o lucro é consequência.
4. **Sistema perfeito não existe** — consistência > perfeição.
5. **Stop barato/alta rentabilidade**: muitas perdas pequenas, poucos ganhos grandes = E alto.
6. **Operar todos os sinais** — seleção manual destrói a estatística.
7. **Espera**: pular operações de E marginal melhora resultado global.

## Conexão com o bot
- O `risk_calculator.py` materializa a regra do 1%.
- `metrics.py` (Fase 1) computará a **expectância real** do sistema operado.
- O bot é a **materialização do plano de trade** em código.
