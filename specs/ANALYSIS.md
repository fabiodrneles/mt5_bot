# Análise e verificação do MT5Bot

> Data: 2026-10-24 · Base: commit `0198117` (branch `main`, v2.12.0)
> Método: leitura do código + build (Python e Go), testes, lint e execução real dos comandos documentados contra uma conta MT5 real (Hantec, hedging), além da reprodução do CI num ambiente limpo.

## 1. Resumo executivo

O núcleo de trading funciona e é testado localmente: 184 testes Python e todos os testes Go passam, e as rotas quant foram validadas fora da amostra. **Ainda não é um produto instalável.** Hoje, para usar, é preciso clonar o repositório, ter Python e Go e editar `config.py`. O CI do GitHub está vermelho desde agosto, e o pacote Python gerado pelo `pyproject.toml` quebra ao ser importado.

- O usuário comum não consegue instalar: não há instalador, e o pacote gerado está incompleto.
- Nenhuma mudança é protegida por CI: o pipeline falha antes de rodar um único teste.
- O macOS e o Linux não têm caminho oficial, porque a biblioteca `MetaTrader5` do Python só existe para Windows.
- Os setups clássicos ainda estão ligados para operar ao vivo, e o histórico real deles é negativo.

A base é boa. A recomendação é **corrigir, consolidar e empacotar**, não reescrever.

## 2. O que foi verificado

| Verificação | Resultado |
|---|---|
| `python -m pytest -q` (máquina do dono, Python 3.13) | ✅ 184 passed |
| `go vet ./... && go test ./...` (maestro) | ✅ ok |
| CI no GitHub (`gh run list`) | ❌ vermelho em todos os pushes desde 2026-08-19 (ex.: run `40057784737`) |
| CI reproduzido num venv limpo (`pip install pytest numpy pandas`) | ❌ 5 erros de coleta: `ModuleNotFoundError: pytz` |
| Coleta do pytest no CI | ❌ `test_rvol_wins.py` (raiz) chama `exit()` na importação → `INTERNALERROR`, "no tests ran" |
| `pip wheel .` (pacote do `pyproject.toml`) | ❌ sem `mt5bot.mentorship` (importado no topo de `execution_manager.py:10`); com módulos velhos soltos (`config.py`, `main.py`, `tui.py`…) vindos de `build/lib`; sem o `maestro.exe` que o comando `mt5bot` precisa |
| `run.bat` (`go run main.go worker.go`) | ❌ `undefined: ColorAmber` (faltam `style.go`, `ui.go`, `badges.go`…) |
| `mt5bot.bat` → `maestro.exe --version` | ✅ `MT5Bot v2.12.0` |
| `bot.bat diagnose / config / positions / market / quant --once / dashboard` | ✅ funcionam contra o MT5 real |
| `bot.bat hardware` | ⚠️ exige `psutil`, que não está nas dependências (documentado) |
| `bot.bat ask "setup russo"` | ✅ |
| `ruff check --select F821,F811,F401,E9` | ⚠️ 53 achados: 45 imports não usados e redefinições (`indicators.py:211` redefine `calculate_bollinger_bands`) |
| Histórico real (`%APPDATA%\mt5bot\trades.json`) | ⚠️ 7 trades fechados de setups clássicos/manuais: **−$33,18** |
| macOS / Linux | ❌ não verificado em máquina; a lib `MetaTrader5` só publica wheels para Windows |

## 3. Observações por severidade

### Críticas

| # | Observação | Evidência | Spec |
|---|---|---|---|
| C1 | O CI está vermelho há 2 meses; nenhuma mudança é protegida | run `40057784737`: `test_rvol_wins.py:15 exit()`; venv limpo: `No module named 'pytz'` | 001 |
| C2 | O pacote Python está quebrado: falta `mt5bot.mentorship`, sobram módulos velhos, e o `mt5bot` exige um `maestro.exe` que não é empacotado | `pyproject.toml` (`packages = [...]` manual); conteúdo do wheel | 002 |
| C3 | Não existe instalador: o usuário precisa de git, Python, pip e Go | README §Instalação | 002 |
| C4 | Não há caminho para macOS/Linux | a lib `MetaTrader5` é só para Windows | 002, D1 |

