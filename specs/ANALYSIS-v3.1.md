# Análise de lacunas para ficar acima da média — v3.1.0

> Data: 2026-10-24 · Base: commit `f1bb0b3` (branch `main`, v3.1.0)
> Método: leitura do código, das limitações já documentadas no guia técnico (cap. 13) e comparação com um **padrão de referência** de robôs de varejo bem feitos e de prática profissional de pesquisa quantitativa (López de Prado 2018; Bailey & López de Prado 2014; Chan 2013).

## 1. Resumo executivo

A v3.1.0 é instalável, testada e honesta nos números. A engenharia de entrega (CI, instalador, release reproduzível, manual) já está acima do que se vê na maioria dos robôs de varejo. **As lacunas estão em três frentes:**

1. **Proteções que falham abertas.** Algumas travas de capital liberam a entrada quando dão erro, e o robô não se reconecta sozinho ao MT5.
2. **Evidência estatística de um só corte.** As rotas foram validadas com uma separação IS/OOS, sem *walk-forward*, sem correção para comparações múltiplas e sem acompanhar se o desempenho ao vivo continua dentro do esperado.
3. **Operação sem supervisão.** Os alertas existem só como função solta, não há relatório periódico, os segredos ficam em `.env` em texto puro e as dependências não são auditadas.

A recomendação é uma sequência de quatro fases (v3.2 → v4.0). Ela fecha primeiro o que protege dinheiro, depois o que sustenta a evidência, depois a operação e por fim o produto.

## 2. Padrão de referência ("acima da média")

Um robô de varejo **médio** opera uma estratégia, tem stop e um backtest de um corte só. Um robô **acima da média** tem, além disso:

| # | Capacidade | MT5Bot v3.1.0 | Spec |
|---|---|---|---|
| R1 | Toda trava de capital falha **fechada** (erro = não opera) | ⚠️ parcial | 007 |
| R2 | Limites de perda diária, semanal e por sequência; *kill switch* com retomada manual | ⚠️ só diária | 007 |
| R3 | Dimensionamento que nunca arrisca sem vantagem estimada | ❌ piso de Kelly | 007 |
| R4 | Reconexão automática, verificação do SL na corretora após cada ordem e tratamento de *retcodes* | ❌ | 008 |
| R5 | Validação *walk-forward*, correção para comparações múltiplas, intervalos de confiança | ❌ um corte IS/OOS | 009 |
| R6 | Um simulador de referência usado por todas as ferramentas | ⚠️ quatro simuladores | 010 |
| R7 | Acompanhamento ao vivo × esperado, com pausa automática se a estratégia degradar | ❌ | 011 |
| R8 | Alertas e resumo diário fora da máquina (celular) | ⚠️ função existe, não está ligada | 012 |
| R9 | Diário de decisões auditável (por que entrou, por que recusou) e relatórios | ⚠️ só log texto | 013 |
| R10 | Segredos protegidos, dependências auditadas, SBOM, binário assinado | ❌ | 014 |
| R11 | Risco de carteira: exposição agregada e correlação entre rotas | ❌ | 015 |
| R12 | ML sem vazamento temporal, avaliado por expectativa, com falha visível | ❌ | 016 |
| R13 | Configuração pela interface, atualização verificada e relatórios para leigos | ⚠️ só leitura | 017 |
| R14 | Testes de propriedade e mutação no núcleo de risco; orçamento de desempenho no hardware-alvo | ⚠️ cobertura 60% | 018 |

## 3. Observações (verificadas no código)

### Críticas — podem custar dinheiro

| # | Observação | Evidência | Spec |
|---|---|---|---|
| G1 | A trava de perda diária do Modo Quant **libera a entrada** se der erro ao calcular | `mt5bot/execution/quant_manager.py:163-164` (`except` → só `warning`, segue para a ordem) | 007 |
| G2 | O meio Kelly arrisca no mínimo 0,5% mesmo quando $f^* \le 0$ (sem vantagem) e usa 1% quando a probabilidade é inválida | `mt5bot/risk/risk_calculator.py:52-59` | 007 |
| G3 | O robô não se reconecta: se o terminal cair, o laço continua chamando o MT5 sem `initialize()` de novo | `tools/quant_runner.py:217-256` (um só `initialize`) | 008 |
| G4 | Depois de abrir a posição, ninguém confere se o SL ficou gravado na corretora (princípio 1 da constituição) | `quant_manager.py:207-213` | 008 |
| G5 | O Modo Quant não confere o *spread* antes de entrar; os caminhos clássicos conferem | `quant_manager.py:_scan_quant` × `config.SYMBOL_MAX_SPREAD_POINTS` | 008 |

### Altas — sustentam (ou não) a evidência

