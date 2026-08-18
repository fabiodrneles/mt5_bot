# A Filosofia de Tecnologia Embarcada no MT5Bot

Embora o MT5Bot não seja um código rodando fisicamente em um chip de geladeira ou em um Arduino, ele foi **arquitetado, desenhado e programado seguindo puramente os preceitos de Engenharia de Sistemas Embarcados (Embedded Systems)**.

Isso significa que não o tratamos como um "scriptzinho de Python", mas sim como um **motor industrial pesado e enxuto**. Abaixo estão as 4 características que conferem ao nosso robô esse status de Tecnologia Embarcada:

### 1. Restrição Extrema de Hardware (O fator principal)
Sistemas embarcados nascem para rodar sob estritas restrições de recursos (pouca CPU, pouca RAM). O nosso robô foi projetado para tracionar de forma limpa em um **Core i3 de 4ª geração com apenas 4GB de RAM**.
Por conta disso, tomamos decisões de engenharia específicas para "hardware de borda":
- **Golang no Maestro:** Usamos Go para a orquestração e UI justamente porque seu consumo de memória RAM beira o zero, deixando o PC livre para a execução.
- **RAG via BM25 (Sem Redes Neurais):** Nossa base de memória permanente não utiliza embeddings vetoriais pesados, mas sim matemática lexical pura (BM25 implementado nativamente) para indexação, de forma a nunca travar a máquina.
- **Ambiente Headless:** Ausência de interfaces gráficas baseadas em janelas (Tkinter, PyQt). O bot roda de forma silenciosa num terminal de baixo custo computacional.

### 2. Máquina de Estados Finita (FSM - Finite State Machine)
O coração lógico do robô (`strategy.py`) foi desenvolvido como uma Máquina de Estados Finita. Essa é a exata mesma arquitetura utilizada para escrever o *firmware* de um marcapasso ou de componentes de aviação.
O robô só existe e transita entre estados rígidos e controlados: `SCANNING` → `SIGNAL_READY` → `IN_POSITION`. Ele não "pensa fora da caixa", não engasga tentando ser multitarefa e roda em um loop temporal (heartbeat) focado 100% no seu estado isolado, o que garante previsibilidade matemática absoluta.

### 3. Operação Autônoma e "Headless"
A verdadeira tecnologia embarcada liga na tomada e funciona sozinha, sem intervenção humana. O MT5Bot espelha isso com maestria:
- Possui um arquivo `config.py` fechado como única fonte da verdade.
- Mantém seu próprio estado na memória persistente em disco (via `persistence.py`), sabendo exatamente onde parou para o caso de uma queda de energia ou desligamento abrupto.
- Opera um sistema de *logs* rotativos, autogerenciando seu próprio histórico de execução sem intervenção manual.

### 4. Integração Direta como Atuador e Leitura de Sensores
Em sistemas embarcados clássicos, temos a leitura de sensores (temperatura, pressão) convertida em ações de atuadores (motores, relés).
O MT5Bot realiza uma leitura crua direta do MetaTrader 5 em milissegundos (o mercado atuando como nossos **sensores de ticks e preço**). Em resposta aos dados brutos e baseado em sua lógica condicional de estado, ele dispara chamadas de rede diretas (ordens MT5), que agem como seus **atuadores**.

> **Resumo:** Mais do que código, o MT5Bot adota a mentalidade de um hardware. Ele é enxuto, direto ao ponto, tolerante a falhas (resiliente) e capaz de sobreviver em ambientes de baixa capacidade computacional sem perder o pulso do mercado.
