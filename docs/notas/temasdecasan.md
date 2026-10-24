# Temas de CASA — Auditoria de Supervisão (Supervisor → Antigravity)

> **Para o Antigravity:** este arquivo contém a análise de supervisão do MT5Bot.
> Ele foi escrito para VOCÊ avaliar, contestar e corrigir o que estiver errado.
> **Não é ordem de mercado.** É um pedido de revisão fundamentada: se você discordar,
> apresente contraprova com linha do código, livro ou spec. Se concordar, corrija.
>
> **Contexto da auditoria:** comparação entre (1) os livros do Palex (memória RAG),
> (2) a spec do maestro multi-setup, e (3) o código real na branch `feat/ai-memory-rag`
> (commit `3f43905`, que contém o seu "phase 5").

---

## ⚠️ AVISO CRÍTICO DE WORKFLOW (ler antes de tudo)

O commit `3f43905` (seu "phase 5") foi feito **na branch `feat/ai-memory-rag`**
(a branch do supervisor), **não** na sua branch `feat/palex-implementation`
(que segue em `81360e2`, sem o seu trabalho novo).

Isso significa que:
- O seu trabalho está fundido com o trabalho do supervisor (RAG/memória) numa branch só.
- `strategy.py`, `tui.py`, `run_bot.py` foram deletados e `main.py` reescrito **na branch errada**.
- O plano original era 3 branches separadas (monolito `main`, supervisor, você).
- O arquivo `maestro/maestro_supervisor_check.exe` (artefato de build do supervisor,
  usado só para auditar o maestro) também entrou no commit via `git add -A`.

**Sugestão de resolução:** mover o commit `3f43905` para a sua branch via
`git cherry-pick` (ou rebase) para `feat/palex-implementation`, e separar o que
pertence a cada arquitetura. **Confirme com o usuário antes de reescrever histórico.**

---

## 1. BLOQUEANTE MATEMÁTICO — `+0.01` hardcoded em TODOS os setups

**Arquivo:** `brain/setups.py` — **13 ocorrências** de `+ 0.01` / `- 0.01`:

```
linha  43: "trigger_price": c_last['low']  - 0.01,   (9.1 sell)
linha  53: "trigger_price": c_last['high'] + 0.01,   (9.1 buy)
linha  69: "trigger_price": c_last['high'] + 0.01,   (9.2)
linha  75: "trigger_price": c_last['low']  - 0.01,   (9.2)
linha  88: "trigger_price": c_last['high'] + 0.01,   (9.3)
linha  97: "trigger_price": c_last['low']  - 0.01,   (9.3)
linha 114: "trigger_price": c2['high']     + 0.01,   (PC)
linha 124: "trigger_price": c2['low']      - 0.01,   (PC)
linha 136: "trigger_price": df['high'].iloc[-1] + 0.01,  (GAP buy)
linha 143: "trigger_price": df['low'].iloc[-1]  - 0.01,  (GAP sell)
linha 156: "trigger_price": c_last['high'] + 0.01,   (FFFD buy)
linha 167: "trigger_price": c_last['high'] + 0.01,   (FFFD sell — REPARAR: deveria ser low - 0.01)
linha 175: "trigger_price": c_last['low']  - 0.01,   (FFFD sell)
```

**Por que é bloqueante:**
- O livro do Palex diz **"1 centavo"** — contexto: ações B3, onde o tick é 0,01.
- O bot opera **EURUSD (tick 0,00001)** → `+0.01` = **1000 ticks acima do preço**.
  Uma ordem de compra 1000 ticks acima do mercado seria executada **imediatamente**
  (não espera pullback), matando o setup e a relação risco/retorno.
- **HK50 (tick 1.0)** → `+0.01` é **menor que 1 tick** → a ordem entra **abaixo do tick**
  e o MT5 **arredonda para baixo = vira ordem de compra ANTES do trigger** (execução prematura).
- Para **WIN** (tick 0,5 em pontos — depende da corretora) e US500 (tick 0,01), o offset também é errado.

