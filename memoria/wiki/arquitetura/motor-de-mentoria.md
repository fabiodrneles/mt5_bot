# Motor de Mentoria Adaptativo (Adaptive Supervisor)

## Visão Geral
O **Motor de Mentoria** (Mentorship Engine) é um componente arquitetural planejado para o futuro (Fase 4/5) focado em **aprendizado contínuo e calibração dinâmica**. Ele atua como um supervisor acima do Cérebro Python padrão (que é estritamente baseado em regras fixas).

Sua função principal é interceptar "vetos" gerados por filtros macro e decidir, com base em dados históricos consolidados (telemetria de rejeição), se aquele filtro é adequado para o contexto específico do mercado no momento.

## O Problema Atual (Regras Rígidas)
Atualmente, os filtros (RVOL, MM50, MTF) são constantes absolutas. Por exemplo, o filtro de Volume Relativo (`RVOL_THRESHOLD = 1.15`) exige que o candle de gatilho tenha 15% a mais de volume do que a média. 
Isso pode ser excelente para a B3 no início do pregão, mas excessivamente restritivo para o Forex (ex: `EURUSD` no gráfico de `M5`), impedindo o robô de capturar movimentos lucrativos em mercados de volatilidade comprimida.

## Como o Motor de Mentoria Resolve
1. **O Gatilho:** Quando o motor de decisão original (`scoring.py`) veta uma entrada matemática válida por causa de um filtro, ele notifica o Motor de Mentoria antes de descartar definitivamente o trade.
2. **Avaliação de Contexto:** O Motor de Mentoria consulta a base de dados (`virtual_rejections.json` e histórico de performance) e constata: *"Neste par (EURUSD), neste timeframe (M5), durante esta faixa de horário (Sessão Asiática/Europeia), o limite ideal de RVOL é 1.05, não 1.15"*.
3. **Override (Destravar):** O Motor envia um comando de exceção para o executor, destravando a operação e autorizando a entrada com parâmetros calibrados (ex: stop e alvo ajustados para aquele perfil de volatilidade).

## Fonte de Dados
Para o Motor de Mentoria existir, ele precisa de uma base rica de *causa e consequência*. O **Modo Study (`/study`)** com sua telemetria de rejeição implementada na versão v1.8.6 é a fundação deste sistema. Ele grava em `%APPDATA%/mt5bot/virtual_rejections.json` todos os sinais vetados, que mais tarde servirão como *dataset* de treinamento para a IA de calibração do Motor de Mentoria.

## Fluxo de Decisão Projetado
`Sinal Matemático Detectado` ──> `Filtros Padrão (Ex: RVOL < 1.15? = VETO)` ──> `Motor de Mentoria Intercepta` ──> `Análise do Dataset de Rejeições` ──> `É falso positivo para este ativo/hora?` ──> `(SIM)` ──> **OVERRIDE E EXECUÇÃO**.
