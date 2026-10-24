# 017 — Experiência de produto

- **Prioridade:** P2
- **Status:** Draft
- **Código afetado:** `interfaces/dashboard.py`, `mt5bot/core/user_config.py`, `maestro/`, `bot.bat`, `packaging/windows/mt5bot.iss`
- **Resolve:** G18, G19 · R13

## Contexto

O público-alvo (princípio 8) é leigo. Hoje ele vê tudo pelo dashboard, mas para mudar qualquer coisa precisa abrir um arquivo TOML. Também não sabe quando sai uma versão nova com correções de segurança.

## Requisitos funcionais

- **FR-1** (D15) O dashboard MUST ter uma página **Configuração editável** para as chaves documentadas do `config.toml` (risco por rota, limites de perda, notificações), com a mesma validação de `user_config` e mensagem de erro por campo.
- **FR-2** A edição MUST exigir um *token* de sessão gerado ao abrir o dashboard (anti-CSRF) e só escutar em `127.0.0.1`. Toda alteração é registrada no diário (013) com o valor antigo e o novo.
- **FR-3** Mudanças que aumentam risco (subir `max_risk_pct`, desligar um limite, `allow_unvalidated_live`) MUST pedir confirmação explícita digitada, como o assistente faz para conta real.
- **FR-4** O Maestro e o dashboard MUST avisar quando houver versão nova (consulta à API de releases do GitHub no máximo 1 vez por dia, desligável), mostrando o link e o resumo do CHANGELOG. A atualização em si continua manual (baixar e rodar o instalador).
- **FR-5** O dashboard MUST ter uma página **Relatórios** que lista e abre os relatórios de 013.
- **FR-6** Toda a interface (painel, dashboard, Maestro, mensagens de erro do `bot.bat`) MUST estar disponível em pt, en e es (o console ainda está só em português).
- **FR-7** Um modo **demonstração** SHOULD permitir abrir o dashboard e o Maestro com os dados de demonstração usados no manual, sem MT5, para quem quer conhecer o produto.

## Requisitos não funcionais

- **NFR-1** Sem *framework* JS nem CDN; o dashboard continua um arquivo servido pelo `http.server`.
- **NFR-2** Acessibilidade WCAG 2.1 AA nas páginas novas (rótulos visíveis, contraste, teclado).

## Critérios de aceite

- **AC-1** Dado `max_risk_pct = 500` enviado pelo formulário, o valor é recusado com a mensagem no campo e o arquivo não muda.
- **AC-2** Dado um POST sem o *token* de sessão, a resposta é 403.
- **AC-3** Dado subir o risco do US500 de 12 para 15, a mudança só é gravada depois da confirmação digitada, e o diário registra 12 → 15.
- **AC-4** Dada a API de releases devolvendo uma versão maior, o Maestro mostra o aviso; sem rede, nada quebra e não há aviso.
- **AC-5** Com o idioma `en`, nenhuma string do painel quant aparece em português (teste varre as chaves).

## Fora de escopo

- Atualização automática silenciosa (o instalador não é assinado; ver 014).
- Acesso remoto ao dashboard.

## Decisões

- D15 — edição local com *token* de sessão.
