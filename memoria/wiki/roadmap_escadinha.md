---
title: "Roadmap de Crescimento (A Escadinha do Capital)"
date: "2026-08-18"
tags: [arquitetura, risco, gestao, roadmap]
---

# A Escadinha de Capital (Roadmap Convexo)

Esta página documenta a estratégia oficial de escala de capital do MT5Bot.
A matemática quantitativa provou que ativos diferentes possuem *Drawdowns* (rebaixamentos) diferentes e custos de margem diferentes. O HK50 provou ser o degrau inicial perfeito graças a alavancagem micro em frações de centavos na corretora utilizada.

O sistema da **Garagem (Garage Lock)**, implementado no `risk_calculator.py`, lê o dicionário `MIN_BALANCE_REQUIREMENTS` no `config.py` e tranca automaticamente os ativos pesados (como EURUSD e JP225) até que a conta atinja o degrau necessário.

## Os 3 Degraus da Escada

### 1. Degrau da Tração Micro-Cents ($16.00 a $60.00)
- **Ativo:** `HK50` / `HKG50`
- **Margem do Lote Mínimo:** Frações de centavos
- **Estratégia:** Setup Russo (Russian BB) em M5.
- **Horário:** 22:15 às 01:00 BRT
- **Por que:** Devido à estrutura de lotes micro-fracionados da corretora (1 ponto = ~$0.001 USD), o índice permite surfar os lucros maciços do Setup Russo sem comprometer a conta. O Drawdown fica perfeitamente suportável para os $16 de saldo inicial.

### 2. Degrau do Forex Estável ($60.00 a $300.00)
- **Ativo:** `EURUSD`
- **Margem do Lote Mínimo:** ~$1 a $3
- **Estratégia:** Setup Russo (Russian BB) em H1 / M5.
- **Horário:** 03:00 às 09:00 BRT (Sessão de Londres)
- **Por que:** Baixa volatilidade extrema. Risco quase nulo de stop loss agressivo. Requer pelo menos $60 para suportar o stop-loss baseado na largura das Bandas de Bollinger sem estourar o "Risk Shield" de 1.5% do bot.

### 3. A Máquina de Convexidade Asiática ($300.00+)
- **Ativo:** `JP225` / `JPN225`
- **Margem do Lote Mínimo:** ~$20 a $30
- **Estratégia:** Ponto Contínuo (H1) com SMA200.
- **Horário:** 21:00 às 06:00 BRT (Sessão Asiática)
- **Por que:** O "Santo Graal" das tendências longas. Exige $300 de saldo mínimo (Garage Lock) para suportar oscilações intradiárias, enquanto captura os imensos lucros tendenciais (800+ pontos).
