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
| [ANALYSIS-v3.1.md](ANALYSIS-v3.1.md) | Análise de lacunas para ficar acima da média (2026-10-24, v3.1.0) |
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
| 007 | [Proteção de capital à prova de falhas](007-protecao-capital/spec.md) | P0 | Draft |
| 008 | [Execução resiliente](008-execucao-resiliente/spec.md) | P0 | Draft |
| 009 | [Validação estatística robusta](009-validacao-estatistica/spec.md) | P1 | Draft |
| 010 | [Simulador único de referência](010-simulador-unico/spec.md) | P1 | Draft |
| 011 | [Monitoramento ao vivo × esperado](011-monitoramento-ao-vivo/spec.md) | P1 | Draft |
| 012 | [Alertas e notificações](012-alertas-notificacoes/spec.md) | P1 | Draft |
| 013 | [Diário de decisões, auditoria e relatórios](013-auditoria-relatorios/spec.md) | P1 | Draft |
| 014 | [Segredos e cadeia de suprimentos](014-seguranca-supply-chain/spec.md) | P1 | Draft |
| 015 | [Risco de carteira e novas rotas](015-risco-carteira/spec.md) | P2 | Draft |
| 016 | [ML sem vazamento e com falha visível](016-ml-sem-vazamento/spec.md) | P2 | Draft |
| 017 | [Experiência de produto](017-experiencia-produto/spec.md) | P2 | Draft |
| 018 | [Engenharia de qualidade avançada](018-engenharia-qualidade/spec.md) | P1 | Draft |

Estado atual (2026-10-24): Fases 1, 2 e 3 concluídas (v2.13.0, v2.14.0, v3.0.0); pacote Wine verificado e guia técnico completo em v3.1.0. v3.2.0: pesquisa ampla (guia cap. 14), diário de sinais e rotas em estudo. Fases 4–7 especificadas (specs 007–018, [ANALYSIS-v3.1](ANALYSIS-v3.1.md)); aguardam as decisões D9–D16.

Status possíveis: `Draft` → `Approved` → `In Progress` → `Done`.
