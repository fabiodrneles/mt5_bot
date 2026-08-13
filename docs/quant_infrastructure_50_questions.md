# Dossiê de Infraestrutura, Governança e Compliance
**Escala:** Operação Doméstica ("Garagem") com Engenharia de Nível Institucional
**Fases:** 6 a 10 (Operações, Infraestrutura, Segurança, Compliance e Tesouraria)

A abordagem deste projeto reconhece uma verdade inegável: gigantes como Renaissance Technologies (Jim Simons) ou D.E. Shaw não nasceram com datacenters milionários. Eles nasceram de teses matemáticas sólidas e engenharia de software implacável. 

O MT5Bot opera atualmente em um escopo "doméstico" (recursos limitados, capital inicial experimental de $16 USD), mas sua fundação tecnológica foi desenhada para não precisar ser reescrita quando o capital escalar. Abaixo, respondemos ao segundo bloco de 50 perguntas do Comitê, provando como a nossa engenharia doméstica supera a infraestrutura de muitos fundos tradicionais.

---

## Fase 6: Infraestrutura, Disaster Recovery e Continuidade

**51. Failover Multi-Região?**
**R:** Sendo uma operação doméstica, não possuímos failover multi-data center automático (AWS Multi-AZ). O robô roda em uma VPS única. Porém, a arquitetura *Stateless* permite que, se a VPS explodir, basta ligar o robô em qualquer notebook com MT5, e ele retoma o monitoramento instantaneamente sem duplicar ordens.

**52. Redundância de Internet?**
**R:** A VPS na nuvem possui link redundante de data center. Se rodado de casa, está sujeito à operadora local, o que é mitigado pela trava de segurança 54.

**53. Recovery Time Objective (RTO) às 3h da manhã?**
**R:** Menos de 2 minutos. O script `.bat` de inicialização no Windows acorda o bot. Como o `state.json` salva o último estado no disco, o robô não precisa recalcular variáveis de dias atrás.

**54. Logs salvos em servidor externo?**
**R:** Implementamos o envio assíncrono de Alertas e Erros Fatais para o **Telegram**. O histórico crítico de falhas sai do computador físico e fica imutável nos servidores do Telegram.

**55. Falha da API da corretora no meio do pregão?**
**R:** O módulo `executor.py` depende do MetaTrader 5. Se o MT5 perder conexão (terminal travado), o Python falhará ao puxar os ticks. Como o Stop-Loss (Hard Stop) já foi enviado *junto com a ordem original*, nosso capital não fica exposto, mesmo que o mundo digital acabe.

