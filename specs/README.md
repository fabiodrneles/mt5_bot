# Specs — MT5Bot

Este diretório organiza o desenvolvimento em **Spec Driven Development (SDD)**: nenhuma mudança de comportamento entra no código sem uma spec que a descreva e critérios de aceite que a verifiquem.

## Fluxo

```text
spec.md (O QUÊ / POR QUÊ) → revisão → testes a partir dos AC → implementação → status: Done
```

1. **Especificar:** `FR-*`, `NFR-*` e `AC-*` (Dado/Quando/Então).
2. **Resolver decisões:** antes de implementar ([ANALYSIS.md §7](ANALYSIS.md#7-decisões-em-aberto)).
3. **Testar primeiro:** cada `AC-*` vira ao menos um teste.
4. **Implementar:** o PR referencia os IDs (`002 FR-1, AC-2`).
5. **Fechar:** o status é atualizado no PR de fechamento da fase.

Convenções: MUST/SHOULD/MAY (RFC 2119). Prioridades: **P0** (bloqueia uso real), **P1** (confiabilidade), **P2** (polimento). Commits e código em inglês; specs, issues e PRs em português.

## Documentos

| Documento | Conteúdo |
|---|---|
| [ANALYSIS.md](ANALYSIS.md) | Relatório da verificação (2026-10-24, v2.12.0) |
| [constitution.md](constitution.md) | Princípios inegociáveis |
| [ROADMAP.md](ROADMAP.md) | Tarefas por fase |

## Specs

| ID | Spec | Prioridade | Status |
|---|---|---|---|
| 001 | [CI e qualidade](001-ci-qualidade/spec.md) | P0 | Done |
| 002 | [Instaladores e empacotamento](002-instaladores-empacotamento/spec.md) | P0 | In Progress |
| 003 | [Dados e configuração do usuário](003-dados-config-usuario/spec.md) | P0 | Done |
| 004 | [Higiene do repositório](004-higiene-repositorio/spec.md) | P0 | Done |
| 005 | [Segurança operacional](005-seguranca-operacional/spec.md) | P1 | Done |
| 006 | [Primeiro uso](006-primeiro-uso/spec.md) | P2 | Done |

Estado atual (2026-10-24): Fases 1, 2 e 3 concluídas (v2.13.0, v2.14.0, v3.0.0); pacote Wine verificado e guia técnico completo em v3.1.0. Nenhuma pendência aberta.

Status possíveis: `Draft` → `Approved` → `In Progress` → `Done`.
