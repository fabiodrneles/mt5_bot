# 11. Memória do projeto: RAG com BM25

## 11.1 Propósito

`memoria/` é uma base de conhecimento consultável que guarda os livros-fonte da estratégia, as decisões de arquitetura e os resultados de pesquisa. Ela serve a humanos (`bot.bat ask "pergunta"`) e a assistentes de IA, que consultam a base antes de responder sobre o projeto (`AGENTS.md`). É uma forma simples de *Retrieval-Augmented Generation* (RAG) [Lewis et al. 2020]: em vez de depender da memória de contexto do modelo, recuperam-se os trechos relevantes e eles são fornecidos como evidência.

| Pasta | Conteúdo |
|---|---|
| `raw/` | Fontes **imutáveis** (texto extraído dos livros, spec de design, aprofundamento) |
| `wiki/` | Conhecimento destilado e atualizado a cada decisão (setups, arquitetura, pesquisa, este processo) |
| `index/` | Índice gerado (não versionado) |
| `scripts/` | `build_memory.py` (indexa), `query_memory.py` (consulta) |

## 11.2 Pipeline de indexação

`build_memory.py`:
1. **Normalização:** decomposição Unicode NFD com remoção de acentos (`"ação"` → `"acao"`), para que a busca não dependa de acentuação.
2. **Tokenização:** expressão regular de palavras, caixa baixa, remoção de *stopwords* em português e de tokens com 1 caractere.
3. ***Chunking*:** janelas de até 1.200 caracteres com **sobreposição de 120**, para que um conceito na fronteira entre dois blocos apareça inteiro em pelo menos um deles.
4. **Estatísticas** por termo (frequência de documento) e comprimento médio dos blocos, salvas em JSON.

Hoje são cerca de 1.880 blocos e 26 mil termos, de 41 fontes.

## 11.3 Ranqueamento BM25

`query_memory.py:bm25_score`, a função *Okapi BM25* [Robertson & Zaragoza 2009]:

$$\text{score}(D, Q) = \sum_{q \in Q} \text{IDF}(q)\cdot \frac{f(q,D)\,(k_1 + 1)}{f(q,D) + k_1\left(1 - b + b\,\frac{|D|}{\text{avgdl}}\right)}$$

$$\text{IDF}(q) = \ln\!\left(1 + \frac{N - n(q) + 0{,}5}{n(q) + 0{,}5}\right)$$

com $k_1 = 1{,}5$ e $b = 0{,}75$, os valores clássicos da literatura [Manning, Raghavan & Schütze 2008]. Interpretação:
- **IDF:** termos raros ("RSI2MR", "Kelly") pesam mais que termos comuns. O "+1" dentro do logaritmo mantém o IDF positivo mesmo para termos presentes em mais da metade dos blocos, o que a fórmula original permite ser negativo.
- **Saturação ($k_1$):** a 10ª ocorrência de um termo acrescenta muito menos que a 1ª.
- **Normalização de tamanho ($b$):** blocos longos não vencem só por terem mais palavras.

## 11.4 Por que BM25 e não *embeddings*?

| Critério | BM25 (escolhido) | *Embeddings* densos |
|---|---|---|
| Memória e CPU | Desprezível; biblioteca padrão | Modelo de centenas de MB; inferência pesada num i3/4 GB |
| Dependências | Nenhuma | `sentence-transformers` e PyTorch |
| Termos técnicos exatos | Excelente ("9.4", "RSI2MR", "PULLB") | Pode diluir códigos e siglas raras |
| Sinônimos e paráfrases | Fraco | Forte |

Para um vocabulário técnico e estável, com siglas e nomes de setups, a busca lexical é competitiva. Em avaliações *zero-shot* heterogêneas, o BM25 permanece uma linha de base difícil de superar para muitos modelos densos [Thakur et al. 2021]. A limitação é a semântica: uma pergunta com palavras diferentes das do texto pode não encontrar o bloco certo. A mitigação é manter a `wiki/` escrita com os termos que as pessoas usam.

## 11.5 Manutenção

- `raw/` nunca é editada. Conhecimento novo vai para a `wiki/`, seguido de `python memoria/scripts/build_memory.py`.
- Cada decisão relevante do projeto (pesquisa de estratégias, interfaces, processo SDD) virou uma página da `wiki/`. Assim a memória acompanha o código e qualquer pessoa ou IA que chegue ao projeto encontra o **porquê** das decisões, não só o **o quê**.

## 11.6 Referencial teórico

[Robertson & Zaragoza 2009] BM25; [Manning, Raghavan & Schütze 2008] recuperação de informação; [Lewis et al. 2020] RAG; [Thakur et al. 2021] BEIR (BM25 × modelos densos).
