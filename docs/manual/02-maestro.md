# 2. Maestro: o orquestrador em Go

O Maestro é o programa interativo (`mt5bot.bat` → `maestro.exe`, compilado a partir do pacote Go em `maestro/main.go` e vizinhos). Ele **não decide trades**: inicia, supervisiona e exibe os trabalhadores Python. Essa separação mantém o orquestrador fora do caminho crítico da ordem, de modo que uma falha de interface não pode enviar ordem errada.

## 2.1 Arquitetura da interface: The Elm Architecture

A TUI usa a biblioteca **Bubble Tea**, que implementa *The Elm Architecture* (TEA) [Czaplicki 2012]. O programa é uma tripla pura:

- **Model:** o estado da tela (`maestro/main.go:model`): trabalhadores, logs, dimensões, modo;
- **Update(msg) → (Model, Cmd):** a única função que muda o estado, reagindo a mensagens (teclas, redimensionamento, ticks de 1 s, linhas de log);
- **View(Model) → string:** renderização pura do estado.

**Por que TEA?** O fluxo unidirecional torna a interface determinística e testável: os testes constroem um `model`, chamam `View()` e inspecionam o texto (`maestro/main_ui_test.go`, `ui_test.go`), inclusive verificando que nenhuma linha ultrapassa a largura do terminal em 5 tamanhos diferentes (`TestLayoutNaoEstouraTerminal`). Uma TUI imperativa, que redesenha em vários pontos do código, não teria essa propriedade.

## 2.2 Ciclo de vida de um trabalhador

`maestro/worker.go` modela cada robô como um `PythonWorker`:

```
/add HK50 H4 ─▶ Start() ─▶ runProcess() ─▶ [processo Python vivo]
                   ▲              │ heartbeatLoop: a cada 1 s envia ping + scan
                   │              │ watchdog: 15 s sem pong ⇒ mata o processo
                   │              ▼
                   └── espera 5 s ◀─ processo caiu (erro) ──┐
                                                            │ recordFailure()
                        3 falhas em < 2 min ⇒ DESLIGADO ◀───┘ (crash loop)
                        /fix ⇒ Heal() ⇒ volta a Start()
```

| Mecanismo | Parâmetro | Código |
|---|---|---|
| Heartbeat | ping a cada 1 s | `heartbeatLoop` |
| Watchdog | mata o processo após 15 s sem `pong` | `heartbeatLoop` |
| Reinício | 5 s após a queda | `Start` |
| Proteção contra *crash loop* | 3 falhas numa janela de 2 min desligam o robô | `recordFailure` |
| Reparo manual | `/fix` reinicia os desligados | `Heal` |

**Fundamentação.** O desenho segue a **árvore de supervisão** do Erlang/OTP [Armstrong 2003]: o trabalhador não tenta se recuperar de estados inesperados; ele morre, e o supervisor o reinicia limpo. A proteção contra *crash loop* aplica a ideia do **disjuntor** (*circuit breaker*) de [Nygard 2018]: se reiniciar não resolve (dado corrompido, ativo inexistente), insistir só gasta CPU e enche o log. Depois de 3 falhas o circuito "abre" e espera intervenção humana. O watchdog cobre a falha mais difícil de detectar, o processo travado que não morre.

**Por que reiniciar é seguro?** Por causa da arquitetura *stateless* (cap. 1 §1.4): o processo novo relê o estado do MT5 e continua de onde o anterior parou.

## 2.3 Interpretador Python

`maestro/python.go:pythonExeFor` escolhe o Python dos trabalhadores, nesta ordem:
1. a variável `MT5BOT_PYTHON`;
2. `<app>\python\python.exe`, o Python embutido do instalador, vizinho da pasta do `maestro.exe`;
3. o `python` do PATH, para quem clonou o repositório.

A busca relativa ao executável, e não ao diretório de trabalho, permite que o mesmo binário funcione no repositório e na instalação (cap. 10).

## 2.4 Telemetria na interface

Cada resposta do trabalhador traz `telemetry` (cap. 9 §9.4). O `handleResponse` a decodifica num `Telemetry` tipado, guardado sob *mutex*, porque o heartbeat e a renderização rodam em goroutines diferentes. A `View` lê por `Snapshot()`, uma cópia sob lock, e desenha:
- **Cabeçalho:** selos do modo (LIVE/SIMULADOR), da conexão e da conta REAL/DEMO, com saldo, patrimônio, margem e o P/L flutuante só das posições do robô. Cada ativo é somado uma vez, mesmo com dois timeframes.
- **Cartão por robô:** estado traduzido em selo (`badges.go:statusBadge`), rota quant (★) ou "experimental", contagem até o fechamento do candle, risco × limite (✓ ou 🔒) e posição com P/L.

O mapeamento dos estados em 6 selos (SCAN, WAIT, POS, LOCK, ERRO, INIT) aplica a heurística de **visibilidade do estado do sistema** de [Nielsen 1994]: o usuário vê, sem ler logs, se cada robô está procurando, posicionado, bloqueado ou com erro, e por quê.

## 2.5 Eficiência

- O resumo de performance relê o `trades.json` só quando o arquivo muda, com cache por `mtime` + tamanho (`metrics.go:readTradesFile`). Antes, eram 1 leitura e 1 parse JSON por segundo por robô.
- Os logs ficam limitados a 1.000 linhas, para não congelar a interface.

## 2.6 Comandos e segurança

`/quit close-all`, `wait-flat` e `cancel-open` chamam `python -m mt5bot.core.shutdown_manager`, que age **só** em posições e ordens com o *magic* do robô (cap. 6 §6.8). Esc limpa a linha em vez de encerrar o programa: a ação destrutiva fica atrás de um comando explícito (`/quit` ou Ctrl+C), outra heurística de prevenção de erros [Nielsen 1994].

## 2.7 Limitações

- O ping de 1 s também é o gatilho do *scan*: o intervalo de decisão fica acoplado ao do heartbeat. Para timeframes H4/D1, ciclos de 1 s são mais frequentes que o necessário, embora baratos (cap. 9 §9.5).
- Se dois robôs rodam o mesmo ativo (Maestro e Modo Quant, por exemplo), eles podem disputar a mesma posição; isso é documentado, não impedido.

## 2.8 Referencial teórico

[Armstrong 2003] supervisão e *let it crash*; [Nygard 2018] disjuntores e estabilidade; [Czaplicki 2012] The Elm Architecture; [Nielsen 1994] heurísticas de usabilidade.
