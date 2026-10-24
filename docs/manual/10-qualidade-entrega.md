# 10. Qualidade, testes e entrega

## 10.1 Processo: Spec Driven Development (SDD)

Nenhuma mudança de comportamento entra sem uma spec em `specs/` com requisitos funcionais (FR), não funcionais (NFR) e critérios de aceite no formato Dado/Quando/Então (AC). O fluxo completo está em [`specs/README.md`](../../specs/README.md) e no [`CONTRIBUTING.md`](../../CONTRIBUTING.md):

```
descoberta → ANALYSIS.md → decisões do dono → constituição + specs + ROADMAP
→ épico por fase → ticket (sub-issue) → branch → testes a partir dos AC → código
→ CI verde → PR → merge → PR de fechamento → tag → release
```

**Por que SDD?** Num sistema que opera dinheiro, o requisito precisa ser **verificável antes** de existir código, e cada critério de aceite vira ao menos um teste. A ideia descende da especificação por exemplos e do desenvolvimento guiado por testes [Beck 2002], acrescida de rastreabilidade: o PR cita o ticket, o ticket cita a spec e a spec cita o achado da análise.

## 10.2 Estratégia de testes

| Nível | O que verifica | Exemplos |
|---|---|---|
| Unidade | Funções puras (indicadores, sinais, *scoring*, risco) | `test_indicators`, `test_scoring`, `test_quant_routes` |
| Integração com *test double* | Fluxos que chamam o MT5 | `test_profit_fixes`, `test_setup_wizard` |
| Interface | Layout da TUI e do painel | `maestro/main_ui_test.go`, `test_quant_panel` |
| Estrutural | Todo módulo importa; o pacote instalado importa | `test_imports`, `tools/check_wheel.py` |
| Contrato de workflow | Regras dos workflows do CI | `test_workflows` |
| Ponta a ponta | Instalador instalado, executado e desinstalado | `packaging/windows/smoke.ps1` |

**O MT5 simulado.** `tests/conftest.py` instala um módulo `MetaTrader5` falso *antes* de qualquer import do projeto, e cada teste ajusta respostas com `monkeypatch`. Na taxonomia de [Meszaros 2007] isso é um *fake* com *stubs* configuráveis; a escolha de verificar **estado** (ordens enviadas, arquivos gravados) em vez de interações segue [Fowler 2007]. Os testes não precisam do terminal, rodam em Linux e são determinísticos. O mesmo `conftest` aponta a pasta de dados para um diretório temporário, para que os testes nunca leiam o `config.toml` nem gravem nos trades do usuário.

**Testes de layout da TUI** verificam, em 5 tamanhos de terminal, que nenhuma linha passa da largura e que a tela não passa da altura: uma propriedade de interface testada de forma automática.

## 10.3 Checagem de mutação

Cada teste novo passa por uma **checagem de mutação manual**: o comportamento protegido é quebrado de propósito e confirma-se que o teste falha. Exemplos registrados nos PRs:
- desligar a trava de setups não validados faz o teste do AC-2 falhar;
- aceitar `max_risk_pct = 500` faz o teste de validação falhar;
- voltar ao workflow de ML antigo faz o teste de workflow falhar;
- um nome indefinido faz o lint falhar.

Isso responde à pergunta que a cobertura não responde: **o teste detecta o defeito?** O teste de mutação parte da hipótese do programador competente e do efeito de acoplamento [DeMillo, Lipton & Sayward 1978]; ver o *survey* de [Jia & Harman 2011].

## 10.4 Cobertura

`coverage` mede linhas executadas em `mt5bot` e `interfaces`; o piso (`fail_under = 60`, medido em 61%) **só sobe**. É um detector de regressão, ou seja, um PR que apaga testes falha, e não uma meta de qualidade em si: cobertura alta com testes fracos é possível, e a mutação (§10.3) cobre essa lacuna. Os módulos menos cobertos (ML/mentoria, `paper_tracker`, `brain_worker`) estão identificados para evolução.

## 10.5 Integração contínua

`.github/workflows/ci.yml`, a cada PR e a cada push na `main`:

| Job | Gate |
|---|---|
| Lint | `ruff` (regras E9 + F: erros de sintaxe, nomes indefinidos, imports quebrados) |
| Python | pytest + cobertura em **Windows e Ubuntu × Python 3.10 e 3.13** |
| Wheel | Constrói, instala num venv limpo e importa todos os módulos do `site-packages` |
| Maestro | `go vet`, `go test -race`, build para Windows |
| Instalador | Build e *smoke* do `Setup.exe` (em PRs de empacotamento) |

`tools/ci.ps1` (`bot.bat ci`) roda os mesmos passos localmente. A regra de ouro: **nada entra com CI vermelho, e nenhum gate é enfraquecido para passar** (constituição, princípio 4). Isso vem de [Humble & Farley 2010]; [Forsgren, Humble & Kim 2018] associam essas práticas a desempenho de entrega e estabilidade.

