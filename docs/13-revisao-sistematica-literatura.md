# Revisão Sistemática da Literatura: Recuperação de Informação, LLMs e RAG (Estado da Arte 2024–2026)

Este documento sintetiza o estado da arte em Recuperação de Informação (IR), Modelos de Linguagem de Grande Escala (LLMs) e Retrieval-Augmented Generation (RAG) entre 2024 e início de 2026, com foco nas decisões de arquitetura relevantes para o projeto **BuscaAI**.

A revisão está organizada em quatro eixos:

1. Evolução dos paradigmas de RAG (com diagramas de cada um)
2. Estratégias de recuperação (lexical, densa, híbrida)
3. Aprimoramentos do pipeline (chunking, reranking, query expansion)
4. Arquiteturas modulares e agênticas (com diagramas detalhados)

---

## 1. A evolução dos paradigmas de RAG

A literatura organiza a evolução do RAG em três grandes paradigmas, conforme a taxonomia consolidada por Gao et al. (2024). Cada paradigma representa um aprimoramento progressivo sobre o anterior, mantendo uma relação de herança: Advanced RAG é caso especial de Modular RAG, e Naive RAG é caso especial de Advanced RAG.

---

### 1.1 Naive RAG — o paradigma fundacional

Introduzido por Lewis et al. (2020). Consiste em três etapas lineares, sem otimizações em nenhuma delas.

**Diagrama de fluxo:**

```
═══════════════════════════════════════════════════════════════════
 NAIVE RAG
═══════════════════════════════════════════════════════════════════

INGESTÃO (offline)
─────────────────────────────────────────
[documentos]
      ↓
[chunking simples]              ← divisão por tamanho fixo
      ↓
[embedding denso]               ← um único modelo de embedding
      ↓
[banco vetorial]


CONSULTA (online)
─────────────────────────────────────────
[query do usuário]
      ↓
[embedding da query]
      ↓
[busca por similaridade (top-k)]   ← geralmente k=5 a 10
      ↓
[chunks recuperados]
      ↓
[prompt: query + chunks]
      ↓
[LLM gera resposta]
      ↓
[resposta para o usuário]
```

**Detalhes das etapas:**

1. **Chunking** — divisão por tamanho fixo (ex: 500 caracteres), sem respeitar estrutura.
2. **Embedding** — modelo único (ex: text-embedding-ada-002), aplicado tanto na ingestão quanto na query.
3. **Busca** — similaridade de cosseno entre o vetor da query e os vetores dos chunks, retorna os k mais próximos.
4. **Geração** — todos os chunks recuperados vão para o prompt do LLM, sem reordenação ou filtragem.

**Problemas documentados:**

- **Lost in the Middle** — quando muitos chunks vão para o prompt, o LLM tende a ignorar os do meio.
- **Sem distinção lexical** — perde queries com termos exatos (códigos, IDs, jargão).
- **Sem adaptação** — trata query simples e complexa do mesmo jeito.

---

### 1.2 Advanced RAG — otimizações em pré e pós-retrieval

Surge como resposta às limitações do Naive RAG, adicionando otimizações **antes** e **depois** da etapa de busca, mantendo o pipeline linear.

**Diagrama de fluxo:**

```
═══════════════════════════════════════════════════════════════════
 ADVANCED RAG
═══════════════════════════════════════════════════════════════════

INGESTÃO (offline)
─────────────────────────────────────────
[documentos]
      ↓
[chunking otimizado]            ← recursive / semantic / structure-aware
      ↓
[embedding denso]
      ↓
[banco vetorial]
      ↓
[metadados extraídos]           ← fonte, página, data


CONSULTA (online)
─────────────────────────────────────────
[query do usuário]
      ↓
═══ PRÉ-RETRIEVAL ════════════════════════════════════
      ↓
[query rewriting / expansion]   ← LLM reformula ou expande
      ↓
[HyDE opcional]                 ← gera resposta hipotética
      ↓                            e usa o embedding dela
      ↓
═══ RETRIEVAL ════════════════════════════════════════
      ↓
[busca vetorial (top-N maior)]  ← ex: top-50 em vez de top-5
      ↓
═══ PÓS-RETRIEVAL ════════════════════════════════════
      ↓
[reranking com cross-encoder]   ← reordena os 50
      ↓
[seleção dos top-k finais]      ← top-5 mais relevantes
      ↓
[compressão de contexto]        ← opcional: remove ruído
      ↓
═══ GERAÇÃO ══════════════════════════════════════════
      ↓
[prompt: query + top-k]
      ↓
[LLM gera resposta]
      ↓
[resposta]
```

