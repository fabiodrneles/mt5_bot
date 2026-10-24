# Contribuindo com o MT5Bot

O projeto segue **Spec Driven Development (SDD)**: nenhuma mudança de comportamento entra sem spec e critérios de aceite. O processo completo está em [`specs/README.md`](specs/README.md); aqui fica o guia prático.

## Ambiente

```powershell
git clone https://github.com/fabiodrneles/mt5_bot.git
cd mt5_bot
pip install -e ".[dev]"        # dependências + pytest, ruff, build
.\bot.bat build                # compila o Maestro (precisa de Go)
.\bot.bat ci                   # roda localmente os mesmos passos do CI
```

Os testes usam um MetaTrader 5 simulado (`tests/conftest.py`) e uma pasta de dados temporária: não precisam do terminal aberto e nunca tocam nos seus trades reais.

## Fluxo

1. **Issue primeiro.** Use o template "Tarefa" ou "Bug". Cada tarefa de fase é uma sub-issue do épico da fase.
2. **Branch por issue:** `<tipo>/<nº-da-issue>-<descrição-curta>`, por exemplo `fix/13-maestro-version-path`. Tipos: `feat`, `fix`, `docs`, `ci`, `chore`, `test`.
3. **Testes a partir dos critérios de aceite**, depois o código. Cada `AC-*` vira pelo menos um teste.
4. **Checagem de mutação:** quebre de propósito o que o teste novo protege e confirme que ele falha.
5. **Commits** em [Conventional Commits](https://www.conventionalcommits.org/), em inglês e no imperativo: `feat: add --watch mode`.
6. **Antes do push:** `.\bot.bat ci` verde.
7. **PR por issue**, usando o template. A descrição começa com `Closes #N · Épico #M · Spec NNN`.
8. **CI verde é obrigatório** para o merge. Nunca enfraqueça um teste ou um gate para passar.

## Regras do projeto

- A [constituição](specs/constitution.md) vale para todo PR. As principais regras:
  - nada abre posição sem SL na corretora;
  - nada mexe em posição ou ordem sem o MAGIC do robô;
  - só opera ao vivo o que foi validado fora da amostra.
- Logue com `logging`, nunca com `print()` no caminho de produção.
- Dependência nova e pesada só com justificativa em spec: o alvo é um i3 com 4 GB de RAM.
- Trabalho descoberto no meio de uma tarefa vira **issue nova**, não carona no PR atual.
- Arquivos de status (`specs/README.md`, checkboxes do ROADMAP, `CHANGELOG.md`) só mudam no PR de fechamento da fase.

## Fechamento de fase e versões

Com todos os PRs da fase mergeados, um PR de fechamento atualiza o status das specs, o ROADMAP e o `CHANGELOG.md` ([Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/)). O dono cria a tag `vX.Y.Z` ([SemVer](https://semver.org/lang/pt-BR/)).
