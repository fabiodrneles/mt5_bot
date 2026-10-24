# Metas, ideias e observações para o futuro do projeto

> Registrado em 2026-10-24, depois da pesquisa ampla (guia, cap. 14) e da release v3.2.0. Serve de base para transformar as conclusões da pesquisa em metas e projetos. Complementa o [roteiro de publicação](ROTEIRO.md).

## 1. O que este projeto já é

**Para engenharia de software, o projeto já é forte, e o lucro do robô quase não importa para isso.** Quem avalia um engenheiro olha *como* ele construiu:

- **Arquitetura:** dois processos (Maestro em Go e cérebro em Python) conversando por JSON em stdin/stdout, sem estado e com watchdog. Instalador Windows (Inno Setup, Python embutido) e pacote Linux/macOS via Wine, testados no CI.
- **Disciplina de testes:** mais de 280 testes, CI em Windows e Ubuntu com Python 3.10 e 3.13, um teste que impede o simulador de "ver o futuro" (*look-ahead*) e um teste que confere linha a linha se o código citado no manual existe.
- **Processo profissional:** *Spec Driven Development* (specs com critérios de aceite), um PR por tarefa, *releases* reproduzíveis com checksum e um guia técnico acadêmico de 14 capítulos com referencial teórico.
- **Engenharia de dados:** seis defeitos nos dados de uma corretora, encontrados e provados com ticks (guia, cap. 14 §14.4). É o tipo de trabalho que times de dados de bancos e fintechs fazem.
- **Pesquisa reprodutível:** cerca de 130 mil configurações com protocolo pré-registrado, FDR, *walk-forward*, Deflated Sharpe e Monte Carlo, num *pipeline* que sobrevive a queda de energia, fim de cota da IA e disco cheio.

**O que falta não é uma estratégia que ganhe muito. Falta mostrar isso ao mundo**, no formato que engenheiros reconhecem.

## 2. Correções de entendimento (para não esquecer)

- **Não é verdade que "nenhum setup teve lucro".** O RSI2 no US500 tem lucro comprovado em 10 anos (t 2,48) e opera no robô. A mesma regra, sem reotimizar, funcionou no US100 (t 2,10) e no US30. O que não passou nos filtros foram as estratégias **novas**.
- **"Se não tem lucro com $16, não tem com $600" está errado nas duas pontas.** Há lucro com $16, só que pequeno e com risco de 7,5% por trade. Com mais capital o **percentual** é o mesmo; o capital compra **liberdade de risco** (arriscar 1% em vez de 7,5%) e **diversificação** (mais rotas). Ver o cap. 14 §14.9 e o artigo, §5.4.
- **O 9.x testado na pesquisa ampla era uma versão simplificada** (forex e CFDs intradiários, entrada a mercado e alvo fixo de 2×). O Palex opera ações da B3 no diário, com **ordem stop acima da máxima** e **saída conduzida pela MME9**. Os testes simplificados não dizem que "o 9.x não funciona"; dizem que *aquela versão, naqueles mercados*, não paga o custo. O teste fiel ao livro está registrado em `docs/validacao-9x-fiel.md`.
- **"Muitos ganham com o 9.x" e "a pesquisa não achou vantagem" podem ser verdade ao mesmo tempo**, por três motivos: mercados e tempos gráficos diferentes, forma de saída e o viés de sobrevivência (quem perde raramente aparece para contar).

## 3. Cenário de referência: $600 por 1 ano (números da pesquisa)

Com risco de 1% por trade ($6):

| Rota | Lote possível | Lucro esperado no ano | Confiança |
|---|---|---|---|
| US500 RSI2 | ~5× o lote mínimo | ~$5 | Boa (10 anos, t 2,5) |
| US100 RSI2 (sairia do estudo) | 1× o lote mínimo | ~$5 | Boa (t 2,1) |
| US30 RSI2 | 1× o lote mínimo (risco de 1,2%) | ~$4 | Média (t 1,1) |
| HK50 PULLB | ~26× o lote mínimo | entre $0 e ~$35 | Fraca |

**Total esperado: algo entre $15 e $50 no ano (cerca de 2% a 8%), com incerteza real.** O US500 teve 3 anos negativos em 10. Não é "nada", mas também não é máquina de dinheiro; a renda fixa costuma render mais, com menos risco.