**Detalhes das técnicas usadas:**

**Pré-retrieval:**

- **Query rewriting** — LLM reformula a query para torná-la mais clara ou específica.
- **Query expansion** — gera sinônimos e termos relacionados (ex: "rescisão" → "rescisão, distrato, encerramento, resilição").
- **HyDE (Hypothetical Document Embeddings)** — pede ao LLM para gerar uma resposta hipotética à query, e usa o embedding **dessa resposta** para buscar (a hipótese é que a resposta hipotética está mais próxima dos chunks reais do que a query crua).

**Pós-retrieval:**

- **Reranking** — modelos cross-encoder analisam pares (query, chunk) com mais cuidado e reordenam.
- **Compressão de contexto** — remove sentenças irrelevantes dos chunks antes de mandar pro LLM, economizando tokens.

---

### 1.3 Modular RAG — o paradigma reconfigurável

O estado da arte atual. Gao et al. (2024) descrevem o framework como uma estrutura "LEGO" — componentes independentes que podem ser combinados de várias formas.

**Diagrama conceitual:**

```
═══════════════════════════════════════════════════════════════════
 MODULAR RAG — pipeline configurável
═══════════════════════════════════════════════════════════════════

                    ┌──────────────────────┐
                    │       ROUTER          │  ← decide o caminho
                    │  (classificador)      │
                    └──────────┬───────────┘
                               ↓
        ┌──────────────┬───────┴───────┬──────────────┐
        ↓              ↓               ↓              ↓
    ┌────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐
    │ Query  │    │ Lexical │    │  Dense  │    │  Graph  │
    │ Module │    │ Retr.   │    │  Retr.  │    │  Retr.  │
    └────┬───┘    └────┬────┘    └────┬────┘    └────┬────┘
         │             │              │              │
         └─────────────┴──────────────┴──────────────┘
                              ↓
                    ┌──────────────────────┐
                    │       FUSION          │  ← RRF, weighted, etc.
                    └──────────┬───────────┘
                               ↓
                    ┌──────────────────────┐
                    │       RERANKER        │  ← opcional
                    └──────────┬───────────┘
                               ↓
                    ┌──────────────────────┐
                    │      VALIDATOR        │  ← opcional
                    │  (verifica qualidade) │
                    └──────────┬───────────┘
                               ↓
                    ┌──────────────────────┐
                    │      GENERATOR        │
                    │       (LLM)           │
                    └──────────┬───────────┘
                               ↓
                          [resposta]
```

**Operadores típicos no Modular RAG:**

| Categoria | Operadores |
|---|---|
| **Indexação** | Chunking, Embedding (denso/esparso), Indexing |
| **Pré-retrieval** | Query rewriting, Query expansion, Routing, Decomposition |
| **Retrieval** | Sparse search, Dense search, Hybrid search, Graph search |
| **Pós-retrieval** | Reranking, Fusion (RRF), Compression, Filtering |
| **Validação** | Quality scoring, Faithfulness check, Web fallback |
| **Geração** | Prompting, Streaming, Citation, Self-reflection |

**O que muda em relação ao Advanced RAG:**

- Pipeline deixa de ser linear fixo — passa a ser um **grafo configurável**.
- Componentes podem ser ativados/desativados/substituídos sem refatorar o resto.
- Roteamento dinâmico permite caminhos diferentes para queries diferentes.
- Suporta orquestração via frameworks como LangGraph e DSPy.

---

## 2. Estratégias de recuperação

### 2.1 Limites do retrieval puramente vetorial

A literatura é convergente em apontar as limitações do retrieval denso isolado: deriva semântica, tensão recall-precisão, lacunas relacionais. Análises de produção identificam padrões consistentes de falha.