**A versão antiga (`strategy.py`, deletada) fazia certo:**
```python
trigger = high + tick_size * config.TICK_OFFSET
```
Havia `tick_size` via `mt5.symbol_info(symbol).trade_tick_size`.

**Correção esperada (verificação com você):** trocar `0.01` por
`tick_size * TICK_OFFSET`, com `tick_size` obtido do MT5 (via `symbol_info`).
**Não existe tratamento de `tick_size` em `brain/` hoje.**

---

## 2. BLOQUEANTE — Saída final diverge do livro

**Arquivo:** `brain/execution_manager.py` (saída final por EMA9 virar contra) e
`brain/shutdown_manager.py`.

**O livro exige DUAS condições para a saída final:**
1. EMA9 virar contra a posição **E**
2. **O candle que provocou a virada perder a mínima/máxima** do candle anterior.

**Código atual:** implementa apenas a condição 1 (EMA9 virou). A condição 2
(candle de virada perder a mínima) **não está implementada** — nem no
`execution_manager.py` novo, nem na antiga `strategy.py`.

**Impacto:** o bot pode sair de posição no mesmo candle da virada sem confirmar
que o mercado realmente quebrou — antecipa saídas, cortando lucros que o livro
prescreve deixar correr.

---

## 3. BLOQUEANTE — Resiliência do Maestro (spec vs. realidade)

**Arquivos:** `maestro/worker.go`, `maestro/main.go`. **Spec:** `docs/superpowers/specs/2026-08-11-mt5-multi-setup-maestro-design.md`.

| Item da spec | No código |
|---|---|
| Heartbeat a cada **1s** | `worker.go:162`: `time.NewTicker(10 * time.Second)` |
| Watchdog de 3s para reiniciar Python morto | **ausente** |
| Crash Loop Protection (backoff exponencial) | **ausente** |
| Testes Go (mesmo que smoke) | **ausente** |
| `metrics.py` (contadores de erros/ordens) | **ausente** |

**Bug adicional (`worker.go:120`):**
```go
// Pass stderr to OS so we can see Python logs in the console
w.cmd.Stderr = w.cmd.Stderr   // ← self-assignment, no-op
```
Os logs do Python (que vão para stderr) são **engolidos** — você nunca vê o erro
do brain. `go vet` já sinaliza isso. **Correção:** `w.cmd.Stderr = os.Stderr`.

**Nota:** você tem um loop de heartbeat que envia o comando de scan com `symbol`,
`action:"scan"`, `timeframe`. `brain/main.py` já responde `pong` no heartbeat —
isso está correto. Mas o intervalo de 10s + ausência de watchdog + ausência de
Crash Loop = o maestro NÃO sobrevive a um crash do Python sozinho.

---

## 4. BLOQUEANTE — `magic: 1000` hardcoded no shutdown

**Arquivo:** `brain/shutdown_manager.py:49` — `"magic": 1000`.
**Arquivo:** `config.py:74` — `MAGIC = 20260731`.

O `magic` é o identificador do bot. Com `1000` hardcoded, o shutdown manager pode
**fechar/cancelar ordens de outro bot** que use magic 1000 (padrão de muitos bots)
ou **não fechar as suas próprias** (que usam magic 20260731).

**Correção:** importar `MAGIC` de `config.py` (ou passar por parâmetro).
`execution_manager.py` também — verificar se usa o magic certo ao montar ordens.

---

## 5. Divergências menores (registrar para decisão)

- **9.2** (`brain/setups.py:69-75`): usa `close[-1] < low[-2]` para sell.
  O livro usa **`low[-1] < low[-2]`** (fechamento NÃO é a condição — é a mínima).
- **9.3**: difere da spec do maestro em um detalhe do 2º fechamento — conferir.
- **Scoring**: score fixo (10/15/20/25/30/35). A spec §5.5 pede **RRR ≥ 1**
  como filtro/ordenação — não implementado (`MIN_RISK_REWARD` não existe em `config.py`).
- **Filtros da spec Fase 2 ausentes em `config.py`:** `CONFIG_SETUPS`,
  `MIN_RISK_REWARD`, `TRAILING`, filtros MM200/MM50/IFR9/VWAP.
  (Nota: o SMA200 filter foi adicionado inline em `setups.py`; GAP está isento do filtro.)

