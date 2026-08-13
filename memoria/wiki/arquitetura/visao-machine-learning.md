# Visão de Futuro: Machine Learning e IA no mt5bot

> *Documento de registro arquitetural criado para não esquecer o potencial de evolução do Motor de Mentoria.*

A arquitetura dividida do mt5bot (Maestro em Go cuidando da orquestração leve, e Cérebro em Python cuidando da execução) foi desenhada visando, no longo prazo, permitir a integração de modelos de **Machine Learning** (como TensorFlow, PyTorch, XGBoost, etc.) de forma segura e performática, mesmo com restrições severas de hardware local (i3, 4GB RAM).

## 1. Como a IA se encaixa (Estrategista de Risco, não Gerador de Sinal)

A regra de ouro é **nunca substituir** os setups matemáticos objetivos (Setup 9.1, 9.2, Ponto Contínuo, etc.) por "caixas pretas" preditivas que geram compras/vendas caóticas. Os setups objetivos já possuem expectativa matemática positiva comprovada pelos livros.

O papel da IA no bot é atuar dentro do **Motor de Mentoria / Otimizador**, prevendo o **Perigo** e ajustando o Risco.

### Casos de Uso Planejados:
* **Classificação de Regime de Mercado**: A IA lê os últimos N candles para prever (ex: 85% de chance) se o dia atual será de lateralização (*chop*). Se for, ela comanda o Maestro a desligar configurações de "falso rompimento" ou reduzir lotes drasticamente.
* **Filtro de Stop Hunt (Caça-Stop)**: Analisar a volatilidade e volume para detectar padrões institucionais de violação de mínimas antes de iniciar a tendência. Recomendar recuos profundos.
* **Ajuste Dinâmico de Lote**: Diminuir lote em eventos de altíssima volatilidade prevista, mantendo o controle de ruína no longo prazo.

## 2. Lidando com Restrições de Hardware (i3, 4GB RAM)

O treinamento de redes neurais profundas com TensorFlow é inviável no hardware de produção atual. A estratégia para não engasgar o bot é:

1. **Treinamento Offline (Cloud)**: Os dados gerados pelo `paper_tracker` (banco de dados de rejeições, vitórias e contextos) serão exportados. O treinamento do modelo preditivo será feito externamente em plataformas na nuvem gratuitas (ex: Google Colab).
2. **Inferência Leve (Local)**: O bot fará apenas o *deploy* do modelo já treinado e cristalizado (formato TFLite ou ONNX). Fazer inferências (previsões) com um modelo TFLite consome praticamente zero de CPU e pouquíssima RAM.
3. **Alternativas mais Leves**: Antes de ir para Redes Neurais (TensorFlow), priorizar modelos baseados em Árvores de Decisão (como **XGBoost** ou **LightGBM** usando `scikit-learn`), pois costumam performar extraordinariamente bem com dados tabulares/séries temporais financeiras, sendo absurdamente mais leves para rodar localmente.

## 3. O Próximo Passo

O **Motor de Mentoria** trabalha coletando a base de dados (os "estudos" gerados pelo `simulator.py` e os logs de rejeição do `paper_tracker`).

**ATUALIZAÇÃO IMPORTANTE (Fase 2 Concluída - ML Context V2):** 
O bot agora extrai nativamente em `indicators.py` e `strategy.py` um contexto profundo para Machine Learning que inclui:
- **ADX**: Para medir a força da tendência.
- **Z-Score (21 períodos)**: Para medir desvios institucionais (estatística pura).
- **Distâncias Relativas**: Percentual de distanciamento do preço frente à EMA9, SMA21, SMA200 e VWAP.
- **Microestrutura**: Tamanho absoluto do body, upper wick e lower wick em percentual do ATR.

Toda essa riqueza de dados já está sendo injetada e salva pelo `tracker.py` e `paper_tracker.py`. Quando o banco de dados possuir milhares de exemplos de mercado reais e simulados, teremos o *dataset perfeito* para dar o pontapé inicial no treinamento do modelo externo em XGBoost/LightGBM.