**Tipos de query onde a busca densa falha sistematicamente:**

```
PADRÃO DE FALHA DA BUSCA DENSA
─────────────────────────────────────────

Query: "0x80070005"  (código de erro Windows)
       ↓
   embedding → [0.12, 0.45, 0.33, ...]
       ↓
   vetores próximos no espaço:
       ─ "0x80070006"   ← código diferente, semanticamente vizinho ❌
       ─ "0x8007000F"   ← código diferente, semanticamente vizinho ❌
       ─ "ERR_ACCESS"   ← outro código, vetor próximo             ❌

Query: "RTX 4090"  (SKU de produto)
       ↓
   vetores próximos:
       ─ "RTX 4070"     ← produto DIFERENTE                        ❌
       ─ "RTX 4080"     ← produto DIFERENTE                        ❌

→ Códigos exatos têm sinal semântico próximo de zero
→ BM25 acerta isso direto
```

### 2.2 BM25 — fluxo do algoritmo

```
═══════════════════════════════════════════════════════════════════
 BM25 — RETRIEVAL LEXICAL
═══════════════════════════════════════════════════════════════════

INGESTÃO
─────────────────────────────────────────
[documento: "O contrato pode ser rescindido em 30 dias"]
      ↓
[tokenização]
      ↓
[tokens: "contrato", "pode", "ser", "rescindido", "30", "dias"]
      ↓
[índice invertido]
      ↓
"contrato"    → [doc_1, doc_15, doc_42, ...]
"rescindido"  → [doc_1, doc_88, ...]
"30"          → [doc_1, doc_12, doc_77, ...]


CONSULTA
─────────────────────────────────────────
[query: "prazo de rescisão"]
      ↓
[tokens: "prazo", "rescisão"]
      ↓
[para cada token, calcula score em cada doc]
      ↓
   Para cada documento candidato d e termo t:
   ┌─────────────────────────────────────┐
   │  score(t, d) = IDF(t) × TF_norm     │
   │                                       │
   │  IDF(t) = log(N / df(t))             │
   │     ↑ termo raro vale mais           │
   │                                       │
   │  TF_norm = saturação(freq(t,d))     │
   │     ↑ repetir não vale infinito     │
   └─────────────────────────────────────┘
      ↓
[score total = soma dos scores por token]
      ↓
[ordenação por score]
      ↓
[top-k documentos]
```

### 2.3 Busca densa — fluxo do algoritmo

```
═══════════════════════════════════════════════════════════════════
 BUSCA DENSA — RETRIEVAL SEMÂNTICO
═══════════════════════════════════════════════════════════════════

INGESTÃO
─────────────────────────────────────────
[documento]
      ↓
[chunking]
      ↓
[chunk: "O contrato pode ser rescindido em 30 dias"]
      ↓
[modelo de embedding]   ← BERT, OpenAI, Cohere, etc.
      ↓
[vetor denso: [0.23, 0.87, 0.12, 0.95, 0.44, ...]
                ↑ 384 a 3072 dimensões]
      ↓
[banco vetorial com índice HNSW]


CONSULTA
─────────────────────────────────────────
[query: "qual o prazo de rescisão?"]
      ↓
[mesmo modelo de embedding]
      ↓
[vetor da query: [0.21, 0.85, 0.13, 0.93, 0.46, ...]]
      ↓
[busca por similaridade no HNSW]
      ↓
   navegação aproximada no grafo:
   camada superior → camada média → camada base
      ↓
[top-k mais próximos por similaridade de cosseno]
```

### 2.4 Busca híbrida — o consenso atual

Combina BM25 e busca densa. Linha de base recomendada pela literatura recente.

