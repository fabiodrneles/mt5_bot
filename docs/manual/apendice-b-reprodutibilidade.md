# Apêndice B. Reprodutibilidade

Um resultado computacional só é científico se outra pessoa conseguir reproduzi-lo [Peng 2011]. Este apêndice lista, para cada afirmação central do manual, como refazê-la. Os comandos assumem a raiz do repositório no Windows; `bot.bat` usa o Python embutido quando ele existe.

## B.1 Ambiente

| Item | Versão de referência | Onde está fixado |
|---|---|---|
| Python | 3.12 no instalador; CI testa 3.10 e 3.13 | `packaging/windows/build.ps1`, `.github/workflows/ci.yml` |
| Dependências | `numpy`, `pandas`, `MetaTrader5`, `xgboost-cpu`, `psutil` | `pyproject.toml` |
| Go (Maestro) | a do `go.mod` | `maestro/go.mod` |
| Software | 3.2.0 | `pyproject.toml`, tag `v3.2.0` |

Para estudar sem instalar o MT5, os testes usam um MT5 falso (`tests/conftest.py`), e o Python pode rodar no Linux.

## B.2 Qualidade do software (cap. 10)

```powershell
bot.bat test                      # suíte pytest
bot.bat ci                        # os mesmos passos do CI: lint, testes, Maestro
cd maestro; go test -race ./...   # testes do orquestrador
```

Resultado esperado: tudo verde, cobertura acima do piso configurado no `pyproject.toml`. O CI público de cada PR fica no GitHub Actions do repositório.

## B.3 Instalador e integridade dos binários (cap. 10)

```powershell
powershell -File packaging/windows/build.ps1      # gera dist/MT5Bot-Setup-<versão>.exe e o pacote Wine
powershell -File packaging/windows/smoke.ps1 -Setup dist\MT5Bot-Setup-3.2.0.exe
```

Para conferir que um instalador baixado corresponde ao código publicado, compare o hash com o `SHA256SUMS` da *release*: `certutil -hashfile MT5Bot-Setup-3.2.0.exe SHA256` (Windows) ou `sha256sum -c SHA256SUMS` (Linux).

## B.4 Pesquisa das rotas quant (cap. 8)

Exige um terminal MT5 aberto e logado (conta demo serve). Os scripts só **leem** histórico; não enviam ordens.

```powershell
cd tools/quant_research
python fetch.py JP225,US500,FR40,AU200,HK50,USOIL+,UKOIL+,ETHUSD,EU50,UK100,CN50,SOLUSD,XRPUSD,LTCUSD,BTCUSD
python meta.py                                   # custos e valor do ponto de cada símbolo
python research.py <ativos> M15,H1,H4,D1 r_all.json
python analyze.py r_all.json                     # robustez IS × OOS por família
python deep.py                                   # ano a ano e spread × 1,5
python portfolio.py                              # mesmo PULLB em todos os ativos
python robustness.py                             # estatística t, entradas aleatórias, RSI2 entre ativos
```

**Limites da reprodução.** Os dados vêm da corretora e **não** são versionados (pasta `data/` ignorada pelo git). Outra corretora, ou a mesma em outra data, entrega históricos e *spreads* um pouco diferentes; os números exatos do cap. 8 podem variar, mas as conclusões qualitativas (qual família é robusta, qual generaliza) é que devem ser conferidas. Os nomes de símbolos (`USOIL+`, por exemplo) também mudam entre corretoras.

## B.5 Equivalência entre pesquisa e produção (cap. 8 §8.8)

A verificação foi feita rodando `quant_setups.evaluate` vela a vela, com janela de 400 candles, sobre os mesmos dados usados por `research.py`, e comparando os sinais. Ela não é um script versionado; para refazê-la, percorra o histórico com uma janela deslizante, chame `mt5bot.engine.quant_setups.evaluate(setup, janela, params)` e compare a direção do sinal com o vetor de sinais de `research.strategies`. Os testes de `tests/test_quant_routes.py` cobrem as regras de entrada e saída de cada rota com dados sintéticos.

## B.6 Memória RAG (cap. 11)

```powershell
python memoria/scripts/build_memory.py           # reconstrói o índice
bot.bat ask "regras do setup 9.4"                # consulta
```

## B.7 Este manual

```powershell
python tools/manual_screenshots.py               # refaz as figuras (dados de demonstração; requer Go e Chrome/Edge)
python tools/build_manual.py                     # gera dist/MT5Bot-Guia-Tecnico-<versão>.md, um arquivo único
python -m pytest tests/test_manual.py            # citações e caminhos de código válidos
```

O teste do manual garante que toda citação tem entrada nas referências, que toda referência é citada, que todo caminho de código citado existe, que cada listagem de código continua idêntica ao arquivo de origem e que toda figura existe (cap. 10 §10.7).
