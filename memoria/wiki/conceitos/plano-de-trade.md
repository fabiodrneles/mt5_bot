# Plano de Trade — Sistematização

Fonte: `raw/fundamentos.txt` (p.301, ~L31882) · Status: fundamento estratégico

## A visão do Palex
> **"Mais de 90% dos traders perdem dinheiro porque não seguem um plano de trade."** A maioria não tem regras definidas antes de entrar no mercado.

## Componentes do plano de trade
1. **Regras de entrada** claras (setup definido + time frame).
2. **Regras de saída** (stop, alvo, tempo máximo na operação).
3. **Gestão de risco** (tamanho da posição, % do capital por trade).
4. **Frequência** (quantas operações por dia/semana).
5. **Avaliação** (métricas de performance — acerto, Pay Off, expectância).

## Por que sistematizar
- Remove a **emoção** e o **viés de confirmação** das decisões.
- Permite **replicar** o processo (essencial para automatização com o bot).
- Permite **medir** a performance e **melhorar** o sistema (feedback loop).

## Aplicação no bot
- O bot **É** a materialização do plano de trade: setups → sinais → execução com regras fixas.
- `main.py` + `strategy.py` + `config.py` = o plano em código.
- Fase 3 (maestro Go) = supervisão do plano (heartbeat, falhas, filas).

## Observação de trading
- Palex: "Abracem a simplicidade" — planos complexos falham; regras simples e seguidas consistentemente vencem.
- Operar **todos os sinais do sistema** (sem escolher a dedo) — seleção manual destrói a estatística.