```
═══════════════════════════════════════════════════════════════════
 BUSCA HÍBRIDA — DENSO + ESPARSO + RRF
═══════════════════════════════════════════════════════════════════

INGESTÃO
─────────────────────────────────────────
[chunk]
      ↓
   ┌──┴──┐
   ↓     ↓
[embedding denso]    [embedding esparso (BM25 ou SPLADE)]
   ↓     ↓
   └──┬──┘
      ↓
[banco vetorial salva os DOIS vetores no mesmo ponto]


CONSULTA
─────────────────────────────────────────
[query]
      ↓
   ┌──┴──┐
   ↓     ↓
[embedding denso da query]    [embedding esparso da query]
   ↓                                    ↓
[busca densa: top-50]         [busca esparsa: top-50]
   ↓                                    ↓
   └──────────────┬─────────────────────┘
                  ↓
═══════════════════════════════════════════
       FUSÃO COM RRF
═══════════════════════════════════════════
                  ↓
   Para cada documento d:
   ┌────────────────────────────────────────┐
   │  score_RRF(d) = Σ  1 / (k + rank(d,i))  │
   │                 i                         │
   │                                           │
   │  i = cada lista (densa, esparsa)         │
   │  rank(d,i) = posição de d na lista i     │
   │  k = constante (geralmente 60)           │
   └────────────────────────────────────────┘
                  ↓
   Exemplo:
   doc_A: rank 1 na densa, rank 3 na esparsa
   score = 1/(60+1) + 1/(60+3) = 0.0164 + 0.0159 = 0.0323

   doc_B: rank 5 na densa, rank 1 na esparsa
   score = 1/(60+5) + 1/(60+1) = 0.0154 + 0.0164 = 0.0318
                  ↓
[lista ordenada pelo RRF score]
                  ↓
[top-k finais (ex: top-50 para o reranker)]
```

**Por que RRF é preferido sobre soma de scores:** as escalas dos scores da busca densa (similaridade de cosseno, 0–1) e da busca esparsa (BM25, 0–∞) são completamente diferentes. Somar diretamente é tecnicamente errado. O RRF opera só sobre as **posições**, evitando esse problema.

---

## 3. Aprimoramentos do pipeline

### 3.1 Reranking — fluxo detalhado

```
═══════════════════════════════════════════════════════════════════
 RERANKING COM CROSS-ENCODER
═══════════════════════════════════════════════════════════════════

[query] + [50 candidatos do retrieval híbrido]
      ↓
═══ ETAPA 1: PREPARAR PARES ═══════════════════════
      ↓
   par 1:  (query, chunk_1)
   par 2:  (query, chunk_2)
   par 3:  (query, chunk_3)
   ...
   par 50: (query, chunk_50)
      ↓
═══ ETAPA 2: CROSS-ENCODER ═══════════════════════
      ↓
   Para cada par:
   ┌─────────────────────────────────────┐
   │   [CLS] query [SEP] chunk [SEP]      │
   │            ↓                          │
   │      modelo transformer              │
   │      (BERT, MiniLM, etc.)            │
   │            ↓                          │
   │   score de relevância (0 a 1)        │
   └─────────────────────────────────────┘
      ↓
═══ ETAPA 3: ORDENAÇÃO ═══════════════════════════
      ↓
   reordena 50 candidatos pelo novo score
      ↓
[top-5 ou top-10 finais]
```

**Diferença entre bi-encoder (retrieval) e cross-encoder (rerank):**

```
BI-ENCODER (usado na busca rápida)
─────────────────────────────────
   query   →  encoder  →  vetor_query
                                    ↘
                                    similaridade
                                    ↗
   chunk   →  encoder  →  vetor_chunk

   → vetores podem ser pré-computados
   → busca é rápida (lookup no índice)
   → menos precisa


CROSS-ENCODER (usado no rerank)
─────────────────────────────────
   query + chunk  →  encoder  →  score direto

   → analisa os dois JUNTOS
   → não pode pré-computar
   → mais preciso
   → mais lento (cada par é uma inferência)
```

### 3.2 HyDE — Hypothetical Document Embeddings

Técnica de pré-retrieval que melhora alinhamento entre query e documentos.

```
═══════════════════════════════════════════════════════════════════
 HyDE — HYPOTHETICAL DOCUMENT EMBEDDINGS
═══════════════════════════════════════════════════════════════════

[query: "qual o prazo de rescisão contratual?"]
      ↓
[LLM gera resposta HIPOTÉTICA]
      ↓
   "O prazo de rescisão contratual é geralmente de 30 dias,
    com aviso prévio por escrito. Em contratos com prazo
    determinado, a rescisão antecipada pode incorrer em multa."
      ↓
[embedding da resposta hipotética]
      ↓
[busca no banco vetorial usando ESSE embedding]
      ↓
   ↓ a hipótese: a resposta hipotética está mais próxima
   ↓ dos chunks reais do que a query crua
      ↓
[chunks mais relevantes recuperados]
```