## 4. Capital mínimo viável (descoberta da pesquisa)

Nos produtos alavancados de varejo, a menor posição tem risco fixo em dinheiro. Abaixo de um capital mínimo, a conta é forçada a arriscar demais ou a não operar. Com 1% de risco por trade, o mínimo é de cerca de **$36 em ações CFD, $157 em índices, $567 em cripto, $601 em forex e $7.478 em commodities**. Para uma conta pequena, **o aporte vale centenas de vezes mais que a estratégia**: com $16, só o lucro levaria uns 85 anos para chegar ao mínimo do US500; aportes de $50 por mês levam uns 2 meses. Isso vale para alavancagem com lote mínimo, não para investimento comum (fundos, ETFs, Tesouro).

## 5. Metas propostas

### Curto prazo (1 a 3 meses)

1. **Teste justo do 9.x** (ordem stop, saída pela MME9, gráfico diário). ✅ Ver `docs/validacao-9x-fiel.md`.
2. **Publicar o preprint dos defeitos de dados** no SSRN, a partir de `artigo-data-artifacts.md`: completar os `[TODO]`, gerar as figuras e criar o DOI no Zenodo.
3. **Primeiros 3 textos técnicos** (LinkedIn ou blog): "o candle de abertura que mente", "o spread que o candle esconde", "como testei um simulador contra *look-ahead*".
4. **README em inglês atualizado** e capítulo 14 em inglês.
5. **Diário de sinais em uso:** 30 ou mais anotações para medir o próprio olho.

### Médio prazo (3 a 9 meses)

6. **`backtest-guard`: o laboratório como ferramenta aberta.** Um pacote Python (`pip install`) que qualquer pessoa usa no próprio histórico do MetaTrader para:
   - detectar os defeitos de dados (abertura irreal, spread mínimo escondido, rollover e reabertura);
   - simular com custo realista (spread, comissão, swap triplo, regras de abertura);
   - dizer se o resultado sobrevive à sorte (*walk-forward*, DSR, FDR, Monte Carlo de ruína com o capital da pessoa);
   - responder **"em que mercado, tempo gráfico e forma de saída este setup dá lucro?"**, em vez de "dá ou não dá".

   É útil para quem opera, inclusive o 9.x, e não depende de o robô ficar rico. Ferramentas usadas viram estrelas no GitHub, citações e reputação.
7. **Repetir a auditoria de dados em 2 ou 3 corretoras.** Se os defeitos aparecerem em outras, o achado passa a ser sobre o mercado, e não sobre uma empresa.
8. **Fase 4 do roadmap** (`specs/ROADMAP.md`, v3.3.0): proteção de capital à prova de falhas e execução resiliente. É pré-requisito para a operação autônoma.
9. **Histórico ao vivo transparente:** publicar o que as rotas fizeram contra o que o simulador previa, inclusive os meses ruins (spec 011).

### Longo prazo (9 meses ou mais)

10. **Operação autônoma com intervenção mínima** (specs 007–014): limites de perda, *kill switch*, reconexão, pausa de rota degradada e alertas no celular. O robô opera sozinho e só chama quando algo sai do normal.
11. **Submissão a congresso** (por exemplo, o Encontro Brasileiro de Finanças) com o artigo revisado e replicado em mais de uma corretora.
12. **Formação formal** (opcional): mestrado em engenharia financeira, econometria ou ciência de dados aplicada, usando o projeto como proposta de pesquisa.

## 6. Princípios para seguir motivado

- **O resultado negativo honesto é raro e valioso.** A maior parte do conteúdo sobre robôs mostra só o que deu certo. Documentar por que quase tudo falha, com método, é o que constrói autoridade.
- **Ferramentas e textos constroem reputação técnica**; lucro de robô, não. Um engenheiro é lembrado pelo que outros conseguem usar e pelo que ele explica bem.
- **Teste justo antes de veredito.** Um setup só é descartado depois de testado como o autor dele opera (mercado, tempo gráfico, tipo de ordem, saída).
- **Pesquisa não é recomendação.** Divulgar método, código e resultados, sempre com o aviso. Não publicar dados brutos da corretora.