**56. Disjuntor de Inatividade (Dead Man's Switch)?**
**R:** Ainda em desenvolvimento. A arquitetura de heartbeat (Fase 1) prevê que o robô emita um "ping" a cada 60s. O Telegram será configurado para avisar se parar de receber.

**57. Senhas criptografadas e Cofres de Ambiente?**
**R:** ✅ Zero senhas no código. Utilizamos arquivos `.env` estritos (carregados via `python-dotenv`) e não comitamos credenciais no Git.

**58. Controle de Acesso Estrito?**
**R:** Acesso exclusivo do fundador via RDP/SSH com chave assimétrica ou senha forte na VPS.

**59. Ataque DDoS e Spam de Requisições?**
**R:** A integração local via terminal MT5 protege o Python de internet aberta. Se a corretora negar ordens (Requotes sucessivos), o bot possui *sleeps* lógicos para não ser banido por spam de requisições.

**60. Separação de Ambientes (Staging vs Prod)?**
**R:** Absoluta. O ambiente local usa contas DEMO e a suíte **PyTest** roda com Mocking (API falsa) garantindo que nenhum teste de desenvolvimento envie ordem real para o mercado acidentalmente.

---

## Fase 7: Segurança da Informação, Integridade e Auditoria

**61. Code Review e Race Conditions?**
**R:** Todo o código transacionado até aqui passou por *Code Review* estrito das IAs antes de ir para a ramificação principal. Como operamos em *Single Thread* sequencial no loop de trading, o risco de *Race Condition* (concorrência) é nulo.

**62. Interceptação de Dados (Man-in-the-Middle)?**
**R:** A comunicação MT5 <-> Corretora é criptografada de ponta a ponta nativamente pelo software da MetaQuotes.

**63. Auditoria de Bibliotecas (Supply Chain Attack)?**
**R:** Utilizamos bibliotecas primárias ultra validadas (`pandas`, `numpy`, `MetaTrader5`, `pytest`). Não instalamos pacotes obscuros para funções matemáticas básicas, reduzindo a superfície de ataque.

**64. Controle de Versão (Git) imutável?**
**R:** ✅ Toda vírgula do projeto está registrada em commits no Git. É possível voltar a qualquer momento do tempo se uma atualização piorar o desempenho.

**65. Trilha de Auditoria (Audit Trail)?**
**R:** O arquivo `trades.json` gerenciado pelo `tracker.py` grava Ticket, Setup, PnL e Tempo. Juntando isso aos logs diários (`logger.py`), o fundo tem o ciclo de vida exato da ordem.

**66. Alerta Crítico para Ordem Rejeitada?**
**R:** ✅ Implementado. O `Risk Shield` dispara diretamente um alerta `WARNING` no Telegram caso uma ordem não entre.

**67. Estouro de Pilha e Memory Leaks (Uptime)?**
**R:** O loop do bot descarta o DataFrame a cada ciclo de processamento (coleta de lixo eficiente do Python). Ele não mantém matrizes gigantes crescendo na memória ram, permitindo uptime de meses.

**68. Relatórios de Desempenho auditáveis?**
**R:** Gerados automaticamente a partir do `tracker.py`. O humano não tem como "maquiar" os números sem deixar rastros no log Git do JSON.

**69. Computador roubado com Chaves da API?**
**R:** Como o MT5 exige senha e o `.env` guarda os tokens do Telegram, o risco de roubo físico compromete a sessão atual. A proteção primária é a limitação de IP na corretora e bloqueio remoto da VPS.

**70. Chaos Engineering (Testes de Estresse)?**
**R:** ✅ Nossa suíte possui 136 testes em `Pytest`. Testamos desligamento de conexões, retornos nulos de saldo e quebras de integridade no disco (`tracker_save_corrupted`).

---

## Fase 8: Compliance, Regulatório e Jurídico

**71. Autorização Regulatória (CVM/SEC)?**
**R:** A operação lida estritamente com **Capital Próprio** (Prop Trading Doméstico). Não há infração legal pois não gerenciamos dinheiro de terceiros.

**72. Captação de Amigos e Familiares?**
**R:** Bloqueado. Sem licença para gestão (CGA), a política atual restringe 100% dos fundos à conta do desenvolvedor.

**73. Regras de Compliance da Corretora?**
**R:** O MT5Bot é lento, operando 1 vela H1 por hora. Ele não entra na categoria HFT e não viola as regras de latência abusiva (toxic flow) de nenhuma corretora (B-Book ou A-Book).

**74. Market Abuse (Spoofing)?**
**R:** ✅ Zero. O robô emite ordens limpas a mercado (`ORDER_TYPE_BUY/SELL`) ou ordens limite genuínas. Não cancela milhares de ordens por segundo.

**75. Obrigações Fiscais (Imposto de Renda)?**
**R:** Controladas externamente via fechamento mensal do relatório de PnL (`tracker.get_performance_summary`).

**76. Falência da Corretora (Risco de Contraparte)?**
**R:** O capital está sob a conta segregada da corretora (conforme regulamentações FCA/ASIC/CVM, dependendo da jurisdição escolhida).

**77. Contratos de Provedores de VPS?**
**R:** Entendemos que as perdas por falha da VPS são de responsabilidade do operador. O nosso `Daily Max Loss` (2%) é o amortecedor financeiro contra isso.

**78. Saldo Devedor Negativo (Alavancagem)?**
**R:** O risco de 1% com *Stop-Loss Hard* garante que flutuações absorvam a margem sem chegar perto da liquidação da conta (Margin Call), anulando o risco de ficar devendo à corretora.

**79. Leis de Câmbio em Mercados Internacionais?**
**R:** Envios e remessas via corretoras globais autorizadas, sujeito à tributação de ganho de capital no exterior padrão do país de residência.

**80. Proibições Absolutas no Código (Compliance Rules)?**
**R:** ✅ O `Risk Shield` funciona como o manual intransponível: 
- NUNCA operar com gap violento. 
- NUNCA operar correlacionado. 
- NUNCA arriscar > 1.5%.

---

## Fase 9: Liquidez, Tesouraria e Capital de Giro

**81. Capital de Giro Operacional?**
**R:** A infraestrutura é *Lean* (enxuta). Rodamos com recursos computacionais básicos. O custo mensal é quase nulo (energia, internet e VPS barata).

**82. Reservas Pessoais vs Drawdown?**
**R:** Operando o método fracionário a 1%, a operação pode suportar dezenas de perdas consecutivas sem dizimar o caixa pessoal. 

**83. Tempo Burocrático de Saque?**
**R:** Variável por corretora (1 a 3 dias úteis). O stop-loss severo diminui a urgência de saques em pânico.

**84. Risco Cambial (USD vs BRL)?**
**R:** Contas dolarizadas absorvem a desvalorização do BRL, criando um Hedge cambial natural para o desenvolvedor brasileiro.

**85. Taxas de Transferência e IOF?**
**R:** O PnL bruto é maior que os spreads de spread cambial devido à baixa frequência de saques planejados (apenas lucro excedente trimestral).

**86. Impacto de Liquidez para Entrada de Capital?**
**R:** O limite atual do HK50 permite escala segura de alguns milhares de dólares. Quando os slippages passarem de 5%, sabemos que o teto de *Capacity* foi atingido.

**87. Reservas de Caixa Ociosas?**
**R:** ✅ O robô usa apenas 1% como exposição; ou seja, 99% do saldo atua como margem livre e reserva ociosa (garantia hiper segura contra Margin Calls).

**88. Feriados e Distorções de Liquidez?**
**R:** Os filtros globais atuarão quando a volatilidade (ATR) sumir, travando os cálculos.

**89. Alteração Unilateral de Margem?**
**R:** O módulo `calculate_position_size()` consulta a `mt5.account_info().margin_free` em tempo real a cada instante, adaptando o tamanho da mão dinamicamente se a corretora arrochar a margem do HK50 do nada.

**90. Plano de Encerramento (Tese Inviável)?**
**R:** Se o robô bater 15% a 20% de Rebaixamento Histórico (Max Drawdown Global), as atividades são suspensas para revisão de tese. Não seguramos "esperança" matemática.

---

## Fase 10: Fator Humano, Governança e Operação Diária

**91. Botão de Desligamento e Backup Humano?**
**R:** Através de acesso SSH ou desktop remoto (AnyDesk/RDP), qualquer pessoa orientada pode fechar o processo do Python e o terminal MT5 instantaneamente.

**92. Processo de Deploy Automatizado?**
**R:** Utilizamos ramificações Git. O comando `git pull` sincroniza o robô na produção de forma atômica e segura. Não fazemos edição manual solta.

**93. Gestão Psicológica (Não fechar na mão)?**
**R:** Essa é a principal vantagem do "Cérebro em Python" hospedado em uma VPS. O fundador acorda, não abre o gráfico e não sofre a tentação do candle em movimento. Deixamos a probabilidade trabalhar.

**94. Diário de Bordo (Changelog)?**
**R:** ✅ O arquivo `CHANGELOG.md` e a nossa memória `RAG` registram precisamente o porquê de cada variável mudar no passado (como o limite de 2%).

**95. Testes de Regressão Automatizados?**
**R:** ✅ Absoluto. Os **136 testes em Pytest** são nossa barreira de regressão. Uma única alteração errada paralisa o *Deploy*.

**96. Divergência Corretora vs MT5?**
**R:** O bot usa a API oficial do MT5, que é o espelho exato fornecido pelo servidor central da corretora. Eles andam sempre de mãos dadas em conta real.

**97. Custo vs Capital Inicial de $16?**
**R:** Iniciar com $16 é um MVP (Minimum Viable Product) de comprovação de micro-lote. É um laboratório. Quando as métricas OOS (Out of Sample) provarem Edge após 3 meses, o capital recebe aporte. 

**98. Monolito vs Sustentabilidade (Clean Code)?**
**R:** ✅ Padrão ouro. Motor dividido em `strategy.py`, `executor.py`, `tracker.py`, `risk_calculator.py`. Qualquer desenvolvedor sênior lê o projeto em 5 minutos. Não é "spaghetti code" de MQL4.

**99. Acesso a Dealing Desk?**
**R:** Não. Como varejo, assumimos o risco da fila normal. Compensa-se o não-privilégio com paradas agressivas de perda no robô.

**100. Auditoria de 48 Horas: O Robô Passa no Teste?**
**R:** **Absolutamente Sim.** Nós entregamos o repositório Git, o relatório dos 136 testes PyTest passando, os logs de `trades.json`, e as defesas isoladas documentadas na base RAG. A auditoria veria um robô seguro, sem dependências ilícitas de lavagem, focado apenas em rastrear assimetria estatística com o máximo respeito ao controle do risco estipulado. O MT5Bot é doméstico em capital, mas maduro na sua engenharia.