**Quando ajuda:** queries curtas, vagas, ou em forma de pergunta — onde a query crua tem embedding muito diferente dos chunks (que são afirmações).

**Quando atrapalha:** queries técnicas com termos exatos — a "resposta hipotética" gerada pode introduzir vocabulário diferente do que está nos documentos.

---

## 4. Arquiteturas modulares e agênticas

### 4.1 Adaptive RAG — Jeong et al. (2024)

Classificador roteia entre estratégias conforme a complexidade da query.

```
═══════════════════════════════════════════════════════════════════
 ADAPTIVE RAG
═══════════════════════════════════════════════════════════════════

[query]
      ↓
═══ CLASSIFICADOR (T5-Large pequeno) ═══════════════
      ↓
   classifica em 3 categorias:

   ┌─────────┬──────────────────────────────────┐
   │  A      │  query SIMPLES                   │
   │         │  (ex: "quanto é 2+2?")          │
   │         │  → sem retrieval                 │
   ├─────────┼──────────────────────────────────┤
   │  B      │  query SINGLE-HOP                │
   │         │  (ex: "qual o prazo de X?")     │
   │         │  → 1 retrieval + geração         │
   ├─────────┼──────────────────────────────────┤
   │  C      │  query MULTI-HOP                 │
   │         │  (ex: "compare X com Y e diga    │
   │         │   por que Z depende de ambos")  │
   │         │  → retrieval iterativo           │
   └─────────┴──────────────────────────────────┘
      ↓
═══ ROTEAMENTO ═══════════════════════════════════════
      ↓
   ┌──────┬───────────────┬─────────────────────────┐
   ↓      ↓               ↓                         ↓
 [A]    [B]             [C]                       [outro]
   ↓      ↓               ↓
[LLM   [retrieve →     [loop iterativo:
 direto] reranker →      retrieve → reason →
         LLM]            retrieve → reason → ...]
   ↓      ↓               ↓
   └──────┴───────────────┘
                ↓
            [resposta]
```

**Resultado da literatura:** classificador pequeno (T5-Large, 770M params) iguala baselines sempre-caros (que sempre fazem multi-hop) com custo muito menor — porque a maioria das queries reais é A ou B.

---

### 4.2 Self-RAG — Asai et al. (2024)

O próprio LLM decide quando recuperar e quando parar, usando "reflection tokens" especiais.

```
═══════════════════════════════════════════════════════════════════
 SELF-RAG
═══════════════════════════════════════════════════════════════════

[query]
      ↓
═══ LOOP DE GERAÇÃO COM REFLEXÃO ═════════════════════
      ↓
┌─────────────────────────────────────────────────────┐
│                                                       │
│  [LLM gera o próximo trecho da resposta]             │
│           ↓                                            │
│  [LLM gera um REFLECTION TOKEN especial]             │
│           ↓                                            │
│      ┌────┴────────────────────────┐                  │
│      ↓                              ↓                  │
│  [Retrieve]               [No Retrieve]               │
│   → busca chunks            → continua gerando        │
│      ↓                              ↓                  │
│  [chunks chegam]                    │                  │
│      ↓                              │                  │
│  [LLM continua gerando]             │                  │
│  com os chunks                      │                  │
│      ↓                              │                  │
│  [LLM gera REFLECTION TOKEN: IsRel] │                  │
│           ↓                          │                  │
│   chunks relevantes?                │                  │
│      ↓                              │                  │
│  [LLM gera REFLECTION TOKEN: IsSup] │                  │
│           ↓                          │                  │
│   resposta suportada?               │                  │
│      ↓                              │                  │
│  [LLM gera REFLECTION TOKEN: IsUse] │                  │
│           ↓                          │                  │
│   resposta útil?                    │                  │
│      ↓                              ↓                  │
│      └────────────┬─────────────────┘                  │
│                   ↓                                     │
│            terminou?                                    │
│           ↙        ↘                                    │
│         sim         não → volta ao início do loop      │
│           ↓                                              │
└───────────┼──────────────────────────────────────────────┘
            ↓
       [resposta final]
```

