# 008 — Execução resiliente

- **Prioridade:** P0
- **Status:** Draft
- **Código afetado:** `tools/quant_runner.py`, `mt5bot/execution/executor.py`, `mt5bot/execution/quant_manager.py`, `interfaces/brain_worker.py`, `maestro/worker.go`
- **Resolve:** G3, G4, G5 · R4

## Contexto

Um robô que roda dias seguidos vai enfrentar terminal reiniciado, internet caindo, requote, mercado fechado e corretora recusando o SL. O Maestro já reinicia o processo Python que cai (*watchdog*), mas o Python não percebe quando **o MT5** cai e continua de pé, chamando uma conexão morta.

## Estado atual (verificado)

- `quant_runner.run()` chama `mt5.initialize()` uma única vez (linha 217). Dentro do laço, uma falha vira `🔴 SEM DADOS` ou `🔴 ERRO` para sempre.
- `executor._send_order` registra o *retcode* e devolve o resultado; não há nova tentativa para erros transitórios (`REQUOTE`, `PRICE_CHANGED`, `PRICE_OFF`, `CONNECTION`, `TIMEOUT`).
- Depois de `TRADE_RETCODE_DONE`, ninguém relê a posição para confirmar SL e TP.
- O `_scan_quant` não confere o *spread* (os caminhos clássicos conferem `SYMBOL_MAX_SPREAD_POINTS`).

## Requisitos funcionais

- **FR-1** Cada ciclo MUST verificar a saúde da conexão (`terminal_info().connected` e `account_info()` não nulos). Se cair, o robô MUST tentar `shutdown()` + `initialize()` com espera exponencial (5 s, 10 s, 20 s… até 5 min) e mostrar `🟠 RECONECTANDO (tentativa N)`.
- **FR-2** Enquanto desconectado, nenhuma ordem MUST ser enviada. Ao reconectar, o estado é relido do MT5 (stateless) antes de qualquer decisão.
- **FR-3** Erros transitórios de `order_send` MUST ter até 3 novas tentativas com preço atualizado, respeitando o atraso máximo de entrada (`MAX_ENTRY_DELAY_FRACTION`). Erros definitivos (`NO_MONEY`, `INVALID_STOPS`, `MARKET_CLOSED`, `TRADE_DISABLED`) MUST NOT ser repetidos.
- **FR-4** Após abrir uma posição, o robô MUST relê-la por *ticket* e conferir se `sl` é diferente de zero e está a até 1 *tick* do pedido. Se não estiver, MUST tentar `TRADE_ACTION_SLTP` uma vez e, se falhar, **fechar a posição a mercado** e registrar `CRITICAL` (constituição, princípio 1).
- **FR-5** O Modo Quant MUST recusar entrada com *spread* acima de `SYMBOL_MAX_SPREAD_POINTS` (ou de um limite por rota no `config.toml`).
- **FR-6** O *slippage* de cada execução (preço pedido × preço executado) MUST ser registrado no trade, para alimentar a spec 011.
- **FR-7** Envios de ordem MUST ser idempotentes por candle: um reenvio depois de *timeout* primeiro confere se já existe posição com o mesmo `comment` e MAGIC.

## Requisitos não funcionais

- **NFR-1** A reconexão não pode bloquear o painel: ele continua desenhando e mostra a contagem.
- **NFR-2** Nenhuma nova tentativa ultrapassa 10% da duração do candle depois da abertura.

## Critérios de aceite

- **AC-1** Dado o mock do MT5 com `terminal_info()` devolvendo `None` em 2 ciclos e depois conectado, então `initialize()` é chamado de novo, o estado passa por `RECONECTANDO` e volta a `SCANNING` sem reiniciar o processo.
- **AC-2** Dado `order_send` devolvendo `REQUOTE` e depois `DONE`, então a posição abre na segunda tentativa.
- **AC-3** Dado `order_send` devolvendo `NO_MONEY`, então há exatamente uma tentativa.
- **AC-4** Dado `DONE` mas a posição relida com `sl = 0` e o `SLTP` falhando, então a posição é fechada e há um log `CRITICAL`.
- **AC-5** Dado o *spread* do HK50 em 800 pontos e limite 500, então o sinal é recusado com estado `🔴 SPREAD ALTO`.
- **AC-6** Dado um *timeout* no envio e a posição já existente no MT5, então não há segunda ordem.

## Fora de escopo

- Ordens pendentes e execução em várias contas.

## Decisões

- —
