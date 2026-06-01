# Comparativo de Bancos Vetoriais — 2026

Dados baseados em VectorDBBench (abr/2026), MarkTechPost (mai/2026),
CallSphere (abr/2026) e LetsDatScience (mar/2026).

> **Nota sobre custos:** os custos cloud parecem altos à primeira vista, mas
> self-hosted tem custo oculto real de infra, DevOps e manutenção. Para volumes
> pequenos (<1M vetores, <50k queries/mês), cloud gerenciado quase sempre é
> mais barato no total. Self-hosted compensa acima de 5–10M vetores em produção contínua.

---

## Sumário

1. [Cloud gerenciado](#1-cloud-gerenciado)
2. [Self-hosted (open-source)](#2-self-hosted)
3. [Comparativo de custos por cenário](#3-comparativo-de-custos-por-cenário)
4. [Hybrid search — suporte por banco](#4-hybrid-search)
5. [Guia de decisão](#5-guia-de-decisão)
6. [Integração com o BuscaAI](#6-integração-com-o-buscaai)

---

## 1. Cloud gerenciado

Bancos onde você não gerencia infra — paga pelo uso ou por capacidade reservada.

| Banco | Licença | Latência p99 | Escala máx. | Hybrid search | Filtros | Free tier | Custo produção | Melhor para |
|---|---|---|---|---|---|---|---|---|
| **Qdrant Cloud** | Apache 2.0 | 30–40ms | Bilhões | ✓ nativo v1.9+ | ✓ Filtered HNSW | 1 GB grátis | ~$50–300/mês | Melhor custo cloud, migração do self-hosted |
| **Pinecone** | Proprietária | 50–100ms | Bilhões | ✓ sparse vectors | ⚠ lento | 2 GB grátis | ~$50–5.000+/mês | Zero ops, escala automática |
| **Weaviate Cloud** | BSD-3 | 50–70ms | Bilhões | ✓ BM25+dense nativo | ✓ médio | Sandbox 14 dias | ~$25–3.000/mês | Hybrid search nativo forte |
| **Zilliz Cloud** (Milvus) | Apache 2.0 | 40–60ms | 100B+ | ✓ Sparse-BM25 v2.5 | ⚠ lento | Free tier | ~$800–5.000+/mês | Escala massiva gerenciada |
| **AWS OpenSearch Service** | Apache 2.0 | 10–50ms | Bilhões | ✓ BM25+kNN nativo | ✓ rich queries | AWS Free Tier | ~$70–2.000+/mês | AWS nativo, Apache 2.0, lexical + vetorial unificado |
| **MongoDB Atlas Vector** | SSPL | 50–120ms | Milhões | ⚠ parcial | ✓ rich queries | Free tier | ~$50–500+/mês | Já usa MongoDB |
| **Supabase pgvector** | PostgreSQL | 30–50ms | 50M+ | ⚠ incipiente | ✓ SQL nativo | Free tier | ~$25–500/mês | Postgres gerenciado, ACID |

### Custos cloud detalhados (maio 2026)

```
BANCO                 100k vetores    1M vetores      10M vetores     100M vetores
──────────────────────────────────────────────────────────────────────────────────
Qdrant Cloud          grátis (1GB)    ~$50/mês        ~$150–300/mês   ~$800+/mês
Pinecone              grátis (2GB)    ~$50–150/mês    ~$500–800/mês   ~$3.000–5.000+/mês
Weaviate Cloud        sandbox grátis  ~$100/mês       ~$300–500/mês   ~$1.000–3.000/mês
Zilliz Cloud          free tier       ~$100/mês       ~$800–1.500/mês ~$3.000+/mês
AWS OpenSearch Svc    AWS free tier   ~$70–130/mês    ~$200–500/mês   ~$500–2.000+/mês
  (t3.small.search)   (limitado)
AWS OpenSearch Srv*   —               ~$350/mês min   ~$350–800/mês   ~$1.000+/mês
Supabase PG           grátis          ~$25/mês        ~$100/mês       ~$300–500/mês
──────────────────────────────────────────────────────────────────────────────────
* Serverless: mínimo fixo de 2 OCUs × $0.24/h × 730h ≈ $350/mês mesmo sem queries
```

### Quando cloud compensa

```
✓ Time sem DevOps disponível
✓ Base < 5M vetores (infra própria não justifica)
✓ POC e MVP — precisa estar online rapidamente
✓ SLA contratual obrigatório
✓ Compliance que exige ambiente gerenciado
✓ Pico de carga imprevisível (escala automática)
✓ Já está no ecossistema AWS → AWS OpenSearch Service
```

---

## 2. Self-hosted

Você baixa, instala e opera. Custo de API zero — paga só a infraestrutura.

| Banco | Licença | Linguagem | Latência p99 | Escala máx. | Hybrid search | Filtros | RAM (1M vetores 1536d) | Custo infra/mês | Melhor para |
|---|---|---|---|---|---|---|---|---|---|
| **Qdrant**  | Apache 2.0 | Rust | 30–40ms | Bilhões | ✓ nativo v1.9+ | ✓ Filtered HNSW | ~9 GB | ~$30–80/mês | Padrão BuscaAI — melhor geral |
| **Weaviate** | BSD-3 | Go | 50–70ms | Bilhões | ✓ BM25+dense nativo | ✓ médio | ~10 GB | ~$50–150/mês | Hybrid search nativo, multi-tenant |
| **OpenSearch** | Apache 2.0 | Java/Lucene | 10–50ms | Bilhões | ✓ BM25+kNN nativo | ✓ rich queries | 2–4 GB (JVM) + índice | ~$50–150/mês | Apache 2.0, unifica lexical + vetorial, AWS |
| **Milvus** | Apache 2.0 | Go/C++ | 40–60ms | 100B+ | ✓ Sparse-BM25 v2.5 | ⚠ lento | ~8 GB | ~$200–600/mês | Escala massiva, GPU support |
| **pgvector** | PostgreSQL | C | 30–50ms | 50M+ (pgvectorscale) | ⚠ v0.9 sparse | ✓ SQL nativo | ~12 GB | $0 extra | Já tem Postgres, ACID obrigatório |
| **Chroma** | Apache 2.0 | Python | 100–200ms | ~100M | ✗ não nativo | ⚠ básico | ~5 GB | ~$5–25/mês | POC, dev local, embedded mode |
| **LanceDB** | Apache 2.0 | Rust | 40–80ms | Grande | ✓ nativo | ✓ médio | disk-based (~2 GB RAM) | ~$10–40/mês | Pouca RAM, data lake, multimodal |
| **Faiss** | MIT | C++ | <10ms | Bilhões (GPU) | ✗ | ✗ | custom | $0 (só hardware) | Pesquisa, batch GPU, pipeline custom |

### OpenSearch como banco vetorial — o diferencial

OpenSearch é o único banco nesta lista que unifica **busca lexical (BM25)** e
**busca vetorial (kNN/HNSW)** em um único serviço maduro. Para o BuscaAI isso
significa poder eliminar o Qdrant **e** o índice BM25 próprio, rodando tudo em
uma única engine:

```
Sem OpenSearch (stack padrão BuscaAI):
  Qdrant         → vetores densos + esparsos
  esparsos       → pré-filtragem 
  Redis          → fila + cache

Com OpenSearch (stack alternativa):
  OpenSearch     → vetores + BM25 + hybrid search (tudo em um)
  Redis          → fila + cache

Vantagem: menos um serviço para operar
Desvantagem: JVM (2–4 GB RAM mínimo), Qdrant tem Filtered HNSW mais maduro
```

**Neural sparse retrieval (ELSER equivalente):**
OpenSearch 3.x adicionou suporte a sparse neural retrieval nativo —
similar ao ELSER do Elasticsearch, permite embedding esparso sem GPU externa.

**Quando escolher OpenSearch como banco vetorial:**
- Empresa já tem OpenSearch rodando para logs/observabilidade
- Apache 2.0 obrigatório (sem SSPL/AGPL)
- Quer unificar lexical + vetorial em um serviço só
- Infraestrutura AWS (integra com IAM, CloudWatch, etc.)
- Volume acima de 10M vetores com equipe DevOps disponível


### Quando self-hosted compensa

```
✓ Base > 5M vetores em produção contínua
✓ Regulação exige dados on-premise
✓ Time com DevOps disponível
✓ Custo cloud ficaria > $200/mês
✓ Customização além do que APIs permitem
✓ Privacidade total dos dados (saúde, jurídico)
```

---

## 3. Comparativo de custos por cenário

### Cenário A — 100k vetores, POC

```
Cloud:
  Qdrant Cloud     → grátis (free tier 1GB)
  Pinecone         → grátis (free tier 2GB)
  Supabase PG      → grátis

Self-hosted:
  Chroma embedded  → $0 (roda no processo)
  Qdrant Docker    → $0 (dev local)

Veredicto: tanto faz, use cloud — sem custo e sem setup
```

### Cenário B — 1M vetores, produção pequena

```
Cloud:
  Supabase PG          → ~$25/mês      ← mais barato cloud
  Qdrant Cloud         → ~$50/mês
  Pinecone             → ~$50–150/mês
  AWS OpenSearch Svc   → ~$70–130/mês
  Weaviate Cloud       → ~$100/mês

Self-hosted:
  pgvector             →  mais barato
  Qdrant Docker        → ~$30/mês (Hetzner pequeno)
  OpenSearch           → ~$50–80/mês (single node 16GB)

Veredicto: pgvector se já tem Postgres. Qdrant self-hosted se não.
           OpenSearch vale se vai unificar lexical + vetorial.
```

### Cenário C — 10M vetores, produção média

```
Cloud:
  Qdrant Cloud         → ~$150–300/mês
  AWS OpenSearch Svc   → ~$200–500/mês
  Weaviate Cloud       → ~$300–500/mês
  Pinecone             → ~$500–800/mês  ← começa a ficar caro

Self-hosted:
  pgvectorscale        → ~$50/mês (servidor dedicado)   ← mais barato
  Qdrant               → ~$80/mês (servidor 32GB RAM)
  OpenSearch           → ~$80–150/mês (single node 32GB)
  LanceDB              → ~$30/mês (disk-based, menos RAM)

Veredicto: self-hosted claramente mais barato. Qdrant ou pgvectorscale.
           OpenSearch se precisar unificar com busca lexical.
```

### Cenário D — 100M vetores, escala grande

```
Cloud:
  Qdrant Cloud         → ~$800+/mês
  AWS OpenSearch Svc   → ~$500–2.000/mês
  Weaviate Cloud       → ~$1.000–3.000/mês
  Pinecone             → ~$3.000–5.000+/mês   ← muito caro

Self-hosted:
  pgvectorscale        → ~$200–400/mês
  Qdrant cluster       → ~$400–600/mês (3 nós)
  OpenSearch cluster   → ~$200–400/mês (3 nós, ampla adoção)
  Milvus cluster       → ~$600–1.000/mês

Veredicto: self-hosted obrigatório. Pinecone inviável.
           OpenSearch cluster é competitivo em escala grande.
```

---

## 4. Hybrid Search

```
BANCO                  CLOUD                    SELF-HOSTED
────────────────────────────────────────────────────────────────────
Qdrant                 ✓ nativo v1.9+           ✓ nativo v1.9+
Weaviate               ✓ nativo                 ✓ nativo
Milvus / Zilliz        ✓ nativo v2.5            ✓ nativo v2.5
OpenSearch             ✓ BM25+kNN nativo        ✓ BM25+kNN nativo
                         + sparse neural 3.x      + sparse neural 3.x
LanceDB                —                        ✓ nativo
Pinecone               ✓ sparse vectors         ✗ sem self-hosted
pgvector               ⚠ incipiente v0.9        ⚠ incipiente v0.9
Chroma                 ⚠ parcial                ✗ não nativo
MongoDB Atlas          ⚠ parcial                ⚠ limitado
Faiss                  —                        ✗ não suporta
────────────────────────────────────────────────────────────────────

Nota OpenSearch: hybrid search via Reciprocal Score Fusion (RSF) nativo.
Combina BM25 e kNN em uma única query — não precisa de RRF externo.
```

---

## 5. Guia de decisão

```
JÁ USA POSTGRES?
  → pgvector self-hosted ($0 extra) ou Supabase (cloud, ~$25/mês)

QUER ZERO OPS, ACEITA PAGAR MAIS?
  → Pinecone (managed líder) ou Qdrant Cloud (melhor custo cloud)

MELHOR CUSTO-BENEFÍCIO GERAL?
  → Qdrant self-hosted (~$30–80/mês)    ← padrão BuscaAI

HYBRID SEARCH NATIVO MAIS MADURO?
  → Weaviate (cloud ou self-hosted) ou OpenSearch

QUER UNIFICAR LEXICAL + VETORIAL EM UMA ENGINE?
  → OpenSearch self-hosted
    (elimina Qdrant + índice BM25 separado da stack)

JÁ ESTÁ NO ECOSSISTEMA AWS?
  → AWS OpenSearch Service (~$70/mês entrada, Apache 2.0)

APACHE 2.0 OBRIGATÓRIO (compliance / SaaS)?
  → OpenSearch (fork Apache 2.0 do Elasticsearch)

ESCALA > 100M VETORES?
  → Milvus self-hosted ou Pinecone cloud
    (OpenSearch cluster também é viável)

POC / DEV LOCAL?
  → Chroma embedded (zero setup)

POUCA RAM, HARDWARE MODESTO?
  → LanceDB (disk-based)

PESQUISA / BATCH GPU?
  → Faiss (biblioteca)
```

---

## 6. Integração com o BuscaAI

```python
# rag_settings.py

# Cloud — Qdrant Cloud
VECTOR_STORE = {
    "backend":    "qdrant",
    "url":        os.environ.get("QDRANT_URL"),
    "api_key":    os.environ.get("QDRANT_API_KEY"),
    "collection": "buscaai",
}

# Cloud — Pinecone
VECTOR_STORE = {
    "backend":    "pinecone",
    "index_name": "buscaai",
    "api_key":    os.environ.get("PINECONE_API_KEY"),
}

# Cloud — AWS OpenSearch Service
VECTOR_STORE = {
    "backend":   "opensearch",
    "host":      os.environ.get("OPENSEARCH_HOST"),   # endpoint AWS
    "port":      443,
    "use_ssl":   True,
    "aws_region": os.environ.get("AWS_REGION", "us-east-1"),
    "index":     "buscaai-vectors",
}

# Self-hosted — Qdrant Docker 
VECTOR_STORE = {
    "backend":    "qdrant",
    "host":       os.environ.get("QDRANT_HOST", "localhost"),
    "port":       6333,
    "collection": "buscaai",
}

# Self-hosted — OpenSearch (unifica lexical + vetorial)
VECTOR_STORE = {
    "backend": "opensearch",
    "host":    os.environ.get("OPENSEARCH_HOST", "localhost"),
    "port":    9200,
    "index":   "buscaai-vectors",
}

# Com OpenSearch, pré-filtragem usa a mesma engine:
PRE_FILTERING = {
    "enabled":  True,
    "strategy": "opensearch",   # mesma instância do VECTOR_STORE
    "host":     os.environ.get("OPENSEARCH_HOST", "localhost"),
    "port":     9200,
    "top_n":    50000,
}

# Self-hosted — pgvector
VECTOR_STORE = {
    "backend":  "pgvector",
    "host":     os.environ.get("PG_HOST"),
    "port":     5432,
    "database": os.environ.get("PG_DB"),
    "table":    "embeddings",
}

# Self-hosted — Chroma (POC)
VECTOR_STORE = {
    "backend": "chroma",
    "mode":    "embedded",
    "path":    "./chroma_db",
}
```

### Recomendação por fase

```
FASE           CLOUD                       SELF-HOSTED
─────────────────────────────────────────────────────────────────────
POC            Qdrant Cloud (free)         Chroma embedded
MVP            Qdrant Cloud (~$50)         Qdrant (~$30–80)
Produção       Qdrant Cloud                Qdrant ← padrão BuscaAI
Já tem PG      Supabase (~$25)             pgvector ($0 extra)
AWS nativo     AWS OpenSearch (~$70+)      OpenSearch self-hosted
Unifica stack  AWS OpenSearch              OpenSearch self-hosted
               (lexical + vetorial)        (elimina índice BM25 separado)
Enterprise     Pinecone / Qdrant Cloud     Qdrant cluster
Escala 100M+   Pinecone (caro)             Milvus ou OpenSearch cluster
─────────────────────────────────────────────────────────────────────
```

---

## Fontes

- VectorDBBench — benchmarks abr/2026
- MarkTechPost: "Best Vector Databases in 2026" (mai/2026)
- CallSphere: "Vector Database Benchmarks 2026" (abr/2026)
- LetsDatScience: "Vector Databases Compared" (mar/2026)
- DigitalApplied: "Vector Databases for AI Agents 2026" (abr/2026)
- OpenSearch Documentation: "k-NN Search" + "Hybrid Search" (mai/2026)
- AWS: "Amazon OpenSearch Service pricing" (mai/2026)