**Reflection tokens são tokens especiais aprendidos durante fine-tuning:**

- `[Retrieve]` / `[No Retrieve]` — decide se busca.
- `[IsRel]` — chunk recuperado é relevante? (yes/no)
- `[IsSup]` — a resposta está suportada pelo chunk? (fully/partial/no)
- `[IsUse]` — a resposta é útil? (1-5)

**Custo:** o LLM faz várias chamadas por query, gerando tokens normais e reflexivos. Cada decisão é uma inferência.

---

### 4.3 Corrective RAG (CRAG) — Yan et al. (2024)

Adiciona um avaliador entre o retrieval e a geração. Se o retrieval falha, dispara busca web.

```
═══════════════════════════════════════════════════════════════════
 CORRECTIVE RAG (CRAG)
═══════════════════════════════════════════════════════════════════

[query]
      ↓
[retrieval normal: top-k chunks]
      ↓
═══ AVALIADOR DE RETRIEVAL (modelo leve) ═══════════════
      ↓
   Para cada chunk:
   ┌──────────────────────────────────────┐
   │  modelo classifica:                   │
   │    Correct    (alta confiança)       │
   │    Incorrect  (baixa confiança)      │
   │    Ambiguous  (média confiança)      │
   └──────────────────────────────────────┘
      ↓
   confiança geral = agregação dos scores
      ↓
═══ ROTEAMENTO POR CONFIANÇA ═══════════════════════════
      ↓
   ┌──────────┬──────────────┬───────────────┐
   ↓          ↓              ↓               ↓
[CORRECT]  [AMBIGUOUS]   [INCORRECT]
   ↓          ↓              ↓
[refina    [combina:      [descarta retrieval
 chunks]    chunks         → faz busca WEB
   ↓        internos +     → reformula query
   │        busca web]      → recupera da web]
   ↓          ↓              ↓
   └──────────┴──────────────┘
              ↓
═══ REFINAMENTO ════════════════════════════════════════
      ↓
[decomposição em "knowledge strips"]
      ↓
[filtra strips relevantes]
      ↓
[recompõe contexto enxuto]
      ↓
═══ GERAÇÃO ════════════════════════════════════════════
      ↓
[LLM gera resposta com contexto refinado]
      ↓
[resposta]
```

**Custo documentado:** 4 chamadas de LLM por query no scoring + possível busca web + refinamento. Significativo, mas inferior ao Self-RAG.

---

### 4.4 Agentic RAG — a fronteira

O LLM atua como agente orquestrador, decidindo dinamicamente que ferramentas usar.

```
═══════════════════════════════════════════════════════════════════
 AGENTIC RAG
═══════════════════════════════════════════════════════════════════

[query complexa: "compare a estratégia de IA da Microsoft em 2023
 com a da Google em 2024, e diga qual investiu mais"]
      ↓
═══ AGENTE LLM (planejamento) ════════════════════════════
      ↓
   [LLM analisa a query e cria um PLANO]
      ↓
   Plano:
   1. buscar "estratégia IA Microsoft 2023"
   2. buscar "estratégia IA Google 2024"
   3. buscar "investimento IA Microsoft 2023"
   4. buscar "investimento IA Google 2024"
   5. comparar e responder
      ↓
═══ LOOP DE EXECUÇÃO ═══════════════════════════════════
      ↓
┌───────────────────────────────────────────────────────┐
│                                                         │
│  [agente escolhe a próxima ação]                       │
│            ↓                                            │
│      ┌────┴───────┬──────────────┬────────────┐        │
│      ↓            ↓              ↓            ↓        │
│  [retrieve]   [web search]   [calculator]  [outro]    │
│   na base                                              │
│      ↓            ↓              ↓            ↓        │
│      └────────────┴──────────────┴────────────┘        │
│                ↓                                        │
│  [resultado da ferramenta]                              │
│                ↓                                        │
│  [agente REFLETE sobre o resultado]                    │
│                ↓                                        │
│  preciso de mais informação?                           │
│       ↙              ↘                                  │
│      sim              não                               │
│      ↑                ↓                                 │
│      └─────┐    [agente SINTETIZA]                     │
│            │          ↓                                 │
│            │    [resposta final]                       │
│            │                                            │
└────────────┘
```