**Lição registrada.** O CI deste projeto ficou vermelho por dois meses (agosto a outubro de 2026) sem ninguém perceber: um script solto na raiz chamava `exit()` durante a coleta dos testes, e o CI nem instalava as dependências. Testes que "passam na minha máquina" não protegem nada se ninguém olha o CI. A correção e a análise de causa raiz estão no PR #9 e em `specs/ANALYSIS.md`.

## 10.6 Empacotamento e instalador

- **Pacote Python:** descoberta automática de pacotes no `pyproject.toml`. A lista manual anterior esquecia `mt5bot.mentorship`.
- **Instalador Windows** (`packaging/windows/`, decisão D2):
  1. Python **embutido** oficial (3.12) com o `._pth` configurado;
  2. dependências instaladas como *wheels* `win_amd64`, com `xgboost-cpu` (2 MB em vez de mais de 100 MB);
  3. Maestro compilado com `-trimpath -s -w`;
  4. **apenas arquivos versionados** (`git ls-files`), sem lixo local;
  5. Inno Setup: instalação por usuário sem administrador, atalhos e desinstalador que preserva os dados do usuário.
  O resultado tem cerca de 48 MB.
- **Por que Python embutido?** Isolamento: não depende nem conflita com um Python instalado pelo usuário, e a versão é fixa e reproduzível.
- **Smoke test** num Windows limpo do GitHub, com 15 verificações: tamanho, instalação silenciosa, import de todos os módulos com o Python embutido, Modo Quant, Maestro, `bot.bat`, desinstalação e dados preservados.

- **Pacote Linux/macOS via Wine** (`packaging/wine/`, decisão D1, **experimental**): a biblioteca `MetaTrader5` só existe para Windows, então o pacote leva o mesmo Python embutido e roda tudo, inclusive o terminal MT5, dentro de um prefixo Wine. O `install.sh` cria o prefixo, copia o programa e cria o comando `mt5bot`. O *smoke* no CI (`packaging/wine/smoke.sh`) roda o pacote num Ubuntu com Wine.

**Lição registrada (issue #47).** O *smoke* do Wine "estourava o tempo" de 10 minutos, o que parecia lentidão. O log mostrava outra coisa: `Unimplemented function ucrtbase.dll.crealf`. O Wine 9 do Ubuntu não implementa uma função da biblioteca C que o numpy usa; o processo abortava e o depurador automático do Wine (`winedbg`) ficava esperando até o *timeout*. Duas lições gerais: (1) um *timeout* é um sintoma, não um diagnóstico, e vale procurar no log o que aconteceu **antes** dele; (2) testes devem **falhar rápido**, e por isso o *smoke* agora desliga o depurador automático e mede cada etapa separadamente (iniciar o Python, importar numpy e pandas, importar todos os módulos).

## 10.7 Ferramentas do próprio manual

O manual é tratado como código: ele tem testes e é gerado de forma reproduzível.

| Ferramenta | O que garante |
|---|---|
| `tests/test_manual.py` | Toda citação tem referência e toda referência é citada; todo caminho de código citado existe; cada **listagem** ("Listagem N.M — arquivo") continua idêntica ao código-fonte, linha a linha e na ordem; toda figura existe |
| `tools/manual_screenshots.py` | Gera as figuras das interfaces com **dados de demonstração** e uma pasta de dados temporária, de modo que nenhum dado real do usuário aparece; usa o Chrome ou o Edge *headless* e, para o Maestro, um teste Go que grava a tela (`maestro/screenshot_test.go`) |
| `tools/build_manual.py` | Junta tudo num arquivo único com as figuras embutidas, publicado em cada *release* |

O teste das listagens resolve um problema clássico de documentação técnica: trechos de código copiados para o texto envelhecem em silêncio quando o código muda. Aqui, uma listagem desatualizada derruba o CI.

## 10.8 Release

Tag `vX.Y.Z` → CI completo → instalador e *smoke* → checagem de que a tag bate com o `pyproject.toml` → `SHA256SUMS` conferido → GitHub Release com notas extraídas do CHANGELOG (`tools/release_notes.py`). Em PRs que mexem no workflow, ele roda como **ensaio**, sem publicar. Versões em SemVer [Preston-Werner 2013]; changelog no formato *Keep a Changelog*; commits em *Conventional Commits*.

**Reprodutibilidade:** binários não ficam no git (decisão D8). Eles vêm sempre do CI, a partir do código da tag, com checksums: qualquer pessoa pode conferir que o instalador corresponde ao código publicado.

## 10.9 Referencial teórico

[Beck 2002] TDD; [Meszaros 2007] *test doubles*; [Fowler 2007] verificação de estado × comportamento; [DeMillo, Lipton & Sayward 1978; Jia & Harman 2011] teste de mutação; [Humble & Farley 2010] entrega contínua; [Forsgren, Humble & Kim 2018] métricas de entrega; [Preston-Werner 2013] SemVer.
