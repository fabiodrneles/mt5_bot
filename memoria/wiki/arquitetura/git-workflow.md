# Fluxo de Versionamento e Branches (Git Workflow)

## Visão Geral
Para garantir que o robô (MT5Bot) opere com o mais absoluto rigor e segurança de engenharia, o projeto adota uma estrutura simplificada de *Gitflow* baseada em ambientes restritos de produção e laboratório.

## Estrutura de Branches
O projeto utiliza apenas **duas branches centrais** para organizar a evolução do código sem colocar em risco o capital de produção.

### 1. `main` (Produção / Ambiente Seguro)
- **Status:** Intocável e rigorosamente validada.
- **Função:** É a branch que roda "valendo dinheiro" (Conta Real). Nenhum desenvolvimento, teste ou experimento é feito diretamente nela.
- **Regra de Atualização:** Código só entra na `main` através de *Merge* vindo da branch de testes, **somente após 100% dos testes da suíte PyTest passarem com sucesso**.

### 2. `testes` (Homologação / Staging)
- **Status:** Laboratório de inovação.
- **Função:** É a branch onde criamos novas funcionalidades, novos indicadores, modificamos a arquitetura ou atualizamos dependências.
- **Regra de Atualização:** Sempre que formos começar um novo desenvolvimento, os engenheiros (ou IAs) farão o `checkout` nesta branch, farão os testes iterativos com o MetaTrader5 rodando em conta DEMO. Assim que o recurso estiver provado, ele é promovido para a `main`.

## Benefícios
- **Limpeza:** Nenhuma branch de `feat/` (funcionalidades isoladas antigas) ficará flutuando eternamente no repositório.
- **Rollback Imediato:** Se um erro grave passar despercebido para a produção, basta reverter o último merge na `main` para devolver o robô à última versão estavelmente lucrativa.
- **Isolamento de Estado:** Impede que um teste mal sucedido ou um código não finalizado envie uma ordem com lote ou gatilho errôneo para a bolsa de valores durante um pregão.
