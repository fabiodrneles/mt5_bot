# Apêndice C. Uso acadêmico

Este apêndice orienta quem vai usar o MT5Bot como objeto de estudo: o que ler conforme a área, que perguntas de pesquisa o projeto permite investigar e como citá-lo.

## C.1 Roteiros de leitura por área

| Área | Capítulos, nesta ordem | Foco |
|---|---|---|
| Engenharia de software | 1, 12, 2, 3, 10, 9, 13 | Arquitetura multiprocesso, supervisão, *stateless*, testes, CI/CD, SDD |
| Ciência da computação / IA | 1, 12, 7, 11, 8, 13 | ML tabular, vazamento temporal, RAG lexical, validação |
| Economia / finanças | 0, 5, 8, 6, 13 | Eficiência de mercado, anomalias, custos, *overfitting*, dimensionamento |
| Estatística | 0, 8, 7, 13 | Comparações múltiplas, testes de permutação, calibração |
| Sistemas de informação / gestão | 0, 1, 6, 9, 13 | Risco operacional, consentimento, interfaces, ética |

Leitura mínima para qualquer área: cap. 0 §0.6, cap. 1 e cap. 12 dão a visão do todo em cerca de uma hora.

## C.2 Perguntas de pesquisa que o projeto sustenta

Cada pergunta tem dados ou código prontos no repositório e uma lacuna documentada no cap. 13:

1. **Validação de estratégias:** o *Deflated Sharpe Ratio* das rotas quant continua significativo depois de descontar as 3.150 tentativas? (cap. 8, 13 §13.1)
2. **Teste versus realidade:** quanto o resultado ao vivo das rotas se desvia do previsto pelo simulador nos mesmos candles? (cap. 8 §8.8, 13 §13.4)
3. **ML com e sem vazamento:** quanto a acurácia do filtro XGBoost cai ao trocar a separação aleatória por uma separação cronológica ou purgada? (cap. 7 §7.4)
4. **Custo dos filtros:** com amostra maior e correção para múltiplos testes, os vetos do caminho clássico destroem ou preservam valor? (cap. 7 §7.5)
5. **Arquitetura:** qual a disponibilidade medida do sistema com supervisão e *stateless*, comparada a um processo único com estado em memória? (cap. 1, 2)
6. **Recuperação de informação:** BM25 contra *embeddings* leves numa base técnica em português, com hardware de 4 GB. (cap. 11)

## C.3 Como descrever o projeto num trabalho

Uma estrutura que segue a ordem do manual:

| Seção do trabalho | Base no manual |
|---|---|
| Introdução e problema | cap. 0 §0.1, cap. 1 §1.1 |
| Referencial teórico | cap. 0 inteiro; §"Referencial teórico" de cada capítulo |
| Metodologia | cap. 8 (pesquisa), cap. 10 (processo de desenvolvimento) |
| Arquitetura e implementação | cap. 1, 12, depois 2 a 7 conforme o foco |
| Resultados | cap. 8 §8.7 |
| Discussão e limitações | cap. 13 |
| Reprodutibilidade | Apêndice B |

## C.4 Como citar

> DORNELES, F. *MT5Bot: robô de trading para MetaTrader 5 com orquestrador em Go, cérebro em Python e validação quantitativa*. Versão 3.1.0. 2026. Software e manual técnico. Disponível em: https://github.com/fabiodrneles/mt5_bot.

Cite sempre a **versão** (tag) usada: resultados, parâmetros e código mudam entre versões, e o `CHANGELOG.md` registra o que mudou.

## C.5 Cuidados

- Não apresente resultados de backtest como previsão de retorno.
- Ao reproduzir a pesquisa com outra corretora, relate as diferenças de dados e custos (Apêndice B §B.4).
- Ao estender o código, mantenha os testes verdes e registre a decisão (cap. 10 §10.1).
