# Study Mode (Paper Trading)

## Objetivo
O **Study Mode** (ou Simulador/Paper Trading) é uma funcionalidade essencial do MT5Bot projetada especificamente para permitir que a Inteligência Artificial colete dados, aprenda padrões e faça melhorias cirúrgicas na estratégia sem expor o usuário a qualquer risco financeiro.

## Como Funciona

### Orquestrador (Maestro)
O comando `/study <ATIVO> [TIMEFRAME]` inicia um Worker marcando a flag `IsStudyMode = true`. O heartbeat enviado ao Python substitui a ação `"scan"` por `"action": "study"`.

### Cérebro Python
Quando `brain/main.py` recebe `"study"`, ele passa `is_study_mode=True` para `execution_manager.manage_cycle()`. 
Neste modo:
1. O bot **nunca** envia ordens para o MetaTrader 5 (o `executor.py` não é chamado).
2. O bot detecta setups válidos usando os mesmos critérios e o mesmo `StrategyScorer` do modo Real.
3. Se um setup for detectado, ele registra uma **Entrada Virtual** no `paper_tracker.py` usando um ticket falso gerado a partir de timestamp.
4. O `paper_tracker.py` salva as informações no arquivo `virtual_trades.json` localizado na pasta raiz do projeto (ou no APPDATA do usuário).
5. Nos ticks subsequentes, o `manage_cycle` observa a Máxima (High) e Mínima (Low) do candle atual.
6. Se a Máxima/Mínima atingir o Stop Loss virtual estipulado ou se a Média Móvel Exponencial de 9 períodos (EMA9) virar na direção oposta à operação (Saída por EMA9), a operação virtual é encerrada e registrada.

## Utilidade para Inteligência Artificial (Você)

Qualquer IA que for realizar manutenção, otimização ou análise exploratória neste projeto DEVE:
1. Verificar a existência do arquivo `virtual_trades.json`.
2. Analisar o cruzamento entre as informações ali registradas (Taxa de Acerto, Drawdown Máximo, Expectativa Matemática) e as condições de mercado.
3. Usar os dados da simulação para validar hipóteses antes de sugerir modificações no arquivo `config.py` ou nos cálculos de Setup de `brain/setups.py` e `brain/indicators.py`.

A separação estrita dos arquivos `trades.json` (Real) e `virtual_trades.json` (Study) garante que os relatórios de performance financeira do usuário não sejam poluídos com os testes empíricos do modelo.