| # | Observação | Evidência | Spec |
|---|---|---|---|
| G6 | Validação com uma só separação IS/OOS; 3.150 combinações testadas sem *Deflated Sharpe* | guia cap. 8 §8.9, cap. 13 §13.1 | 009 |
| G7 | Quatro simuladores com regras de custo diferentes | guia cap. 12 §12.5 | 010 |
| G8 | *Swap* por dias de calendário; erra a rolagem tripla | `tools/quant_research/research.py:90` | 010 |
| G9 | Nada compara o resultado ao vivo com o que o simulador previa | guia cap. 13 §13.4 item 2 | 011 |
| G10 | Sem limite de perda semanal nem de perdas seguidas | `config.py:233-240` | 007 |

### Médias — operação e segurança

| # | Observação | Evidência | Spec |
|---|---|---|---|
| G11 | Telegram implementado em `logger.py:45`, mas sem configuração no `config.toml`, sem eventos de trade e sem resumo diário | `mt5bot/core/logger.py`, `.env.example` | 012 |
| G12 | Segredos (token do Telegram) em `.env` texto puro | `.env.example` | 014 |
| G13 | Sem `pip-audit`, `govulncheck`, Dependabot nem SBOM; dependências sem versão máxima | `pyproject.toml:16-25`, `.github/` | 014 |
| G14 | Instalador sem assinatura (D3 = a) | `packaging/windows/mt5bot.iss` | 014 |
| G15 | Duas rotas em índices correlacionados podem perder juntas; não há limite de risco agregado | `config.QUANT_ROUTES` | 015 |
| G16 | ML: separação aleatória (`train_test_split`), métrica de acurácia e *fail-open* silencioso em 5 caminhos | `tools/train_xgboost.py:47`, `mt5bot/mentorship/ml_xgboost.py:59-134` | 016 |
| G17 | Saída parcial de 50% nunca acontece com lote 0,01 | `config.py:47-49` | 007 |

### Baixas — produto e engenharia

| # | Observação | Spec |
|---|---|---|
| G18 | O dashboard é só leitura; mudar configuração exige `bot.bat config --edit` | 017 |
| G19 | Sem aviso de nova versão | 017 |
| G20 | Cobertura mínima de 60%; sem testes de propriedade nem de mutação no risco | 018 |
| G21 | Sem medição de memória e latência do ciclo no hardware-alvo | 018 |
| G22 | Diário de decisões só existe como texto no log | 013 |

## 4. Pontos fortes (manter)

- Entrega reproduzível: CI em Windows e Ubuntu, instalador, pacote Wine verificado, checksums.
- Pesquisa quant com custos reais e teste de sorte, e equivalência vela a vela entre teste e produção.
- Arquitetura *stateless* com SL/TP na corretora e ações restritas ao MAGIC.
- Guia técnico acadêmico com listagens verificadas por teste.

## 5. Fases propostas

| Fase | Tema | Specs | Versão |
|---|---|---|---|
| 4 | Capital blindado | 007, 008 | `v3.3.0` |
| 5 | Evidência robusta | 009, 010, 011 | `v3.4.0` |
| 6 | Operação supervisionada | 012, 013, 014, 018 | `v3.5.0` |
| 7 | Produto completo | 015, 016, 017 | `v4.0.0` |

A Fase 7 é *major* porque 015 muda o dimensionamento quando há várias rotas, e isso altera o comportamento ao vivo de quem já usa.

## 6. Decisões em aberto

| # | Pergunta | Opções | Recomendação |
|---|---|---|---|
| D9 | Kelly com $f^* \le 0$ | a) recusar o trade; b) cair no risco fixo | **a**: sem vantagem estimada, não há por que arriscar |
| D10 | Limites novos de perda | semanal 5%, 4 perdas seguidas, *drawdown* 15% do pico | **valores propostos**, ajustáveis no `config.toml` |
| D11 | Pausa automática por degradação (011) | a) pausa a rota e avisa; b) só avisa | **a**, com retomada manual |
| D12 | Onde guardar segredos | a) Gerenciador de Credenciais do Windows (`keyring`); b) `.env` cifrado com DPAPI | **a**: padrão do sistema, sem senha extra |
| D13 | Teto de risco agregado | soma dos riscos abertos ≤ 2× o maior limite por rota | **valor proposto**; correlação medida em 015 |
| D14 | ML ao falhar | a) *fail-closed* (recusa); b) *fail-open* com alerta | **b** por padrão (o ML não está nas rotas quant), **a** configurável |
| D15 | Edição de configuração pelo dashboard | a) sim, só em `127.0.0.1` com *token* de sessão; b) não | **a** |
| D16 | Assinatura de código | a) continuar sem; b) certificado; c) SignPath (gratuito para *open source*) | **c**: avaliar a elegibilidade; se não der, **a** |

## 7. Referências

[López de Prado 2018] *Advances in Financial Machine Learning*; [Bailey & López de Prado 2014] *The Deflated Sharpe Ratio*; [Bailey et al. 2017] *The Probability of Backtest Overfitting*; [Chan 2013] *Algorithmic Trading*; [Page 1954] *Continuous Inspection Schemes* (CUSUM); [Wald 1945] *Sequential Tests of Statistical Hypotheses*. As entradas completas estão em `docs/manual/referencias.md`; as novas entram no PR que implementar cada spec.