**Características-chave:**

- **Planejamento** — o agente cria um plano antes de agir.
- **Tool use** — chama múltiplas ferramentas (retrieval, web search, cálculo, APIs).
- **Reflexão** — avalia resultados intermediários e replaneja.
- **Loop dinâmico** — número de passos não é fixo.

**Custo:** cada query pode gerar 5–20 chamadas de LLM. Latência alta. Custo de tokens muito alto.

---

### 4.5 GraphRAG — Microsoft Research (2024)

Estrutura o corpus como grafo de entidades e relações, em vez de chunks isolados.

```
═══════════════════════════════════════════════════════════════════
 GRAPHRAG
═══════════════════════════════════════════════════════════════════

INGESTÃO (pesada)
─────────────────────────────────────────
[documentos]
      ↓
[chunking]
      ↓
[para cada chunk: LLM extrai entidades e relações]
      ↓
   exemplo do chunk:
   "A Microsoft adquiriu o GitHub em 2018 por 7.5 bilhões"
      ↓
   entidades:  Microsoft, GitHub, 2018, 7.5 bilhões
   relações:   (Microsoft) —adquiriu→ (GitHub)
               (GitHub) —ano→ (2018)
               (GitHub) —valor→ (7.5 bilhões)
      ↓
[grafo de conhecimento agregado]
      ↓
[detecção de COMUNIDADES no grafo]
   (clusters de entidades relacionadas)
      ↓
[LLM gera RESUMO de cada comunidade]
      ↓
[grafo + resumos de comunidades salvos]


CONSULTA
─────────────────────────────────────────
[query]
      ↓
═══ DOIS MODOS DE QUERY ═══════════════════════════════
      ↓
   ┌─────────────┬────────────────────┐
   ↓             ↓
[LOCAL]      [GLOBAL]
 query        query
 específica   geral

   ↓             ↓
[encontra     [usa os resumos
 entidades     de comunidades
 na query]     para responder
   ↓           perguntas amplas]
[navega        ↓
 pelo grafo]  [agrega resumos
   ↓           relevantes]
[chunks
 conectados   ↓
 às entidades]
   ↓           ↓
   └─────┬─────┘
         ↓
   [LLM gera resposta]
         ↓
    [resposta]
```

**Diferença fundamental para RAG vetorial:**

```
RAG VETORIAL              GRAPHRAG
─────────────────         ─────────────────
busca por                 navega por
similaridade              relações
   ↓                         ↓
"trechos parecidos        "entidades conectadas
 com a query"              por relações relevantes"
```

**Quando GraphRAG ganha:** queries que envolvem **múltiplos saltos por relações** — "quais empresas foram adquiridas por X que também investem em Y". RAG vetorial não responde isso bem.

**Quando GraphRAG perde:** queries diretas sobre conteúdo de documentos. E o custo de ingestão é proibitivo em bases grandes.

---

## 5. Síntese e relevância para o BuscaAI

O posicionamento do BuscaAI dentro do estado da arte fica claro à luz da literatura:

**Padrão arquitetural adotado** — Modular RAG, alinhado com Gao et al. (2024) e com a consolidação observada em 2024–2026.

**Estratégia de retrieval** — Hybrid Search (denso + esparso + RRF), alinhada com a literatura unânime que aponta busca híbrida como linha de base superior.

**Reranking** — incorporado como etapa pós-retrieval opcional, alinhado com os achados que apontam o reranker como o componente isolado de maior ganho.

**Pré-filtragem léxica** — etapa antes da busca híbrida, coerente com a função de "porteiro lexical" que BM25 desempenha bem em escala.

**Adaptive routing leve** — uso de arestas condicionais no LangGraph para decisões de fluxo, capturando o espírito do Adaptive RAG sem o custo de um classificador treinado.

