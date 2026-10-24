# 13. Validade, limitações, ética e trabalhos futuros

Um trabalho acadêmico sobre este projeto precisa dizer não só o que foi feito, mas **até onde as conclusões valem**. Este capítulo organiza as limitações espalhadas pelo manual na classificação clássica de ameaças à validade [Shadish, Cook & Campbell 2002], adaptada à engenharia de software experimental [Wohlin et al. 2012], e termina com questões éticas e uma agenda de trabalhos futuros.

## 13.1 Ameaças à validade

### Validade de conclusão (a estatística sustenta a afirmação?)

| Ameaça | Onde aparece | Mitigação aplicada | O que falta |
|---|---|---|---|
| Amostras pequenas | RSI2MR: 54 trades em 9,5 anos | Estatística t, sensibilidade de parâmetros, generalização entre ativos | Intervalos de confiança por *bootstrap* do lucro por trade |
| Comparações múltiplas | 3.150 combinações testadas (cap. 8) | Robustez da família, teste de permutação | *Deflated Sharpe Ratio* [Bailey & López de Prado 2014]; probabilidade de *overfitting* [Bailey et al. 2017] |
| Inferência com 3 amostras | Supervisor adaptativo (cap. 7 §7.5) | Nenhuma | Amostra mínima maior e correção para múltiplos testes |
| Métrica inadequada no ML | Acurácia em vez de expectativa (cap. 7 §7.4) | ML não é usado nas rotas quant | Avaliar por expectativa dos trades aprovados |

### Validade interna (o efeito medido é causado pela regra?)

| Ameaça | Mitigação | Evidência |
|---|---|---|
| *Look-ahead bias* | Só candles fechados; entrada em $t+1$ | cap. 3 §3.2, cap. 8 §8.3 |
| Execução diferente do teste | Equivalência de sinais vela a vela: 0 divergências | cap. 8 §8.8 |
| Custos subestimados | *Spread* por candle, comissão real, *swap*; estresse 1,5× | cap. 8 §8.2 |
| Ordem de SL e TP no mesmo candle | Hipótese pessimista (stop primeiro) | cap. 8 §8.3 |
| Vazamento temporal no ML | **Não mitigado**: separação aleatória | cap. 7 §7.4 |

### Validade externa (vale fora do que foi testado?)

- **Entre ativos:** o PULLB lucra só no HK50 e perde em 8 de 9 índices; o RSI2MR generaliza para 6 de 8. A primeira afirmação é **local**; a segunda, mais geral.
- **No tempo:** pela hipótese dos mercados adaptativos [Lo 2004], vantagens se desgastam. O período fora da amostra termina na data da coleta; nada garante o futuro.
- **Entre corretoras:** *spreads*, comissões, *swaps* e horários são da corretora usada. Outra corretora é outro experimento.
- **Entre tamanhos de conta:** o lote mínimo domina contas pequenas; com mais capital, o dimensionamento muda e a execução pode sofrer *slippage* diferente.

### Validade de construto (medimos o que queríamos medir?)

- "Lucro no lote mínimo" mede a vantagem por contrato, não o retorno sobre o capital de um investidor real.
- "Queda máxima" num único caminho histórico subestima a queda possível; simulações de Monte Carlo por reamostragem dos trades dariam uma distribuição.
- O "score" do caminho clássico (cap. 5 §5.4) é um construto de especialista: não foi demonstrado que score maior signifique retorno maior.

## 13.2 Limitações técnicas conhecidas

Reunidas dos capítulos, por gravidade para quem opera:

| Limitação | Efeito | Capítulo | Correção sugerida |
|---|---|---|---|
| Piso de 0,5% no meio Kelly mesmo com $f^* \le 0$ | Pode arriscar quando o modelo diz que não há vantagem | 6 §6.2 | Rejeitar o trade se $f^* \le 0$ |
| ML *fail-open* | Modelo quebrado vira "sem filtro" em silêncio | 7 §7.3 | Alerta visível ou *fail-closed* configurável |
| Saída parcial de 50% com lote 0,01 | Nunca acontece em contas pequenas | 6 §6.5 | Desativar ou exigir lote ≥ 2 × mínimo |
| Vários simuladores | Resultados podem divergir | 12 §12.5 | Consolidar sobre o simulador de referência |
| Uma única separação IS/OOS | Menos robusta que *walk-forward* | 8 §8.9 | *Walk-forward* ou validação purgada [López de Prado 2018] |
| *Swap* aproximado por dias de calendário | Erra o dia da rolagem tripla | 8 §8.9 | Ler o dia de rolagem tripla do símbolo |
| Pacote Linux/macOS via Wine | Depende da versão do Wine; terminal MT5 não testado no CI | 10 §10.6 | Testar com terminal MT5 real no Wine |

## 13.3 Questões éticas e regulatórias

- **Não é recomendação de investimento.** O projeto é material de estudo. Resultados de backtest não garantem resultados futuros, e a evidência sobre o varejo é desfavorável (cap. 0 §0.5).
- **Consentimento informado.** A confirmação explícita de conta REAL (cap. 6 §6.6) e o padrão "só simulação" para setups não validados existem para que ninguém opere dinheiro real por engano ou sem conhecer o risco.
- **Regulação.** CFDs e alavancagem são regulados de formas diferentes em cada país. Na União Europeia, a alavancagem para varejo é limitada desde 2018 [ESMA 2018]. No Brasil, cabe ao usuário verificar se a corretora está autorizada a atender residentes; a Comissão de Valores Mobiliários publica alertas sobre ofertas irregulares.
- **Transparência.** Os resultados negativos (histórico real de −$33,18 nos setups clássicos, combinações com fator de lucro 0,45, a rota que não generaliza) estão documentados com o mesmo destaque dos positivos. Omitir resultados negativos é uma forma de viés de publicação.
- **Uso de IA no desenvolvimento.** Parte do código e da documentação foi produzida com assistentes de IA, guiados pela memória RAG (cap. 11) e pelo processo SDD (cap. 10). Em trabalhos acadêmicos, convém declarar isso e descrever como a correção foi verificada: testes, CI e revisão humana.

## 13.4 Trabalhos futuros

Ordenados pelo valor científico esperado:

1. **Validação mais forte das rotas:** *walk-forward* com várias janelas, *Deflated Sharpe Ratio* e *bootstrap* dos trades.
2. **Acompanhamento ao vivo como experimento:** comparar, trade a trade, o resultado real com o que o simulador previa para os mesmos candles (*tracking error* entre teste e realidade).
3. **ML sem vazamento:** separação cronológica ou validação purgada com embargo, avaliação por expectativa e calibração de probabilidades [Niculescu-Mizil & Caruana 2005].
4. **Calibrar os pesos do scoring** a partir de dados fora da amostra, ou substituí-los por um modelo calibrado.
5. **Corrigir o Kelly com $f^* \le 0$** e cobrir com teste.
6. **Unificar os simuladores** sobre o núcleo de referência.
7. **Gestão de carteira:** risco agregado quando várias rotas operam ao mesmo tempo (correlação entre índices).
8. **Verificar o pacote Wine com o terminal MT5** instalado de verdade.

## 13.5 Referencial teórico

[Shadish, Cook & Campbell 2002] tipos de validade; [Wohlin et al. 2012] validade em engenharia de software experimental; [Bailey & López de Prado 2014; Bailey et al. 2017; López de Prado 2018] validação em finanças; [Lo 2004] não estacionariedade das vantagens; [Niculescu-Mizil & Caruana 2005] calibração; [ESMA 2018] regulação de CFDs.
