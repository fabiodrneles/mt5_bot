# Memória Permanente + RAG — MT5Bot

> **Para qualquer IA que estude o projeto: comece aqui.** Este diretório é a **memória de longo prazo** do MT5Bot. Ele existe para que você entenda o projeto inteiro — dos setups do Palex às decisões de arquitetura — **sem depender do limite de contexto** da conversa.

---

## 1. O que é isto?

Uma **base de conhecimento permanente** consultável por **RAG lexical (BM25)**. Conteúdo:

1. **Os livros do Palex** (Estratégias Operacionais + Fundamentos) — texto integral extraído dos PDFs.
2. **`aprofundamento.md`** — a conversa de arquitetura (maestro Go + cérebro Python, princípios de design).
3. **A spec de design** do motor multi-setup e do maestro Go.
4. **Conhecimento destilado** pela IA (`wiki/`) — setups, fundamentos, arquitetura, em páginas concisas.

Quando qualquer IA (eu, você, outra) precisa de contexto sobre o projeto, **consulta este RAG em vez de tentar lembrar**.

---

## 2. Estrutura

```
memoria/
├── README.md           # ← este arquivo
├── raw/                # FONTES IMUTÁVEIS (nunca editar)
│   ├── estrategias-operacionais.txt   # livro 1 (974KB, ~36k linhas)
│   ├── fundamentos.txt                # livro 2 (836KB, ~34k linhas)
│   ├── aprofundamento.md              # conversa de arquitetura
│   └── design-spec.md                 # spec do maestro multi-setup
├── wiki/               # CONHECIMENTO DESTILADO (a curadoria da IA)
│   ├── index.md        # índice de todas as páginas
│   ├── conceitos/      # setups 9.1–9.4, PC, FFFD, DiNapoli, IFR2, SAR,
│   │                   # MM21/MM200, expectativa matemática, plano de trade, risco
│   └── arquitetura/    # maestro Go, cérebro Python, fases, estado do código
├── index/              # ÍNDICE BM25 GERADO (não editar; reconstruir via script)
│   ├── memoria_index.json
│   └── meta.json
└── scripts/
    ├── build_memory.py   # indexa raw/ + wiki/ → índice BM25
    └── query_memory.py   # consulta o RAG
```

---

## 3. Por que BM25 e não embeddings?

O hardware alvo do projeto é **i3 4ª geração com 4GB RAM** (documentado em `aprofundamento.md`).

| Técnica | RAM | Velocidade | Instalação |
|---|---|---|---|
| **BM25 (escolhido)** | ~MB | ~1ms/consulta | **nenhuma** (stdlib puro) |
| TF-IDF (sklearn) | ~100MB+ | ~1ms | `pip install scikit-learn` |
| Embeddings (MiniLM) | ~400MB+ | lento na CPU | `pip install sentence-transformers` (~100MB) |

**BM25 lexical supera embeddings MiniLM em RAG de baixa RAM** — para domínio técnico (termos como "MME9", "IFR2", "setup 9.1"), a correspondência lexical é mais precisa que semântica. A literatura de 2026 confirma: TF-IDF/BM25 com SVM atinge 93.2% de precisão em roteamento de consultas — superior a MiniLM embeddings por ~3.1 pontos F1.

**Trade-off aceito**: consultas sinônimas/parafraseadas exigem termos próximos (ex: "virada EMA9" ≈ "inversão MME9"). O `query_memory.py` normaliza acentos, então "gestão" casa com "gestao".

---

## 4. Como consultar (comandos)

```powershell
# Básico — top-4 blocos mais relevantes
python memoria\scripts\query_memory.py "regras do setup 9.2 correção rápida"

# Mais/fewer resultados
python memoria\scripts\query_memory.py "ponto contínuo MM21" -k 1

# Filtrar por tipo de fonte
python memoria\scripts\query_memory.py "expectativa matemática" --kind wiki   # só destilado
python memoria\scripts\query_memory.py "pay off" --kind raw                   # só livros/spec

# Mostrar bloco inteiro (sem truncar a 500 chars)
python memoria\scripts\query_memory.py "saída parcial breakeven" --text
```

**Comportamento**: se o índice não existir, o script chama `build_memory.py` automaticamente.

---

## 5. Como funciona por dentro (para IA que quer contribuir)

### 5.1. Chunking (`build_memory.py`)
- Cada fonte é dividida em blocos de ~1200 chars com sobreposição de 120 (respeitando quebras de linha).
- Cada bloco vira um "documento" com id único (hash MD5 da posição), `path`, `title`, `kind` (raw/wiki) e `text`.

### 5.2. Tokenização
- Regex `[a-z0-9]+(\.\d+)?` — preserva termos técnicos com número ("9.1" → token `9.1`).
- **Normalização de acentos** (NFD + remoção de combining marks): "gestão" → "gestao" em ambos os lados.
- **Stopwords** em português removidas.

### 5.3. Índice BM25
- `df[termo]` = nº de documentos com o termo.
- `postings[termo][doc_idx] = tf` — listas invertidas.
- `N`, `avgdl` — parâmetros globais.
- Salvos em `memoria_index.json` (UTF-8, compacto).

### 5.4. Scoring (`query_memory.py`)
- BM25 com **k1=1.5, b=0.75** (padrão Okapi).
- `idf = log(1 + (N - df + 0.5)/(df + 0.5))`.
- Soma os scores dos termos da consulta; retorna top-k com score e fonte.

### 5.5. Correção de encoding
- Windows console usa cp1252; o script reconfigura `stdout` para UTF-8 (evita `UnicodeEncodeError`).

---

## 6. Como atualizar (quando adicionar conhecimento)

**Nunca editar `raw/`** (fontes imutáveis). Para conhecimento novo:

1. **Edite/crie uma página em `wiki/`** seguindo o padrão das existentes:
   - `conceitos/setup-9X.md` — novos setups.
   - `arquitetura/*.md` — decisões de arquitetura.
   - `fontes/*.md` — resumos de fontes.
2. **Atualize `wiki/index.md`** se criar página nova.
3. **Reindexe**:
   ```powershell
   python memoria\scripts\build_memory.py
   ```
4. **Verifique** que a busca encontra o novo conteúdo:
   ```powershell
   python memoria\scripts\query_memory.py "termos do novo conhecimento" --kind wiki
   ```

### Convenções de escrita na wiki
- Página = **um tópico** (setups, indicador, decisão).
- Cabeçalho com `Fonte:` (path em `raw/`) e `Status:`.
- Regras em **lista numerada**, ponto-chave em destaque.
- Referências ao código com `file.py` e (quando souber) função.
- Conciso — a wiki é para leitura rápida; o detalhe fica no `raw/`.

---

## 7. Estatísticas atuais

```
Chunks:    1.824
Termos:    25.8k
Fontes:    26 (4 raw + 22 wiki)
Build:     < 2s
Consulta:  ~1ms
```

---

## 8. FAQ para IA

**Q: Preciso consultar o RAG antes de responder qualquer coisa?**
A: Sim, para perguntas sobre **regras de setups, arquitetura, decisões e o que está implementado**. Para dúvidas puramente de código Python, os testes e o código são a fonte.

**Q: E se o índice estiver desatualizado?**
A: Reindexe: `python memoria\scripts\build_memory.py`. Sempre que editar `wiki/`, reindexar.

**Q: Posso adicionar embeddings depois?**
A: Sim — a camada léxica é a base. Para RAG semântico futuro, o chunking já está pronto; bastaria trocar a camada de scoring. Mas não é necessário no hardware atual.

---

*Este diretório é a memória do projeto. Mantenha-a viva: documente o que aprender.*
