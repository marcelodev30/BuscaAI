# BM25 vs SPLADE — Busca Lexical Clássica vs Neural

Os dois métodos de busca lexical do BuscaAI, lado a lado.
Ambos produzem **vetores esparsos** (a maioria dos pesos é zero) e usam
**índice invertido** — mas de formas fundamentalmente diferentes.

> **Contexto no BuscaAI:** a busca lexical é o componente que captura
> termos exatos (IDs, códigos, nomes próprios) que a busca neural densa
> costuma perder. As duas opções de banco do BuscaAI usam abordagens
> diferentes: **OpenSearch usa BM25**, **Qdrant usa SPLADE** (vetor esparso).

---

## Sumário

1. [O que cada um é](#1-o-que-cada-um-é)
2. [A diferença fundamental](#2-a-diferença-fundamental)
3. [Tabela comparativa completa](#3-tabela-comparativa-completa)
4. [Exemplos lado a lado](#4-exemplos-lado-a-lado)
5. [Onde cada um falha](#5-onde-cada-um-falha)
6. [Custo e performance](#6-custo-e-performance)
7. [Qual escolher](#7-qual-escolher)
8. [No BuscaAI](#8-no-buscaai)

---

## 1. O que cada um é

### BM25 (Best Match 25)

Algoritmo estatístico de ranking criado nos anos 1990. Evolução do TF-IDF.
Pontua documentos com base em três fatores:

```
1. TF  (Term Frequency)    — quantas vezes o termo aparece no documento
2. IDF (Inverse Doc Freq)  — quão raro o termo é na coleção
3. Normalização           — penaliza documentos muito longos
```

BM25 é **puro casamento de strings com peso de frequência**. Não entende
significado nenhum. Se a query diz "carro" e o documento diz "veículo",
o BM25 não faz a conexão.

### SPLADE (Sparse Lexical and Expansion)

Modelo neural baseado em transformer (BERT) criado em 2021 (Formal et al.).
Mantém a estrutura esparsa e o índice invertido do BM25, mas com pesos
**aprendidos** e capacidade de **expandir termos**.

SPLADE passa o texto por uma cabeça de Masked Language Model (MLM),
aplica max pooling e log saturation, e produz um vetor esparso sobre o
vocabulário (30.000+ dimensões, uma por token do vocabulário).

```
A pergunta que o SPLADE responde:
"Dá pra manter a esparsidade e a interpretabilidade do BM25,
 mas ensinar o modelo sobre semântica?"

A resposta é: sim, e funciona muito bem.
```

---

## 2. A diferença fundamental

A diferença está na **expansão de termos**.

```
QUERY: "carro"

BM25 indexa:
  carro: peso alto
  (e mais nada — só a palavra exata)

SPLADE indexa:
  carro:      0.94
  veículo:    0.71   ← expansão aprendida
  automóvel:  0.68   ← expansão aprendida
  automotivo: 0.52   ← expansão aprendida
```

O SPLADE aprendeu que esses termos coocorrem em contextos relevantes.
Quando testado na frase "o carro é azul", o modelo reduz o peso de "o" e "é"
e expande "carro" para termos relacionados como "veículo" e "automóvel" —
algo que o BM25 não consegue fazer, e que os modelos densos fazem de forma
implícita em vez de explícita.

### Por que isso importa

```
Documento: "extinção do contrato de trabalho"
Query:     "rescisão de vínculo empregatício"

BM25:    não encontra (nenhuma palavra em comum)
SPLADE:  encontra (expande "rescisão"→"extinção", "vínculo"→"contrato")
```

---

## 3. Tabela comparativa completa

| Critério | BM25 | SPLADE |
|---|---|---|
| **Tipo** | Estatístico | Neural (transformer/BERT) |
| **Ano** | ~1994 | 2021 |
| **Expansão de termos** | ❌ não | ✅ sim (aprendida) |
| **Entende sinônimos** | ❌ não | ✅ parcialmente |
| **Pesos** | calculados (TF-IDF) | aprendidos (MLM) |
| **Estrutura** | vetor esparso | vetor esparso |
| **Índice** | invertido | invertido |
| **Dimensões** | tamanho do vocabulário | 30.000+ (vocabulário BERT) |
| **Precisa de GPU** | ❌ não | ⚠️ ideal na ingestão |
| **Precisa de modelo** | ❌ não | ✅ sim (SPLADE model) |
| **Custo de indexação** | mínimo | maior (inferência do modelo) |
| **Custo de query** | mínimo | baixo-médio |
| **Latência** | mais rápida | um pouco mais lenta |
| **Termos exatos (IDs, códigos)** | ✅ excelente | ✅ bom |
| **Vocabulary mismatch** | ❌ falha | ✅ resolve parcialmente |
| **Generalização cross-domain** | ✅ robusto | ⚠️ depende do treino |
| **Interpretabilidade** | ✅ total | ✅ alta (vê os termos) |
| **Configuração** | zero (k1, b padrão) | requer rodar o modelo |
| **Qualidade (queries complexas)** | boa | superior |
| **FLOPS (custo computacional)** | ~0.13 | ~0.73 (com regularização) |
| **Engine no BuscaAI** | OpenSearch | Qdrant |

---

## 4. Exemplos lado a lado

### Exemplo 1 — termo técnico raro (BM25 vence)

```
QUERY: "ERR_CONN_RESET_4XX retry semantics"

BM25:
  "ERR_CONN_RESET_4XX" tem IDF altíssimo (aparece em quase nenhum doc)
  → retorna a seção exata como resultado #1
  ✅ resolve instantaneamente

Busca densa:
  → ranqueia documentos semanticamente próximos
  → a seção correta fica em 11º lugar
  ❌ falha em priorizar

SPLADE:
  → também captura o termo raro com peso alto
  ✅ resolve
```

### Exemplo 2 — vocabulary mismatch (SPLADE vence)

```
QUERY: "car reliability"
DOC:   "vehicle dependability"

BM25:
  nenhuma palavra em comum
  ❌ não encontra

SPLADE:
  expande "car"→"vehicle", "reliability"→"dependability"
  ✅ encontra
```

### Exemplo 3 — query conceitual (ambos falham, densa vence)

```
QUERY: "o que acontece quando o gateway não alcança o upstream"
DOC:   "indisponibilidade de upstream e padrões de circuit breaker"

BM25:    ❌ sem overlap de keywords
SPLADE:  ⚠️ expansão limitada ajuda pouco
Densa:   ✅ encontra pelo significado
```

Este exemplo mostra por que a **busca híbrida** (lexical + densa) existe:
cada método cobre a fraqueza do outro.

---

## 5. Onde cada um falha

### BM25 falha em

```
✗ Sinônimos:        "carro" não acha "veículo"
✗ Paráfrases:       "como cancelar" não acha "procedimento de rescisão"
✗ Significado:      é cego a semântica, puro string matching
✗ Multilíngue:      query em PT não acha doc em EN
```

### SPLADE falha em

```
✗ Generalização:    treinado em MS MARCO, pode piorar em domínios muito
                    diferentes do treino (jurídico BR, medicina especializada)
✗ Custo:            inferência do modelo na ingestão (precisa de GPU ideal)
✗ Dependência:      requer carregar e rodar o modelo SPLADE
✗ Termos novos:     palavras que não estavam no vocabulário do treino
```

### Por que o híbrido resolve

```
BM25/SPLADE (lexical)  →  pega termos exatos, IDs, códigos
        +
embedding denso        →  pega significado, conceitos, paráfrases
        ↓
       RRF
        ↓
melhor dos dois mundos
```

A literatura confirma: em documentos financeiros com terminologia
precisa (nomes de empresas, tickers, métricas padronizadas), o BM25
supera até o text-embedding-3-large em quase todas as métricas —
o que desafia a suposição de que a busca densa sempre domina.

---

## 6. Custo e performance

### Custo de indexação (1M de chunks)

```
BM25:
  CPU apenas, tokenização simples
  ~minutos, custo desprezível

SPLADE:
  inferência do modelo por chunk
  CPU: lento (~horas)
  GPU: rápido (~minutos), mas precisa da GPU
  custo: tempo de GPU ou tempo de CPU
```

### Custo de query

```
BM25:    < 5ms — lookup no índice invertido
SPLADE:  10–30ms — inferência da query + lookup
```

### FLOPS (custo computacional relativo)

```
BM25:                    ~0.13  (baseline)
SPLADE (regularizado):   ~0.73
SPLADE (sem regular.):   ~0.88
SparTerm:                ~2.8–4.6 (muito mais caro)
```

SPLADE com regularização FLOPS atinge qualidade similar reduzindo o
custo computacional, aproximando-se do nível do BM25.

### Performance em escala

```
Em datasets de dezenas de milhões a bilhões de documentos:
  SPLADE supera BM25 em qualidade, especialmente queries complexas
  mas tem custo computacional maior
  Expanded-SPLADE com pruning = melhor equilíbrio em escala massiva
```

---

## 7. Qual escolher

```
USE BM25 (OpenSearch) quando:
  ✓ termos técnicos, IDs, códigos, nomes próprios dominam
  ✓ não tem GPU disponível
  ✓ quer zero configuração e zero custo de modelo
  ✓ domínio muito específico (BM25 generaliza melhor)
  ✓ documentos financeiros/jurídicos com terminologia precisa
  ✓ máxima velocidade de indexação e query

USE SPLADE (Qdrant) quando:
  ✓ vocabulário variado (usuário usa palavras diferentes dos docs)
  ✓ sinônimos e paráfrases importam
  ✓ tem GPU para a ingestão (ou aceita CPU mais lento)
  ✓ qualidade em queries complexas é prioridade
  ✓ quer o meio-termo entre BM25 e busca densa

USE OS DOIS (híbrido) quando:
  ✓ na dúvida — é o padrão recomendado
  ✓ lexical (BM25 ou SPLADE) + denso + RRF cobre todas as fraquezas
```

### Resumo da decisão

```
                 BM25              SPLADE
                  │                  │
        termos exatos          significado +
        velocidade             termos exatos
        zero custo             qualidade
                  │                  │
                  └──── híbrido ─────┘
                         +
                    busca densa
                         =
                  BuscaAI padrão
```

---

## 8. No BuscaAI

As duas arquiteturas do BuscaAI usam abordagens lexicais diferentes:

```
OPÇÃO A — OpenSearch
  busca lexical = BM25 nativo (Lucene)
  ✓ zero configuração, máxima velocidade
  ✓ ótimo para termos exatos e domínios específicos

OPÇÃO B — Qdrant (padrão)
  busca lexical = vetor esparso SPLADE
  ✓ expansão de termos, melhor para vocabulário variado
  ✓ qualidade superior em queries complexas
```

### Configuração

```python
# OPÇÃO A — OpenSearch com BM25
VECTOR_STORE = {
    "backend": "opensearch",
    "host":    "localhost",
    "port":    9200,
    "index":   "buscaai",
}
EMBEDDINGS = {
    "dense": {"provider": "openai", "model": "text-embedding-3-small"},
    # lexical = BM25 nativo do OpenSearch, sem config extra
}

# OPÇÃO B — Qdrant com SPLADE
VECTOR_STORE = {
    "backend":    "qdrant",
    "collection": "buscaai",
}
EMBEDDINGS = {
    "dense":  {"provider": "openai", "model": "text-embedding-3-small"},
    "sparse": {"model": "splade"},   # SPLADE faz o papel lexical
}

# Em ambos: a busca híbrida combina lexical + denso
RETRIEVAL = {
    "strategy": "hybrid",   # lexical (BM25/SPLADE) + denso + fusão
    "top_k":    50,
    "rrf_k":    60,
}
```

### Recomendação

```
Caso geral                  → Qdrant + SPLADE (padrão)
Termos técnicos/IDs/AWS      → OpenSearch + BM25
Sem GPU + domínio específico → OpenSearch + BM25
Vocabulário variado          → Qdrant + SPLADE
Na dúvida                    → qualquer um dos dois com hybrid=True
```

---

## Fontes

- Formal et al. (2021) — "SPLADE: Sparse Lexical and Expansion Model"
- Robertson & Zaragoza (2009) — "The Probabilistic Relevance Framework: BM25"
- Won et al. (2025) — "Efficiency and Effectiveness of SPLADE Models on Billion-Scale" (NAVER, arXiv:2511.22263)
- Qdrant — "Modern Sparse Neural Retrieval: From Theory to Practice" (2024)
- Qdrant — "Fine-Tuning Sparse Embeddings for E-Commerce Search" (2026)
- BigData Boutique — "Sparse vs Dense Vectors" (mar/2026)
- "The Past and Present of Sparse Retrieval" — HuggingFace blog (out/2025)
- "From BM25 to Corrective RAG: Benchmarking Retrieval Strategies" (arXiv, abr/2026)