### Altas

| # | Observação | Evidência | Spec |
|---|---|---|---|
| A1 | `run.bat` não compila | `go run main.go worker.go` → `undefined: ColorAmber` | 004 |
| A2 | ~21 MB de binários versionados (`maestro.exe`, `.exe.bak`, `bin/maestro.exe`, `maestro_supervisor_check.exe`), não reproduzíveis | `git ls-files` | 004 |
| A3 | O workflow de ML faz commit e push direto na `main` sempre que a mensagem do commit **contém "ML"**: "HTML", "XML" e "YAML" também disparam | `ml_training.yml:21` (`contains(..., 'ML')`) e `git push` | 005 |
| A4 | Os setups clássicos operam ao vivo por padrão, sem validação fora da amostra; o histórico real é de −$33,18 | `config.ASSET_SETUPS["default"]`; `trades.json` | 005, D5 |
| A5 | A configuração só muda editando código (`config.py`); com o programa instalado, o usuário não consegue (e não deve) editar | `mt5bot/core/config.py` | 003 |
| A6 | Logs e estado são gravados na pasta do programa (`logs/`, `state.json`); instalado em *Program Files*, não há permissão de escrita | `tools/quant_runner.py` (`_ROOT/logs`), `logger.py` | 003 |
| A7 | O CI roda só em Ubuntu, mas o produto é Windows | `ci.yml` (`runs-on: ubuntu-latest`) | 001 |

### Médias

| # | Observação | Spec |
|---|---|---|
| M1 | Não há gate de lint nem de formatação; 53 achados do ruff | 001 |
| M2 | Lixo versionado: `logs/*.log`, `blame.txt`, `build_check.txt`, `dist/*1.0.0*`, `temp/`, `testes/`, CSVs de dataset, 6 Markdown soltos na raiz | 004 |
| M3 | Código legado duplicado (`legacy_main.py`, `legacy_indicators.py`, `tools/sim_fin*.py`, `refactor_imports.py`) | 004 |
| M4 | Falta o guia prático: `CONTRIBUTING.md`, templates de issue/PR, `CODEOWNERS`, `[Unreleased]` no CHANGELOG | 001 |
| M5 | O primeiro uso não é guiado: o usuário não sabe se a conta é demo ou real antes de ligar | 006 |
| M6 | O Maestro chama `python` do PATH: num instalador, precisa apontar para o Python embutido | 002 |

### Baixas / higiene

- `tools/backtest.py`: o ruff aponta F821 em `current_trade_lot`. É provável falso positivo (a variável é atribuída na mesma função), mas a legibilidade é ruim.
- O README em inglês mostra telas do console em português (o console não tem i18n).
- `bot.bat` é exclusivo do Windows.

## 4. Pontos positivos (manter)

- **Validação quant honesta:** pesquisa com custos reais, seleção dentro e fora da amostra, teste de sorte e ferramentas versionadas em `tools/quant_research/`.
- **Proteção de capital testada:** trava de risco por rota, reserva de margem, pânico e shutdown restritos ao MAGIC do bot, e posições manuais intocadas.
- **Arquitetura stateless:** o estado é relido do MT5, e o SL/TP fica na corretora.
- **Três interfaces sobre uma telemetria só** (v2.12.0).
- **Testes:** 184 em Python, com MT5 simulado, e a suíte Go com testes de layout.
- **Memória RAG** do projeto (`memoria/`) e o `AGENTS.md`.

## 5. Avaliação do README

- **Instalação** (`pip install -e ".[dev]"`): funciona em modo editável na máquina do dono. O pacote não editável quebra (C2). O README pressupõe git e Python, o que não serve para um usuário final (C3).
- **`run.bat`**: prometido como alternativa, não compila (A1).
- **Comandos `bot.bat` e Modo Quant**: funcionam como descrito.
- **"Testes passando" no selo**: é verdade localmente, falso no CI (C1).
- **Plataformas**: promete Windows 10/11, o que está correto. Não promete macOS/Linux.

