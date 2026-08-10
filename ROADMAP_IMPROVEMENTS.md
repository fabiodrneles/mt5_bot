# Roadmap de Melhorias - MT5 Bot

Este documento registra o planejamento e o status de implementação das melhorias contínuas do bot de negociação no MetaTrader 5, com foco primário na **Preservação de Capital e Proteção Máxima contra Perdas**.

---

## 🏛️ Filosofia Central do Bot
> *"O objetivo do bot não é focar em ganhos desmedidos, mas sim fazer o trader perder cada vez menos, garantindo que operações só sejam executadas se forem 100% seguras dentro do limite estrito de risco do capital."*

---

## 📌 Status Geral das Fases

| Fase | Descrição | Status |
| :--- | :--- | :---: |
| **Fase 1 (Opção A)** | **Gestão de Risco Avançada, Calculadora de Capital & Proteção Total** | 🟢 **CONCLUÍDO** |
| **Fase 2 (Opção C)** | **Expansão de Estratégia & Filtros de Entrada Rigorosos** | ⏳ PENDENTE |
| **Fase 3 (Opção D)** | **Infraestrutura, CI/CD & Automação de Testes** | ⏳ PENDENTE |
| **Fase 4 (Opção B)** | **Telemetria & Notificações (Telegram / Discord)** | ⏳ PENDENTE (Pausado por opção do usuário) |

---

## 🛡️ Fase 1: Gestão de Risco Avançada & Calculadora de Capital (Opção A)

- [x] **1.1 Calculadora Interna de Proteção de Capital (*Dynamic Risk & Lot Sizer*)**
  - Consulta o saldo em tempo real no MT5 (`account_info().balance`).
  - Calcula o risco máximo seguro por operação em percentual do saldo (`MAX_RISK_PER_TRADE_PERCENT`, ex: 1.0%).
  - Calcula o lote/volume ideal dinamicamente baseado na distância do Stop Loss.
  - **Filtro de Segurança Máxima**: Se a distância do Stop Loss exigir um risco superior ao limite seguro do capital (ex: > 1.5% do saldo), a operação é **bloqueada imediatamente**.

- [x] **1.2 Trava de Perda Máxima Diária Dinâmica (*Daily Max Loss*)**
  - Adicionar configuração `MAX_DAILY_LOSS_PERCENT` em `config.py` (ex: 2.0% do saldo total).
  - Calcular PnL acumulado do dia atual no `tracker.py`.
  - Bloquear abertura de novas posições quando o limite diário em R$ / % for atingido.

- [x] **1.3 Filtro de Spread Máximo (*Max Spread Filter*)**
  - Adicionar configuração `MAX_SPREAD_POINTS` em `config.py`.
  - Validar o spread do símbolo em `executor.py` antes de posicionar ordens pendentes.

- [x] **1.4 Breakeven Automático**
  - Adicionar configuração `ENABLE_BREAKEVEN` e `BREAKEVEN_ATR_RATIO` em `config.py`.
  - Atualizar o Stop Loss em `strategy.py` / `executor.py` para o preço de entrada assim que atingir a meta parcial/ATR.

- [x] **1.5 Filtro de Horário de Negociação (*Trading Session Filter*)**
  - Adicionar `TRADING_HOURS_ENABLED`, `START_TIME` ("09:15"), `END_TIME` ("16:45") e `FORCE_CLOSE_TIME` ("17:30") em `config.py`.
  - Impedir novas entradas fora do horário permitido.

---

## 📈 Fase 2: Expansão de Estratégias & Filtros Operacionais (Opção C)

- [ ] **2.1 Filtro de Tendência Multi-Timeframe (MTF)**
  - Validar inclinação da EMA 9/21 no timeframe superior (ex: H1 quando operando em M15).
- [ ] **2.2 Setup 9.3 (Larry Williams)**
  - Implementar lógica de dois candles consecutivos de correção sem virada de média.
- [ ] **2.3 Filtro de Volume Relativo (RVOL)**
  - Validar volume acima da média das últimas $N$ velas antes da entrada.

---

## ⚙️ Fase 3: Infraestrutura, CI/CD & Automação de Testes (Opção D)

- [ ] **3.1 GitHub Actions CI/CD Pipeline**
  - Workflow automatizado para rodar `pytest` a cada push/PR.
- [ ] **3.2 Expansão de Cobertura de Testes**
  - Criar novos testes unitários para `tracker.py` e `dashboard.py` visando >85% de cobertura total.

---

## 📲 Fase 4: Telemetria & Notificações (Opção B)

- [ ] **4.1 Bot do Telegram**
  - Notificações de execução de ordens, RP, SL, Daily Max Loss e erros.