**O que ficou fora, com justificativa** — Self-RAG, CRAG e GraphRAG, todos exigem LLM no laço de retrieval ou na ingestão, com custo de tokens incompatível com o caso de uso de bases gigantescas e genéricas. A literatura confirma esses custos como barreiras reais à adoção em produção.

---

## Diagrama final: o pipeline do BuscaAI

```
═══════════════════════════════════════════════════════════════════
 BUSCAAI — ARQUITETURA CONSOLIDADA
═══════════════════════════════════════════════════════════════════

INGESTÃO (offline, assíncrona)
─────────────────────────────────────────
[fontes: PDF, SQL, S3, Notion, ...]
      ↓
[chunking adaptativo por tipo]
      ↓
[metadados naturais extraídos]
      ↓
   ┌──┴──┐
   ↓     ↓
[embedding denso]    [embedding esparso (SPLADE)]
   ↓     ↓
   └──┬──┘
      ↓
[indexa no Qdrant + índice invertido]


CONSULTA (online)
─────────────────────────────────────────
[query]
      ↓
[cache hit?] ─sim→ [retorna do cache]
      ↓ não
═══ PRÉ-FILTRAGEM LÉXICA ════════════════════
[BM25 sobre índice invertido]
[milhões → dezenas de milhares]
      ↓
═══ FILTRO DE METADADOS (opcional) ═══════════
[Filtered HNSW]
      ↓
═══ BUSCA HÍBRIDA ═══════════════════════════
[denso] + [esparso] → [RRF]
[→ ~100 candidatos]
      ↓
═══ RERANKER (condicional) ══════════════════
[cross-encoder]
[→ top 5]
      ↓
═══ GERAÇÃO (se /chat) ═══════════════════════
[prompt: query + histórico + chunks]
      ↓
[LLM gera resposta com streaming]
      ↓
[salva no cache]
      ↓
[resposta + fontes para o usuário]
```

---

## Referências citadas

- **Gao, Y., Xiong, Y., Gao, X., Jia, K., Pan, J., Bi, Y., Dai, Y., Sun, J., Wang, M., Wang, H.** (2024). Retrieval-Augmented Generation for Large Language Models: A Survey. arXiv:2312.10997v3.
- **Gao, Y., Xiong, Y., Wang, M., Wang, H.** (2024). Modular RAG: Transforming RAG Systems into LEGO-like Reconfigurable Frameworks. arXiv:2407.21059.
- **Lewis, P., et al.** (2020). Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks. NeurIPS.
- **Jeong, S., Baek, J., Cho, S., Hwang, S. J., Park, J. C.** (2024). Adaptive-RAG: Learning to Adapt Retrieval-Augmented Large Language Models through Question Complexity. NAACL.
- **Asai, A., et al.** (2024). Self-RAG: Learning to Retrieve, Generate, and Critique through Self-Reflection. ICLR.
- **Yan, S. Q., et al.** (2024). Corrective Retrieval Augmented Generation. arXiv:2401.15884.
- **Edge, D., et al.** (2024). From Local to Global: A Graph RAG Approach to Query-Focused Summarization. Microsoft Research.
- **Sharma, C.** (2025). Retrieval-Augmented Generation: A Comprehensive Survey of Architectures, Enhancements, and Robustness Frontiers. arXiv:2506.00054.
- **Ranjan, R.** (2024). A Comprehensive Survey of Retrieval-Augmented Generation (RAG): Evolution, Current Landscape and Future Directions. arXiv:2410.12837.
- **Sarthi, P., et al.** (2024). RAPTOR: Recursive Abstractive Processing for Tree-Organized Retrieval. ICLR.
- **Gao, L., et al.** (2022). Precise Zero-Shot Dense Retrieval without Relevance Labels (HyDE). arXiv:2212.10496.
- **Robertson, S., Zaragoza, H.** (2009). The probabilistic relevance framework: BM25 and beyond. Foundations and Trends in IR.
- **Cormack, G. V., Clarke, C. L. A., Buettcher, S.** (2009). Reciprocal Rank Fusion outperforms Condorcet and individual Rank Learning Methods. SIGIR.
