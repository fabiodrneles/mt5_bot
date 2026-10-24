# Roteiro de publicação e construção de autoridade

> Objetivo do autor (2026-10-24): construir nome, autoridade e relevância em **engenharia financeira** e **engenharia de software para o mercado de capitais** (em inglês, *financial engineering*, *quantitative finance*, *quant development*), usando o MT5Bot como portfólio e base de pesquisa. O autor também opera o próprio capital com o robô.

## Por que este projeto tem valor

1. **Resultado negativo honesto e raro.** São cerca de 130 mil combinações testadas com pré-registro, FDR, *walk-forward*, Deflated Sharpe e Monte Carlo de ruína (guia, cap. 14). A maior parte do conteúdo sobre robôs de trading mostra só o que deu certo.
2. **Contribuição original: seis artefatos de dados da corretora**, confirmados com M1 e ticks. Exemplos: a abertura irreal do pregão das ações e o campo `spread` do candle, que guarda o mínimo do período. Isso afeta qualquer pessoa que faz backtest no MT5.
3. **Engenharia auditável:** testes, CI em Windows/Ubuntu, simulador testado contra *look-ahead*, pipeline reproduzível e guia acadêmico com listagens de código verificadas.
4. **Material didático:** o estudo de caso da MME9 (cap. 14 §14.8) mostra como uma regra que parece óbvia no gráfico se comporta sob teste rigoroso.

## Caminho prático

| # | Entrega | Onde | Base no projeto |
|---|---|---|---|
| 1 | **Preprint** (artigo técnico em inglês) | SSRN e/ou arXiv (q-fin.TR ou q-fin.ST) | `docs/publicacao/artigo-data-artifacts.md` (rascunho), cap. 14 |
| 2 | **Série de textos curtos**, um por descoberta, com gráfico e link para o código | LinkedIn, Medium ou blog próprio | Cap. 14 §14.4 (artefatos), §14.8 (MME9), cap. 8 (metodologia) |
| 3 | **Versão em inglês** do README e do cap. 14 | GitHub | — |
| 4 | **Histórico ao vivo transparente**: o que o robô fez × o que o simulador previa, inclusive os meses ruins | GitHub e textos periódicos | Rotas US500/HK50, modo estudo (US100), spec 011, diário de sinais |
| 5 | **Pacote de reprodução**: código, protocolo e instruções (sem dados brutos) | GitHub (tag/release) e Zenodo (DOI gratuito) | `tools/quant_research/`, `pipeline2.py`, `PROTOCOLO2.md` |
| 6 | **Formação formal** (opcional): mestrado em engenharia financeira, econometria ou ciência de dados aplicada | — | O cap. 14 e as specs 009–011 servem de proposta de pesquisa |

Sugestões de textos para a série:
- "O candle de abertura que mente: um defeito de dados que fabrica estratégias" (A4/A6).
- "O spread que o candle esconde" (A5, ticks do EURGBP).
- "Por que a MME9 parece funcionar no gráfico" (§14.8).
- "130 mil backtests: o que sobra depois do custo e da sorte" (§14.6).
- "Pré-registro em pesquisa de estratégias: o protocolo que impede você de se enganar" (§14.2).
- "Uma estratégia que sobreviveu: RSI2 nos índices americanos" (§14.9).

## Cuidados

- **Não publicar dados brutos da corretora** (candles e ticks): podem ter restrição de uso. Publique código e metodologia; quem quiser reproduz com a própria conta.
- **Pesquisa não é recomendação de investimento.** Divulgar método, código e resultados com aviso explícito é o caminho seguro. Publicar recomendações recorrentes ("compre X") pode exigir certificação de analista (CNPI) e está sujeito à regulação da CVM; gerir dinheiro de terceiros exige autorização. Na dúvida, consultar um advogado da área.
- **Honestidade sobre limitações** (cap. 13 e §14.12): ela é o que dá credibilidade.
- **Declarar o uso de IA** no desenvolvimento e na escrita, e como a correção foi verificada (testes, CI, revisão humana), conforme o Apêndice C.
