# Custos do Sistema — APIs Cloud vs Self-Hosted

Este documento reúne os preços de mercado de cada componente do pipeline RAG, comparando opções **cloud (pay-per-use)** com opções **self-hosted (rodar localmente)**, atualizados em **maio de 2026**.

O objetivo é dar ao desenvolvedor visibilidade real sobre o custo de operar o BuscaAI, em vez de só listar provedores sem indicar quanto cada um cobra.

> **Observação:** preços de APIs de IA têm caído rapidamente (cerca de 80% entre 2025 e 2026). Os valores aqui são referências de **maio/2026**. Sempre confira a página oficial de pricing antes de fechar uma estimativa.

---

## Sumário

1. [Embeddings — denso e esparso](#1-embeddings)
2. [LLMs — geração de resposta](#2-llms-geração-de-resposta)
3. [Reranking](#3-reranking)
4. [Banco vetorial](#4-banco-vetorial)
5. [Infraestrutura de suporte](#5-infraestrutura-de-suporte)
6. [Cenários completos — estimativas mensais](#6-cenários-completos)
7. [Como reduzir custos no BuscaAI](#7-como-reduzir-custos)

---

## 1. Embeddings

### Modelos cloud (API)

| Provedor | Modelo | Preço por 1M tokens | Dimensões | Observação |
|---|---|---|---|---|
| **OpenAI** | text-embedding-3-small | $0.02 | 1536 | Excelente custo-benefício, padrão de mercado |
| **OpenAI** | text-embedding-3-large | $0.13 | 3072 | Mais qualidade, 6.5x mais caro |
| **Voyage AI** | voyage-4-lite | $0.02 | 1024 | Mesmo preço do OpenAI small, contexto 32K |
| **Voyage AI** | voyage-4-large | $0.12 | 2048 | Melhor para retrieval em benchmarks |
| **Cohere** | Embed v3 (English/Multilingual) | $0.10 | 1024 | Multilingual cobre 100+ idiomas |
| **Cohere** | Embed v4 (multimodal) | $0.12 (texto) / $0.47 (imagem) | 1536 | Suporta imagens, contexto 128K |
| **Google** | text-embedding-004 | $0.025 | 768 | Concorrente direto do OpenAI small |
| **Mistral** | mistral-embed | $0.10 | 1024 | Bom para textos europeus |
| **AWS Bedrock** | Titan Text Embeddings V2 | $0.02 | 1024 | Empata como mais barato |
| **Pinecone Inference** | llama-text-embed-v2 | $0.08 | 1024 | Útil se já usa Pinecone como vector store |

**Descontos disponíveis:**
- OpenAI: **50% off** via Batch API (até 24h para processar)
- Voyage AI: **33% off** via Files API
- Mistral: **50% off** via Batch API

### Self-hosted (rodando localmente)

| Modelo | Tipo | RAM/VRAM | Qualidade | Custo de API |
|---|---|---|---|---|
| **SPLADE++** (via FastEmbed) | Esparso neural | ~500 MB | Excelente para BM25 + semântica | **R$0** |
| **BGE-M3** | Denso + esparso | ~2 GB | Top em benchmarks open-source | **R$0** |
| **all-MiniLM-L6-v2** | Denso | ~80 MB | Bom para POC | **R$0** |
| **multilingual-e5-large** | Denso | ~1.1 GB | Bom para PT-BR | **R$0** |
| **Jina v3** | Denso | ~600 MB | Open-source competitivo | **R$0** |

**Custo real do self-hosted:** infraestrutura. Para 1 milhão de embeddings curtos (~100 tokens):

```
API (OpenAI small):    1M docs × 100 tokens × $0.02/1M tokens = $2.00
Self-hosted (BGE):     custo de uma VM com 8GB RAM ≈ $5-20/mês (servidor compartilhado)
```

Para volumes baixos, **API é mais barato**. Para volumes altos e contínuos (>10M embeddings/mês), **self-hosted compensa**.

### Comparação prática — 1 milhão de chunks de ~500 tokens cada

```
Volume total: 1M chunks × 500 tokens = 500M tokens

OpenAI text-embedding-3-small   →  $10.00   (mais barato cloud)
Voyage voyage-4-lite             →  $10.00
AWS Titan V2                     →  $10.00
Cohere Embed v3                  →  $50.00
OpenAI text-embedding-3-large    →  $65.00
Cohere Embed v4                  →  $60.00
Voyage voyage-4-large            →  $60.00

Self-hosted (BGE-M3 em CPU)      →  $0     (paga só infra)
```

---

## 2. LLMs (geração de resposta)

### Modelos cloud (API) — preços por 1M tokens

| Provedor | Modelo | Input | Output | Observação |
|---|---|---|---|---|
| **OpenAI** | GPT-5.2 | $1.75 | $14.00 | Flagship atual |
| **OpenAI** | GPT-4.1 mini | $0.40 | $1.60 | Ótimo custo-benefício |
| **OpenAI** | GPT-5 nano | $0.05 | $0.40 | Mais barato da OpenAI |
| **Anthropic** | Claude Opus 4.6 | $5.00 | $25.00 | Top de qualidade |
| **Anthropic** | Claude Sonnet 4.6 | $3.00 | $15.00 | Balanceado |
| **Anthropic** | Claude Haiku 4.5 | $1.00 | $5.00 | Rápido e barato |
| **Google** | Gemini 2.5 Pro | $1.25 | $10.00 | Contexto 1M+ tokens |
| **Google** | Gemini 2.5 Flash | $0.15 | $0.60 | Muito agressivo no preço |
| **Google** | Gemini 2.5 Flash-Lite | $0.10 | $0.40 | Mais barato com 1M context |
| **xAI** | Grok 4.1 | $0.20 | $0.50 | Barato pra flagship |
| **Cohere** | Command R+ 08-2024 | $2.50 | $10.00 | Otimizado pra RAG |
| **Cohere** | Command R 08-2024 | $0.15 | $0.60 | Tier intermediário |
| **Cohere** | Command R7B | $0.0375 | $0.15 | Um dos mais baratos do mercado |
| **Groq** | Llama 3.1 8B Instant | $0.05 | $0.08 | Hospeda open-source, super rápido |
| **DeepSeek** | DeepSeek V3.2 | $0.14 | $0.28 | Pressão de preço no mercado |
| **Mistral** | Mistral Small | $0.20 | $0.60 | Europeu, bom custo |

**Descontos disponíveis:**
- OpenAI/Anthropic: **50% off** via Batch API
- Cached prompts (cache de prefixo): até **90% off** nos tokens cacheados (OpenAI, Anthropic, Google)

### Self-hosted via Ollama

Roda local, sem custo de API. O custo é o hardware.

| Modelo | Tamanho | RAM mínima | GPU recomendada | Quando vale |
|---|---|---|---|---|
| **Llama 3.2 1B** | 1B params | 2 GB | Não precisa | POC, sumarização leve |
| **Llama 3.2 3B** | 3B params | 4 GB | Não precisa | Tarefas simples |
| **Llama 3.1 8B** | 8B params | 8 GB | Recomendada | Equivalente a Haiku |
| **Llama 3.3 70B** | 70B params | 48 GB | Obrigatória (24GB+ VRAM) | Equivalente a Sonnet |
| **Mistral 7B** | 7B params | 8 GB | Recomendada | Boa pra português |
| **Qwen 2.5 7B** | 7B params | 8 GB | Recomendada | Forte em código |

**O hardware é o gargalo:**

```
Llama 3.1 8B sem GPU       →  ~5-10 tokens/seg (lento, viável só pra dev)
Llama 3.1 8B com RTX 4090  →  ~80-120 tokens/seg (produção pequena)
Llama 3.3 70B com A100     →  ~30-50 tokens/seg (precisa data center)
```

### Comparação — 10.000 respostas por mês

Assumindo cada resposta = 1.000 tokens input + 500 tokens output:

```
Volume mensal: 10M tokens input + 5M tokens output

Cohere Command R7B          →  $0.375 + $0.75   = $1.13/mês
Groq Llama 3.1 8B           →  $0.50 + $0.40    = $0.90/mês  ← mais barato cloud
Gemini 2.5 Flash-Lite       →  $1.00 + $2.00    = $3.00/mês
GPT-4.1 mini                →  $4.00 + $8.00    = $12.00/mês
Claude Haiku 4.5            →  $10.00 + $25.00  = $35.00/mês
GPT-5.2                     →  $17.50 + $70.00  = $87.50/mês
Claude Sonnet 4.6           →  $30.00 + $75.00  = $105.00/mês

Ollama Llama 3.1 8B local   →  $0 API + ~$20-50/mês infra (depende do hardware)
```

---

## 3. Reranking

### Cloud (API)

| Provedor | Modelo | Preço | Observação |
|---|---|---|---|
| **Cohere** | Rerank v3.5 | $2.00 por 1.000 buscas | Padrão de mercado, até 100 docs/busca |
| **Cohere** | Rerank 4 Fast | $2.00 por 1M tokens | Por token, mais previsível |
| **Voyage AI** | rerank-2.5 | Por token (primeiros 200M grátis) | 32K context, instruction-following |
| **Voyage AI** | rerank-2.5-lite | Por token (primeiros 200M grátis) | Mais barato, ainda muito bom |
| **Pinecone** | pinecone-rerank-v0 | $0.08 por 1M tokens | Integrado se já usa Pinecone |
| **Jina AI** | jina-reranker-v2 | $0.02 por 1M tokens | Mais barato cloud |

### Self-hosted (cross-encoder)

| Modelo | Tamanho | RAM/VRAM | Latência (CPU) | Latência (GPU) |
|---|---|---|---|---|
| **ms-marco-MiniLM-L-6-v2** | 22 MB | 200 MB | ~100ms / 30 docs | ~10ms / 30 docs |
| **ms-marco-MiniLM-L-12-v2** | 33 MB | 300 MB | ~200ms / 30 docs | ~20ms / 30 docs |
| **BGE-reranker-large** | 1.5 GB | 2 GB VRAM | impraticável | ~50ms / 30 docs |
| **Qwen3-Reranker-8B** | 8 GB | 16 GB VRAM | impraticável | ~100ms / 30 docs |

### Comparação — 10.000 buscas por mês com reranking de 50 docs

```
Cohere Rerank v3.5          →  $20.00/mês     ($2 por 1k buscas)
Voyage rerank-2.5           →  ~$5-10/mês     (depende do tamanho dos docs)
Jina rerank v2              →  ~$0.50/mês     (token-based barato)

Self-hosted (MiniLM L-6 CPU) →  $0 API + custo da máquina (já incluído na stack)
```

---

## 4. Banco vetorial

### Self-hosted (Apache 2.0 / open-source — gratuitos)

| Banco | Licença | RAM (1M vetores 1536d) | Quando usar |
|---|---|---|---|
| **Qdrant** | Apache 2.0 | ~9 GB | Padrão do BuscaAI, melhor Filtered HNSW |
| **Weaviate** | BSD-3 | ~10 GB | Hybrid search nativo forte |
| **Milvus** | Apache 2.0 | ~8 GB | Escala bilhões de vetores |
| **Chroma** | Apache 2.0 | ~5 GB | Embedded, ótimo pra POC |
| **pgvector** | PostgreSQL License | ~12 GB | Já tem Postgres? Use isso |
| **LanceDB** | Apache 2.0 | ~6 GB | Disk-based, economiza RAM |

**Custo real do self-hosted:** servidor.

```
1M vetores (Qdrant standalone):
  Servidor 16GB RAM + SSD          →  ~$40-80/mês (Hetzner, DigitalOcean)
  Servidor AWS EC2 r6i.large       →  ~$120/mês

10M vetores (Qdrant cluster):
  3 nós 32GB RAM cada              →  ~$240-360/mês
  AWS m5.2xlarge × 3               →  ~$700/mês

100M+ vetores:
  Considerar disk-based (LanceDB, pgvector com pgvectorscale)
  Ou Qdrant com quantização + on-disk storage
```

### Cloud gerenciado

#### **Qdrant Cloud**

```
Free tier:        1 GB grátis (suficiente pra ~100k vetores)
Standard:         pay-as-you-go por cluster
                  ~$25-50/mês para 1M vetores 1536d
                  ~$150-300/mês para 10M vetores
Hybrid Cloud:     Qdrant gerencia no seu VPC
```

#### **Pinecone Serverless**

```
Modelo de cobrança:
  Storage:        $0.33/GB/mês
  Write units:    $4 por 1M (Standard) / $6 por 1M (Enterprise)
  Read units:     $16 por 1M (Standard) / $24 por 1M (Enterprise)

Estimativas de produção:
  100k vetores + 30k queries/mês     →  Free tier cobre
  1M vetores + 300k queries/mês      →  ~$50-100/mês
  10M vetores + 3M queries/mês       →  ~$300-800/mês
  50M+ vetores                       →  $1.500-3.000/mês

Free tier:   2 GB storage, 2M write units, 1M read units
             (chega para protótipos, suficiente até ~350k-1.5M vetores)
```

#### **Weaviate Cloud**

```
Sandbox:          14 dias grátis
Serverless:       a partir de $25/mês para datasets pequenos
                  ~$100-300/mês para 1M vetores
                  ~$500-1500/mês para 10M vetores
Enterprise:       custom, BYOC disponível
```

### Comparação — 1M vetores, 100k queries/mês

```
Qdrant self-hosted (Hetzner CX41)  →  ~$30/mês  ← mais barato
pgvector self-hosted (já tem PG)   →  ~$0 extra (cabe no Postgres atual)
Qdrant Cloud Standard              →  ~$50/mês
Pinecone Serverless                →  ~$50-100/mês
Weaviate Cloud Serverless          →  ~$100-300/mês
```

---

## 5. Infraestrutura de suporte

Custo da stack que roda em volta (PostgreSQL, Redis, workers, API).

### Self-hosted

| Serviço | Recurso típico | Custo mensal (Hetzner) |
|---|---|---|
| API (FastAPI) | 2 vCPU, 4 GB RAM | ~$10 |
| Workers (Celery) | 4 vCPU, 8 GB RAM | ~$25 |
| Redis | 1 vCPU, 2 GB RAM | ~$5 |
| Qdrant | 8 vCPU, 32 GB RAM | ~$60 |
| **Total stack mínima** | | **~$100/mês** |

### Cloud gerenciado (AWS)

| Serviço | Equivalente AWS | Custo mensal aproximado |
|---|---|---|
| API + Workers | ECS Fargate, 2 tasks | ~$70 |
| Redis | ElastiCache cache.t4g.small | ~$25 |
| Qdrant Cloud | Standard 1 cluster | ~$50 |
| Storage + egress | S3 + Data Transfer | ~$20 |
| **Total stack AWS** | | **~$165/mês** |

---

## 6. Cenários completos

Três cenários reais com estimativa total de custo mensal.

### Cenário 1 — Pequena empresa / POC

**Perfil:** chatbot interno, 100k chunks na base, 5k queries/mês.

```
EMBEDDINGS (ingestão única + queries)
  Ingestão: 100k × 500 tokens × $0.02/1M (OpenAI small)    = $1.00 (uma vez)
  Queries:  5k × 50 tokens × $0.02/1M                       = $0.005/mês

BANCO VETORIAL
  Qdrant self-hosted em VPS pequena                          = $20/mês

LLM (geração)
  5k respostas × 1500 tokens (média) × Gemini 2.5 Flash     = ~$5/mês

RERANKER
  5k buscas × Cohere Rerank v3.5                            = $10/mês

INFRA (Postgres, Redis, API)
  VPS dedicada                                               = $20/mês

──────────────────────────────────────────────────────────────────
TOTAL MENSAL                                                 ~$55/mês
TOTAL ANUAL                                                  ~$660/ano
```

### Cenário 2 — Produto em produção

**Perfil:** chatbot de cliente, 5M chunks, 100k queries/mês.

```
EMBEDDINGS
  Ingestão: 5M × 500 tokens × $0.02/1M                       = $50 (uma vez)
  Queries:  100k × 50 tokens × $0.02/1M                      = $0.10/mês

BANCO VETORIAL
  Qdrant Cloud Standard (5M vetores)                         = $150/mês
  OU Qdrant self-hosted em servidor 32GB RAM                 = $80/mês

LLM
  100k respostas × 1500 tokens × Claude Haiku 4.5            = $350/mês
  COM cache de prompt (90% off no contexto repetido)         = ~$100/mês

RERANKER
  100k buscas × Cohere Rerank v3.5                           = $200/mês

INFRA
  API + workers + Redis (cloud)                   = $100/mês

──────────────────────────────────────────────────────────────────
TOTAL MENSAL (com cloud + cache)                             ~$600/mês
TOTAL MENSAL (com self-hosted + cache)                       ~$430/mês
```

### Cenário 3 — Escala grande

**Perfil:** múltiplos clientes, 50M chunks, 1M queries/mês.

```
EMBEDDINGS
  Ingestão (uma vez): 50M × 500 tokens                       = $500
  Queries: 1M × 50 tokens                                    = $1/mês
  USAR EMBEDDING LOCAL (BGE-M3 self-hosted)                  = $0 API

BANCO VETORIAL
  Qdrant cluster self-hosted (3 nós 64GB RAM)                = $600/mês
  Pinecone Serverless equivalente                            = ~$1.500-3.000/mês

LLM
  1M respostas × Gemini 2.5 Flash + cache                    = ~$500/mês
  OU 70% Cohere R7B + 30% Sonnet                             = ~$800/mês
  OU 100% Claude Sonnet (qualidade máxima)                   = ~$3.000/mês

RERANKER
  Cohere v3.5                                                = $2.000/mês
  OU cross-encoder self-hosted em GPU                        = ~$200/mês (servidor)

INFRA
  Cluster Kubernetes + monitoramento                         = $800/mês

──────────────────────────────────────────────────────────────────
TOTAL MENSAL (econômico, self-hosted onde possível)          ~$2.100/mês
TOTAL MENSAL (cloud full, sem otimização)                    ~$7.000/mês
```

---

## 7. Como reduzir custos

Sete estratégias práticas que o BuscaAI suporta:

### 7.1 Embedding local em vez de API

```
1M chunks × OpenAI small:    $10 (uma vez, mas se reindexar é toda vez)
1M chunks × BGE-M3 local:    $0 + infra
```

**Quando trocar:** acima de 5M chunks ou se a base é reindexada com frequência.

### 7.2 Cache de queries

```
Sem cache: 100% das queries vão pro pipeline completo
Com cache (taxa hit 30%): 30% das queries não consomem nada
```

Configurável no settings com `CACHE.enabled = True`.

### 7.3 Prompt caching

OpenAI, Anthropic e Google oferecem até **90% de desconto** nos tokens cacheados quando o início do prompt se repete.

```
Sem cache:  10k respostas × 1000 tokens system × $1/1M  = $10
Com cache:  10k respostas × 1000 tokens cacheados × $0.10/1M  = $1
```

### 7.4 Roteamento por complexidade

Já discutido no fluxo do BuscaAI:

```
70% queries simples  →  modelo barato (Cohere R7B, Groq)
20% queries médias   →  modelo intermediário (Haiku, Gemini Flash)
10% queries complexas →  modelo top (Sonnet, GPT-5.2)
```

Economia típica: **60-80%** comparado a usar sempre o modelo top.

### 7.5 Batch API

Para ingestão e geração não-síncrona:

```
OpenAI Batch:    50% off
Anthropic Batch: 50% off
Voyage Batch:    33% off
Mistral Batch:   50% off
```

### 7.6 Reranker self-hosted para volumes altos

```
Cohere Rerank em produção: $2 por 1k buscas
→ 1M buscas/mês = $2.000/mês

MiniLM cross-encoder local em GPU pequena: ~$200/mês infra
→ 10x mais barato em volumes altos
```

### 7.7 Vector database self-hosted

```
Pinecone 10M vetores:           ~$500-800/mês
Qdrant self-hosted equivalente: ~$80-150/mês
```

A diferença paga DevOps com sobra.

---

## Como configurar no BuscaAI

Tudo isso é configurável no `rag_settings.py`:

```python
# usar modelo local de embedding
EMBEDDINGS = {
    "dense": {"provider": "local", "model": "BAAI/bge-m3"},
    "sparse": {"model": "splade"},
}

# roteamento por complexidade entre LLMs
LLM = {
    "default": "groq",                        # padrão barato
    "providers": {
        "groq":      {"model": "llama-3.1-8b-instant"},
        "anthropic": {"model": "claude-haiku-4-5"},
        "openai":    {"model": "gpt-5.2"},
    },
}

# reranker local
RETRIEVAL = {
    "reranker": True,
    "reranker_model": "cross-encoder/ms-marco-MiniLM-L-6-v2",  # local
}

# vector store self-hosted
VECTOR_STORE = {
    "backend": "qdrant",
    "host": "qdrant",                         # docker-compose interno
}

# cache agressivo
CACHE = {"enabled": True, "ttl": 86400}      # 24h
```

---

## Resumo executivo de custos

```
ETAPA              MAIS BARATO CLOUD        MAIS BARATO LOCAL
─────────────────────────────────────────────────────────────
Embeddings         OpenAI small ($0.02)     BGE-M3 (grátis)
LLM resposta       Groq Llama 8B ($0.05/$0.08)  Llama 3.1 8B (infra)
Reranker           Jina v2 ($0.02/1M)       MiniLM cross-encoder (infra)
Vector DB          Qdrant Cloud free        Qdrant Docker (infra)
─────────────────────────────────────────────────────────────

REGRA GERAL:
  < 1M chunks       → tudo cloud, mais simples e barato
  1M a 10M chunks   → embedding cloud, banco self-hosted
  > 10M chunks      → embedding e LLM local quando possível,
                      vector DB sempre self-hosted
```

A flexibilidade do BuscaAI permite começar 100% em cloud para um POC barato e ir migrando partes para self-hosted conforme o volume cresce, sem refatorar código — só mudando configuração.
