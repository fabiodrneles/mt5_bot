# Laboratório Elite Quant: Mapa de Inovações e Otimizações

Este documento arquiva as frentes de pesquisa quantitativa para otimizar a performance do MT5Bot, desenhadas especificamente para sobreviver e tracionar contas pequenas (Escadinha de Capital inicial).

---

## 1. Otimização Cirúrgica: Saída via Trailing Stop / Volatilidade
**O Problema:** O setup Russo (HK50) possui alta margem de segurança e sobrevivência comprovada (sobreviveu 2 anos com saldo de $16 sem quebrar), porém o lucro nominal é baixo porque a estratégia fecha a operação precocemente (ao tocar a média central), desperdiçando o movimento de reversão se ele se transformar numa nova tendência forte.
**A Solução:** Testar a adição de um **Trailing Stop Inteligente (Baseado em ATR)** ou gatilho de **Breakeven**. 
**Objetivo:** Transformar os lucros de centavos em lucros de dólares capturando as "caudas gordas" (fat tails) do mercado. Se o trade andar a favor, o robô tranca o capital no 0 a 0 e arrasta o stop junto com o preço.
**Status:** 🟡 Na Fila de Pesquisa (Recomendado como próximo passo)

## 2. Pesquisa Geográfica: O "Turno da Madrugada" (Expansão Lateral)
**O Problema:** Com margem pequena, o robô só liga o motor das 22:15 às 01:00 (HK50), deixando o capital ocioso por 21 horas no dia.
**A Solução:** Usar otimização convexa e backtests em Python para caçar distorções probabilísticas de *Mean Reversion* (Reversão à Média) em pares exóticos e de baixo custo durante a madrugada europeia (01:00 às 05:00 BRT).
**Ativos Alvo:** AUDCAD, AUDNZD, EURAUD (horários mortos sem grandes injeções de volume institucional, onde algoritmos laterais costumam reinar).
**Objetivo:** Adicionar um segundo motor seguro ao robô, complementando o horário do HK50 sem expor a conta ao risco direcional das aberturas agressivas.
**Status:** ⚪ Ideia Mapeada

## 3. Inovação Elite: Machine Learning Nível 1
**O Problema:** Setup Russo no HK50 M5 acerta ~40% das vezes de forma mecânica. Muitas entradas são feitas durante falsos sinais de exaustão, resultando em estopadas que poderiam ser evitadas se o contexto fosse melhor analisado.
**A Solução:** Exportar os logs de todos os trades simulados dos últimos 2 anos e treinar um modelo de *Machine Learning* simples (ex: Random Forest ou XGBoost) para classificação binária (Win/Loss).
**Features Sugeridas:** Volume de ticks na abertura, ângulo (slope) da EMA50, correlação do IFR no timeframe superior (H1), e distância exata para a VWAP.
**Objetivo:** Atuar como um porteiro ("Filtro de Machine Learning"). O motor Russo encontra o sinal, mas o modelo de ML diz: "Essa configuração histórica tem 70% de chance de dar stop, aborte a missão."
**Status:** ⚪ Ideia Mapeada (Projeto longo prazo)