## 6. Melhorias recomendadas (priorizadas)

**Fase 1 — Funcionar de verdade (P0) → `v2.13.0`**
1. CI verde e confiável: dependências do projeto, coleta limpa, matriz Windows + Ubuntu e gate de lint (C1, A7, M1).
2. Empacotamento Python correto: descoberta automática de pacotes e um wheel que importa (C2).
3. `run.bat` funcional; binários e lixo fora do git (A1, A2, M2, M3).
4. Dados do usuário (logs, estado e configuração) em `%APPDATA%\mt5bot`, com `config.toml` do usuário sobrepondo o `config.py` (A5, A6).

**Fase 2 — Confiável (P1) → `v2.14.0`**
1. Instalador Windows (`MT5Bot-Setup-x.y.z.exe`): Python embutido, Maestro compilado, atalhos e desinstalador (C3, M6).
2. Workflow de release por tag: CI completo, build, smoke do instalado e checksums (C3).
3. Workflow de ML seguro: manual, sem push na `main` (A3).
4. Setups clássicos fora do modo ao vivo por padrão, conforme D5 (A4).

**Fase 3 — Profissional (P2) → `v3.0.0`**
1. Pacotes para macOS/Linux, conforme D1 (C4).
2. Assistente de primeiro uso: escolher demo/real, testar a conexão, explicar o risco (M5).
3. Guia de contribuição, templates e `CODEOWNERS` (M4).

## 7. Decisões

> Aprovadas pelo dono em 2026-10-24: todas as recomendações aceitas. O projeto **não será vendido**; o objetivo é portfólio de engenharia.

| # | Pergunta | Opções | Decisão |
|---|---|---|---|
| D1 | Como atender macOS e Linux, se a lib `MetaTrader5` só existe para Windows? | a) só Windows; b) pacote Mac/Linux que roda o bot inteiro dentro do **Wine** (MT5 + Python para Windows no mesmo prefixo), marcado como *experimental*; c) Mac/Linux só com o dashboard e a pesquisa, sem operar | **b**: é o único caminho que opera de verdade; o próprio MT5 já roda assim nesses sistemas. Fica rotulado como experimental, com o Windows como plataforma principal |
| D2 | Formato do instalador Windows | a) Inno Setup (`Setup.exe`) com Python embutido; b) PyInstaller em executável único; c) MSIX | **a**: atalhos, desinstalador, Python embutido sem conflito com o do usuário, e build gratuito no GitHub Actions |
| D3 | Assinatura de código (sem ela, o Windows mostra o aviso do SmartScreen) | a) sem assinatura por enquanto, documentando o aviso; b) comprar um certificado (~US$ 200–400/ano) | **a** agora, **b** se o produto for vendido |
| D4 | Fluxo de entrega: PR por ticket com merge feito por você, ou rodada de merges delegada a mim? | a) você revisa e faz merge de cada PR; b) você delega rodadas de merge (sempre com CI verde, na ordem do épico) | **b**: pelo seu pedido de "deixar tudo atualizado", com CI obrigatório em cada merge |
| D5 | Setups clássicos (9.x, PC, russian_bb…) no modo ao vivo | a) manter ligados; b) só em `/study` por padrão, com opção explícita para ligar ao vivo; c) remover | **b**: protege o dinheiro (o histórico real é −$33) sem jogar fora o código |
| D6 | Numeração das versões | a) continuar SemVer em 2.x (`v2.13.0` → `v2.14.0` → `v3.0.0`); b) recomeçar em `v0.x` | **a**: o projeto já publica 2.x |
| D7 | Licença, se o objetivo é vender | a) manter MIT (qualquer um pode revender); b) licença comercial ou proprietária; c) *open core* | **a** até você decidir o modelo de negócio. Essa decisão é sua e, se for vender, vale consultar um advogado |
| D8 | Binários no git (`maestro.exe` etc.) | a) remover do git e publicar só nas Releases; b) manter | **a**: reproduzível e repositório mais leve; quem clona compila com `go build` |
