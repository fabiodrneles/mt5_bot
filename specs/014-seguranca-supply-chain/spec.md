# 014 — Segredos e cadeia de suprimentos

- **Prioridade:** P1
- **Status:** Draft
- **Código afetado:** `mt5bot/core/user_config.py`, novo `mt5bot/core/secrets.py`, `pyproject.toml`, `.github/workflows/*`, novo `.github/dependabot.yml`, `packaging/windows/*`, `SECURITY.md`
- **Resolve:** G12, G13, G14 · R10

## Contexto

Um robô de trading roda numa máquina com acesso a uma conta com dinheiro. A média do varejo distribui executáveis sem assinatura e guarda credenciais em texto puro. Acima da média é tratar o projeto como software que mexe com dinheiro: segredos no cofre do sistema, dependências auditadas a cada PR e um caminho claro para relatar vulnerabilidades.

## Estado atual (verificado)

- O *token* do Telegram fica em `.env` (texto puro), conforme o `.env.example`.
- As dependências em `pyproject.toml` têm só versão mínima; o instalador baixa a versão mais nova do dia do build.
- Não há Dependabot, `pip-audit`, `govulncheck`, SBOM nem `SECURITY.md`.
- O instalador não é assinado (D3 = a).

## Requisitos funcionais

- **FR-1** (D12) Segredos MUST ser guardados no Gerenciador de Credenciais do Windows via `keyring` (no Wine, *fallback* para arquivo com permissão restrita e aviso). `bot.bat secret set telegram_token` pede o valor sem eco.
- **FR-2** O `.env` continua aceito por compatibilidade, com aviso de migração; nenhum segredo MUST aparecer em log, painel, dashboard ou relatório (teste varre as saídas).
- **FR-3** O build do instalador MUST usar dependências **travadas com hash** (`requirements-lock.txt` gerado por `pip-compile --generate-hashes`) e `pip install --require-hashes`.
- **FR-4** O CI MUST rodar `pip-audit` (Python) e `govulncheck` (Go). Vulnerabilidade conhecida com correção disponível = CI vermelho.
- **FR-5** MUST existir `.github/dependabot.yml` para pip, gomod e github-actions, semanal.
- **FR-6** A release MUST publicar um SBOM (CycloneDX) e atestados de proveniência (`actions/attest-build-provenance`) dos binários.
- **FR-7** As *actions* dos workflows MUST ser fixadas por SHA de commit.
- **FR-8** MUST existir `SECURITY.md` com o canal privado de relato (GitHub Security Advisories).
- **FR-9** (D16) A assinatura do instalador SHOULD ser feita via SignPath (gratuito para *open source*), se aprovado; caso contrário, o README documenta como verificar o SHA256 e o atestado.

## Requisitos não funcionais

- **NFR-1** `keyring` é a única dependência nova (leve, pura Python).

## Critérios de aceite

- **AC-1** Dado o *token* salvo com `bot.bat secret set`, o robô envia notificações sem `.env`, e o *token* não aparece em `<dados>/logs/*`.
- **AC-2** Dado um `requirements-lock.txt` com um hash alterado, o build do instalador falha.
- **AC-3** Dada uma dependência com CVE conhecida fixada no lock, o job de auditoria fica vermelho.
- **AC-4** A release tem `sbom.cdx.json` e o atestado verificável com `gh attestation verify`.

## Fora de escopo

- Autenticação da conta MT5 (é feita pelo próprio terminal).

## Decisões

- D12, D16 — ver [ANALYSIS-v3.1 §6](../ANALYSIS-v3.1.md#6-decisões-em-aberto).
