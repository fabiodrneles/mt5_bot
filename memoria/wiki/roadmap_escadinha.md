---
title: "Roadmap de Crescimento (A Escadinha do Capital)"
date: "2026-08-18"
tags: [arquitetura, risco, gestao, roadmap]
---

# A Escadinha de Capital (Roadmap Convexo)

Esta página documenta a estratégia oficial de escala de capital do MT5Bot.
A matemática quantitativa provou que ativos diferentes possuem *Drawdowns* (rebaixamentos) diferentes e custos de margem diferentes. Para proteger a conta contra ruínas, o capital deve escalar em degraus, mudando de ativo conforme o saldo ganha robustez.

O sistema da **Garagem (Garage Lock)**, implementado no `risk_calculator.py`, lê o dicionário `MIN_BALANCE_REQUIREMENTS` no `config.py` e tranca automaticamente os ativos até que a conta atinja o degrau necessário.

## Os 4 Degraus da Escada

### 1. Degrau da Sobrevivência ($10.00 a $60.00)
- **Ativo:** `BCHUSD` (Bitcoin Cash)
- **Margem do Lote Mínimo:** $0.10
- **Estratégia:** Setup 9.1 (H1) ou Ponto Contínuo.
- **Horário:** 24h
- **Por que:** O Drawdown médio em simulações foi de apenas ~$3 a $5. Ideal para alavancar contas de $10 sem risco de Margin Call.

### 2. Degrau de Tração ($60.00 a $150.00)
- **Ativo:** `EURUSD`
- **Margem do Lote Mínimo:** ~$1 a $3
- **Estratégia:** Setup Russo (Russian BB) em H1 / M5.
- **Horário:** 03:00 às 09:00 BRT (Sessão de Londres)
- **Por que:** Baixa volatilidade extrema. Risco quase nulo de stop loss agressivo. Requer pelo menos $60 para suportar oscilações intradiárias seguras.

### 3. Degrau do Acelerador ($150.00 a $300.00)
- **Ativo:** `HK50` / `HKG50`
- **Margem do Lote Mínimo:** ~$15
- **Estratégia:** Setup Russo (Russian BB) em M5.
- **Horário:** 22:15 às 01:00 BRT
- **Por que:** Volatilidade altíssima na abertura da bolsa de Hong Kong. Rende muito, mas tem Drawdown documentado de ~$22 em alguns piores cenários. Exige saldo de $150 para operar com paz.

### 4. A Máquina de Convexidade ($300.00+)
- **Ativo:** `JP225` / `JPN225`
- **Margem do Lote Mínimo:** ~$20 a $30
- **Estratégia:** Ponto Contínuo (H1) com SMA200.
- **Horário:** 21:00 às 06:00 BRT (Sessão Asiática)
- **Por que:** O "Santo Graal" das tendências longas. Precisa de $285 a $300 de saldo mínimo (Garagem Lock) para absorver oscilações enquanto captura lucros massivos (+800 pontos).

---
*Este documento é base para a configuração `MIN_BALANCE_REQUIREMENTS` no núcleo do bot.*