---

## 6. O que está CORRETO (confirmado na auditoria — não mexer)

- Detecção de virada do 9.1 (slope prev<0 → cur>0, buy) **idêntica ao livro**.
- Stop do 9.1 na mínima do candle de virada. ✅
- `_format_price` alinha o preço ao tick (`executor.py:19`). ✅
- Risk Shield (1%/1.5% do saldo) e Daily Max Loss (2%) funcionais. ✅
- `brain/main.py` hidrata 200 velas direto do MT5 e responde `pong` no heartbeat. ✅
- `execution_manager.py` faz saída parcial 50%, breakeven 1×ATR, gestão stateless. ✅
- `test_palex_motor.py` passou (2 testes) com a nova assinatura `tuple[list, str]`. ✅

---

## 7. Testes QUEBRADOS pelo phase 5 (ações necessárias)

`python -m pytest -q` → **1 erro na coleta**:
```
test_cli_shutdown.py:5: ImportError: cannot import name 'parse_shutdown_action' from 'main'
```
**Causa:** `main.py` foi reescrito (era o loop monólito, agora é um launcher do Go
com 1 função). Os testes `test_cli_shutdown.py`, `test_main_cli.py` e
`test_shutdown.py` importam `parse_shutdown_action`, `wait_until_flat`, `run_bot`,
`_shutdown_action` — **não existem mais**.

**Decisão a tomar:** ou (a) os testes são atualizados para a nova arquitetura
(shutdown via `brain/shutdown_manager.py`), ou (b) as funções de shutdown do
monólito são preservadas. **Testes verdes NÃO são opcionais — o projeto tem
convenção de teste obrigatório.**

---

## 8. Arquivos alterados no commit 3f43905 (para sua revisão)

| Arquivo | Status | Observação |
|---|---|---|
| `strategy.py` | **deletado** | continha a matemática correta de tick_size |
| `tui.py` | **deletado** | |
| `run_bot.py` | **deletado** | |
| `main.py` | reescrito (29 linhas) | agora só roteia para Go |
| `brain/main.py` | reescrito | loop stdin/stdout + hydration |
| `brain/setups.py` | +230 linhas | GAP, motor verboso, tuple return |
| `brain/execution_manager.py` | **novo** | gestão stateless de posição |
| `brain/shutdown_manager.py` | **novo** | `magic: 1000` hardcoded ⚠️ |
| `maestro/main.go` | +164 linhas | CLI `/add /stop /list /report /dashboard /quit` |
| `maestro/worker.go` | +41 linhas | heartbeat 10s ⚠️, `Stderr` self-assign ⚠️ |
| `maestro/maestro.exe` | commitado | binário — idealmente não versionar |
| `maestro/maestro_supervisor_check.exe` | commitado | artefato do supervisor — remover |
| `aprofundamento.md` + 2 PDFs | commitados | fontes da memória RAG |
| `test_palex_motor.py` | modificado | nova assinatura de `evaluate_all` |

---

## 9. Prioridade sugerida de correção

1. **`+0.01` → tick_size** (bloqueante #1) — matemática do trigger em todos os setups.
2. **`magic: 1000` → `config.MAGIC`** (bloqueante #4) — risco de fechar ordem de outro bot.
3. **`worker.go:120` → `os.Stderr`** (bloqueante #3) — ver logs do Python.
4. **Saída final do livro** (bloqueante #2) — candle de virada perder mínima/máxima.
5. **Heartbeat 1s + watchdog + Crash Loop + testes Go** (bloqueante #3).
6. **Consertar/adaptar testes de shutdown** (seção 7).
7. **Separar as branches** (seção "AVISO CRÍTICO").

---

*Gerado pelo Supervisor em 2026-08-11. Convite ao Antigravity: revise cada item,
conteste com fonte (livro/spec/linha) e corrija o que confirmar. O objetivo é o
bot entrar em mercado real com a matemática fiel aos livros do Palex.*
