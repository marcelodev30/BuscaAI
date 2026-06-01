# Comparativo de Engines de Pré-Filtragem Léxica — 2026

O pré-filtro léxico é a primeira etapa do pipeline de retrieval no BuscaAI.
Antes de ir ao banco vetorial, a engine de busca lexical reduz o universo
de chunks de milhões para dezenas de milhares, usando BM25 ou variantes.

Dados baseados em OSSAlt (mar/2026), BigData Boutique (mai/2026),
AskAnTech (abr/2026) e Meilisearch Blog (dez/2025).

---

## Por que pré-filtragem importa

```
SEM PRÉ-FILTRO:
  query → busca vetorial em 10M chunks → top-50 → reranker → LLM
  Custo: HNSW percorre grafo inteiro → lento em bases grandes

COM PRÉ-FILTRO:
  query → BM25 filtra 10M → 50k candidatos relevantes
         → busca vetorial nos 50k → top-50 → reranker → LLM
  Custo: HNSW opera em 50k em vez de 10M → 10–100x mais rápido

Ganho típico de latência: 60–80% em bases acima de 5M chunks
```

---

## Sumário

1. [Self-hosted (open-source)](#1-self-hosted)
2. [Cloud gerenciado](#2-cloud-gerenciado)
3. [Funcionalidades comparadas](#4-funcionalidades-comparadas)
4. [Guia de decisão](#5-guia-de-decisão)
5. [Integração com o BuscaAI](#6-integração-com-o-buscaai)

---

## 1. Self-hosted

Custo de API zero — você instala e opera. Paga só a infraestrutura.

| Engine | Licença | Linguagem | Latência busca | RAM mínima | Escala máx. | BM25 | Vetorial | Multilíngue | Setup | Custo infra/mês |
|---|---|---|---|---|---|---|---|---|---|---|
| **Meilisearch** | SSPL | Rust | 5–30ms | 200–500MB | ~50M docs | ✓ nativo | ✓ desde 2024 | ✓ 50+ idiomas | Fácil | ~$5–25/mês |
| **Typesense** | GPL 3.0 | C++ | 1–10ms | 300–600MB | ~100M docs | ✓ nativo | ✓ nativo | ✓ 30+ idiomas | Fácil | ~$10–30/mês |
| **OpenSearch** | Apache 2.0 | Java/Lucene | 10–50ms | 2–4 GB (JVM) | Bilhões | ✓ Lucene | ✓ kNN/HNSW | ✓ 30+ idiomas | Complexo | ~$50–150/mês |
| **Elasticsearch** | SSPL/AGPL | Java/Lucene | 10–50ms | 2–4 GB (JVM) | Petabytes | ✓ Lucene | ✓ kNN + BBQ | ✓ 30+ idiomas | Complexo | ~$50–150/mês |
| **Apache Solr** | Apache 2.0 | Java/Lucene | 15–60ms | 2–4 GB (JVM) | Bilhões | ✓ Lucene | ⚠ básico | ✓ 30+ idiomas | Complexo | ~$50–150/mês |

### Detalhes self-hosted

---

#### Meilisearch — leve e simples

**O que é:**
Engine de busca escrita em Rust. Focada em simplicidade e velocidade para
search-as-you-type. SSPL (source-available, não Apache 2.0 puro — verifique
se há restrição para seu caso de uso).

**Arquitetura:**
- Processo único, sem JVM
- 200–500 MB de RAM para bases médias
- FST (Finite State Transducer) para lookup ultrarrápido
- LMDB como storage persistente eficiente

**Funcionalidades relevantes para RAG:**
- BM25 nativo com ranking customizável
- Vector search desde 2024 (kNN)
- Typo tolerance automática
- Faceted search
- 50+ idiomas incluindo PT-BR
- API REST simples, SDKs em todas as linguagens

**Pontos fortes:**
- Setup em minutos: `docker run meilisearch/meilisearch`
- Mais leve que Elasticsearch (5–10x menos RAM)
- Latência sub-30ms consistente
- Documentação excelente

**Pontos fracos:**
- SSPL — comercialmente restrito para alguns casos
- Sem clustering open-source (só no cloud pago)
- Vector search ainda menos maduro que Qdrant
- Aggregações limitadas comparado ao Elasticsearch

**Quando usar:** hardware fraco, POC rápido, base até 50M docs, time pequeno.

---

#### Typesense — máximo QPS

**O que é:**
Engine de busca escrita em C++. Mais rápida em latência pura e throughput alto
entre as opções leves. Destaque em typo tolerance e busca de produto.

**Funcionalidades relevantes para RAG:**
- BM25 com tie-breaking algorithm
- Vector search nativo
- Typo tolerance built-in
- Configuração por query-time (flexibilidade alta)
- Faceted search com contagem exata ou estimada

**Pontos fortes:**
- 1–10ms de latência — mais rápido da categoria
- Typo tolerance nativo e configurável
- Schema flexível com configuração em query-time
- GPL open-source com licença comercial disponível

**Pontos fracos:**
- GPL 3.0 — requer avaliação jurídica para uso comercial
- Menos maduro que Elasticsearch em analytics
- Comunidade menor

**Quando usar:** e-commerce, busca de produto, latência < 10ms obrigatória.

---

#### OpenSearch — Apache 2.0 puro

**O que é:**
Fork do Elasticsearch feito pela AWS em 2021 após mudança de licença.
Apache 2.0 verdadeiro, mantido pela Linux Foundation com contribuições
de AWS, SAP e outras empresas.

**Funcionalidades relevantes para RAG:**
- Lucene BM25 nativo e maduro
- k-NN com HNSW, FAISS e NMSLIB
- Hybrid search com Reciprocal Rank Fusion
- Neural sparse retrieval (OpenSearch 3.x)
- Agentic AI flows (OpenSearch 3.2)
- Multi-modal embedding support (OpenSearch 3.2)

**Pontos fortes:**
- Apache 2.0 sem amarras — ideal para compliance e SaaS
- Escala Lucene — bilhões de documentos comprovados
- Security built-in (o que no Elasticsearch é pago)
- Compatibilidade com a maioria dos clientes Elasticsearch

**Pontos fracos:**
- JVM — 2–4 GB de RAM mínimo, GC pauses ocasionais
- Setup complexo (configurar cluster, shards, replicas)
- Algumas otimizações recentes do Elasticsearch não chegaram ainda

**Quando usar:** Apache 2.0 obrigatório, base > 10M docs, infraestrutura AWS.

---

#### Elasticsearch — mais maduro e completo

**O que é:**
Veterano de 2010. Motor de busca mais usado do mundo, construído sobre Lucene.
Licença SSPL desde 2021 (com opção AGPL). O mais poderoso da categoria.

**Funcionalidades relevantes para RAG:**
- Lucene BM25 — décadas de otimização
- ELSER (Elastic Learned Sparse EncodeR) — sparse retrieval neural built-in sem GPU
- kNN com HNSW + BBQ (Better Binary Quantization) — 16x menos memória
- DiskBBQ (ES 9.2) — vetores em disco para bases muito grandes
- GPU acceleration via NVIDIA cuVS (tech preview 9.3)
- Elasticsearch Relevance Engine (ESRE) para RAG completo

**ELSER em detalhes:**
```
ELSER é um modelo de retrieval esparso que já vem embutido no cluster.
Sem GPU externa necessária.
Supera BM25 puro em 10–20% de recall em benchmarks.
Funciona como substituto mais inteligente do BM25 dentro do ES.
```

**Pontos fortes:**
- Mais maduro e completo da categoria (15+ anos)
- ELSER supera BM25 sem dependência externa
- BBQ reduz memória vetorial em 16x com <1% perda de recall
- Analytics complexas (aggregations, dashboards, alertas)
- Ecossistema Kibana para monitoramento

**Pontos fracos:**
- SSPL/AGPL — verificar compatibilidade com seu projeto
- JVM pesado (2–4 GB mínimo)
- Complexidade operacional alta
- Mais caro que alternativas em cloud

**Quando usar:** empresa já tem ES rodando, analytics + busca na mesma stack,
ELSER para sparse retrieval sem GPU.

---

#### Apache Solr — veterano enterprise

**O que é:**
Motor de busca Apache desde 2004. 20+ anos de uso em empresas como Netflix,
Apple e Bloomberg. Apache 2.0 puro, robusto, mas com curva de aprendizado alta.

**Quando usar:** legado corporativo com Solr existente, Apache 2.0 obrigatório,
casos onde OpenSearch/Elasticsearch são grandes demais.

---

## 2. Cloud gerenciado

Serviços gerenciados — sem ops, você paga pelo uso ou por capacidade.

| Serviço | Base | Licença | Latência | Escala | BM25 | Vetorial | Free tier | Custo entrada | Custo produção |
|---|---|---|---|---|---|---|---|---|---|
| **Meilisearch Cloud** | Meilisearch | SSPL | 5–30ms | ~50M docs | ✓ | ✓ | 14 dias trial | $30/mês | $30–300/mês |
| **Typesense Cloud** | Typesense | GPL/Comercial | 1–10ms | ~100M docs | ✓ | ✓ | ✗ | ~$30/mês | $30–500/mês |
| **AWS OpenSearch Service** | OpenSearch | Apache 2.0 | 10–50ms | Bilhões | ✓ | ✓ | AWS Free Tier | ~$70/mês | $200–2.000+/mês |
| **AWS OpenSearch Serverless** | OpenSearch | Apache 2.0 | 10–50ms | Bilhões | ✓ | ✓ | ✗ | ~$350/mês* | $350–2.000+/mês |
| **Elastic Cloud (Standard)** | Elasticsearch | SSPL/AGPL | 10–50ms | Petabytes | ✓ | ✓ BBQ | 14 dias trial | ~$95/mês | $200–5.000+/mês |
| **Algolia** | Proprietário | Proprietária | <50ms | Bilhões | ✓ | ✓ NeuralSearch | 10k req/mês | ~$50/mês | $50–5.000+/mês |



### Quando cloud compensa

```
✓ Time sem DevOps disponível
✓ Base < 10M docs e orçamento para $30–100/mês
✓ SLA contratual obrigatório
✓ Pico de carga imprevisível (AWS Serverless)
✓ Já está no ecossistema AWS (OpenSearch Service)
```

---



## 3. Funcionalidades comparadas

```
FUNCIONALIDADE          ÍNDICE    MEILI   TYPESENSE  OPENSEARCH  ELASTIC
                        PRÓPRIO
────────────────────────────────────────────────────────────────────────
BM25 nativo             ✓         ✓       ✓          ✓           ✓
Busca vetorial          ✗         ✓       ✓          ✓           ✓
Hybrid search (BM25+    ✗         ✓       ✓          ✓           ✓
  vetorial)
Typo tolerance          ✗         ✓ auto  ✓ auto     ✓ config    ✓ config
Clustering nativo       ✗         ✗ OSS   ✗ OSS      ✓           ✓
Analytics/aggregações   ✗         ⚠ básico ⚠ básico  ✓           ✓
Sparse neural (ELSER)   ✗         ✗       ✗          ✓ parcial   ✓ nativo
Multi-idiomas (PT-BR)   ⚠         ✓       ✓          ✓           ✓
Setup < 5 minutos       ✓         ✓       ✓          ✗           ✗
RAM mínima < 500MB      ✓         ✓       ✓          ✗           ✗
Apache 2.0 puro         ✓         ✗ SSPL  ✗ GPL      ✓           ✗ SSPL
────────────────────────────────────────────────────────────────────────
```

---

## 4. Guia de decisão

```
HARDWARE FRACO OU POC RÁPIDO:
  → Meilisearch Docker (~200MB RAM, setup 5 min)

MÁXIMO QPS, TYPO TOLERANCE, E-COMMERCE:
  → Typesense (1–10ms, C++, typo tolerance nativo)

APACHE 2.0 OBRIGATÓRIO, BASE > 10M:
  → OpenSearch self-hosted (fork livre do Elasticsearch)

EMPRESA JÁ TEM ELASTICSEARCH RODANDO:
  → Elasticsearch + ELSER (sparse retrieval sem GPU)

ANALYTICS + BUSCA NA MESMA STACK:
  → Elasticsearch ou OpenSearch

CLOUD ZERO OPS, AWS:
  → AWS OpenSearch Service (~$70/mês entrada)
  ⚠ Evite Serverless se volume for previsível ($350/mês mínimo)

CLOUD SIMPLES E BARATO:
  → Meilisearch Cloud ($30/mês) ou Typesense Cloud (~$30/mês)

CHECKLIST:
  □ Base < 10M chunks?          → índice próprio BuscaAI
  □ RAM < 500MB disponível?     → Meilisearch
  □ Apache 2.0 obrigatório?     → OpenSearch ou Solr
  □ Analytics necessário?       → Elasticsearch ou OpenSearch
  □ Zero ops, AWS?              → AWS OpenSearch Service
  □ E-commerce, typo tolerance? → Typesense
  □ Dados on-premise?           → qualquer self-hosted
  □ POC rápido?                 → Meilisearch Docker
  □ ELSER sem GPU?              → Elasticsearch
```

---

## 5. Integração com o BuscaAI

O BuscaAI configura a engine de pré-filtragem via `rag_settings.py`:

```python
# rag_settings.py


# SELF-HOSTED — Meilisearch (hardware fraco, POC)
PRE_FILTERING = {
    "enabled":  True,
    "strategy": "meilisearch",
    "host":     os.environ.get("MEILI_HOST", "localhost"),
    "port":     7700,
    "api_key":  os.environ.get("MEILI_API_KEY"),
    "index":    "buscaai",
    "top_n":    50000,
}

# SELF-HOSTED — OpenSearch (escala grande, Apache 2.0)
PRE_FILTERING = {
    "enabled":  True,
    "strategy": "opensearch",
    "host":     os.environ.get("OPENSEARCH_HOST", "localhost"),
    "port":     9200,
    "index":    "buscaai_lexical",
    "top_n":    50000,
}

# SELF-HOSTED — Elasticsearch (empresa já usa)
PRE_FILTERING = {
    "enabled":  True,
    "strategy": "elasticsearch",
    "host":     os.environ.get("ELASTIC_HOST", "localhost"),
    "port":     9200,
    "index":    "buscaai_lexical",
    "top_n":    50000,
    "use_elser": False,   # True para usar ELSER em vez de BM25 puro
}

# CLOUD — Meilisearch Cloud
PRE_FILTERING = {
    "enabled":  True,
    "strategy": "meilisearch",
    "host":     os.environ.get("MEILI_CLOUD_URL"),
    "api_key":  os.environ.get("MEILI_API_KEY"),
    "top_n":    50000,
}
```

### Recomendação por fase do projeto

```
FASE              SELF-HOSTED                     CLOUD
──────────────────────────────────────────────────────────────────
POC               Índice próprio BuscaAI ($0)     —
Dev local         Meilisearch Docker ($0)          —
MVP < 10M         Índice próprio ($0)              Meilisearch Cloud ($30)
MVP 10–50M        Meilisearch (~$25/mês)           Meilisearch Cloud ($30–100)
Produção          Meilisearch ou OpenSearch        AWS OpenSearch (~$70–200)
Escala 100M+      OpenSearch/ES cluster            AWS OpenSearch ($500+)
Empresa tem ES    Elasticsearch existente          Elastic Cloud ($200+)
──────────────────────────────────────────────────────────────────
```

---

## Fontes

- OSSAlt: "Meilisearch vs Typesense vs Elasticsearch 2026" (mar/2026)
- BigData Boutique: "OpenSearch vs Elasticsearch Compared" (mai/2026)
- AskAnTech: "Elasticsearch vs OpenSearch vs Typesense 2026" (abr/2026)
- Meilisearch Blog: "Elasticsearch Pricing" (dez/2025)
- BigData Boutique: "OpenSearch and Elasticsearch Pricing Guide" (mai/2026)
