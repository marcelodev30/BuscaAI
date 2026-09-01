# Comparativo de Rerankers para RAG — 2026

Dados baseados em Agentset Reranker Leaderboard (fev/2026), FutureAGI (jul/2025),
benchmark Medium (set/2025) e Cohere Pricing (mai/2026).

> **Nota sobre custos:** reranker é aplicado apenas ao top-K do retrieval (ex: 50 chunks),
> não à base inteira. O custo por query é baixo mesmo nas APIs pagas — veja os cenários
> abaixo antes de decidir entre API e self-hosted.

---

## Sumário

- [Comparativo de Rerankers para RAG — 2026](#comparativo-de-rerankers-para-rag--2026)
  - [Sumário](#sumário)
  - [1. Cloud API](#1-cloud-api)
    - [Custos cloud reais — 10k buscas/mês (50 docs × 500 tokens = 25M tokens)](#custos-cloud-reais--10k-buscasmês-50-docs--500-tokens--25m-tokens)
    - [Quando API compensa](#quando-api-compensa)
  - [2. Self-hosted](#2-self-hosted)
    - [Custos infra self-hosted](#custos-infra-self-hosted)
    - [Quando self-hosted compensa](#quando-self-hosted-compensa)
  - [3. Comparativo de custos por volume](#3-comparativo-de-custos-por-volume)
  - [4. Impacto na qualidade do RAG](#4-impacto-na-qualidade-do-rag)
  - [5. Guia de decisão](#5-guia-de-decisão)
  - [6. Integração](#6-integração)
    - [Recomendação por fase](#recomendação-por-fase)
  - [Fontes](#fontes)

---

## 1. Cloud API

Rerankers acessados via chamada HTTP — sem infra, sem modelo local.

| Modelo                     | nDCG@10     | Latência (50 docs) | Contexto   | Multilíngue    | Custo / 1M tokens | Custo / 1k buscas* | Melhor para                                    |
| -------------------------- | ----------- | ------------------ | ---------- | -------------- | ----------------- | ------------------ | ---------------------------------------------- |
| **Cohere Rerank 4 Pro**    | 0.735+      | ~210ms             | 32K        | ✓ 100+ idiomas | $2.00             | ~$2.00             | Melhor qualidade cloud, multilíngue enterprise |
| **Cohere Rerank 4 Fast**   | ~0.700      | ~100ms             | 33K        | ✓ 100+ idiomas | $2.00             | ~$2.00             | Latência crítica, chatbot tempo real           |
| **Voyage rerank-2.5**      | ~0.720      | ~595ms             | 32K        | ✓ multilíngue  | pay-per-token     | ~$0.50–1.00        | 200M tokens grátis, jurídico/financeiro        |
| **Voyage rerank-2.5-lite** | ~0.690      | ~400ms             | 16K        | ✓ multilíngue  | pay-per-token     | ~$0.20–0.50        | Volume alto, custo menor                       |
| **Jina Reranker v2**       | 0.694       | ~110ms             | 8K         | ✓ multilíngue  | $0.02             | ~$0.02             | **Mais barato cloud**, multimodal              |
| **Pinecone Rerank v0**     | melhor BEIR | ~150ms             | 512 tokens | ✗ inglês       | $0.08             | ~$0.08             | Melhor NDCG@10, já usa Pinecone                |

*Estimativa para 50 documentos de ~500 tokens cada por busca.

### Custos cloud reais — 10k buscas/mês (50 docs × 500 tokens = 25M tokens)

```
Jina Reranker v2       → ~$0.50/mês     ← mais barato
Pinecone Rerank v0     → ~$2.00/mês
Voyage rerank-2.5-lite → ~$5–10/mês     (após free tier)
Voyage rerank-2.5      → $0/mês         (dentro dos 200M grátis)
Cohere Rerank 4        → ~$50/mês

Conclusão para 10k buscas: API é extremamente barata.
Até Cohere a $50/mês é razoável para produção pequena.
```

### Quando API compensa

```
✓ Volume < 100k buscas/mês (Jina sai por < $5/mês)
✓ Time sem GPU disponível
✓ Quer multilíngue sem modelo local
✓ POC e MVP — sem infra extra
✓ Voyage rerank-2.5: 200M tokens grátis = ~4M buscas sem custo
```

---

## 2. Self-hosted

Modelos que rodam localmente — custo de API zero, paga só o hardware.

| Modelo                    | nDCG@10 | Latência CPU (30 docs) | Latência GPU | Contexto   | Multilíngue   | Licença    | RAM/VRAM   | Melhor para                        |
| ------------------------- | ------- | ---------------------- | ------------ | ---------- | ------------- | ---------- | ---------- | ---------------------------------- |
| **MiniLM-L-6-v2**         | 0.662   | ~55ms                  | ~5ms         | 512 tokens | ✗ inglês      | Apache 2.0 | ~90MB      | Padrão BuscaAI, zero custo, CPU ok |
| **MiniLM-L-12-v2**        | 0.678   | ~120ms                 | ~12ms        | 512 tokens | ✗ inglês      | Apache 2.0 | ~130MB     | Melhor que L-6, ainda CPU viável   |
| **BGE Reranker v2-m3**    | 0.715   | ~145ms                 | ~20ms        | 8K         | ✓ multilíngue | Apache 2.0 | ~1.2GB     | Melhor OSS multilíngue, PT-BR      |
| **mxbai-rerank-large-v2** | ~0.710  | ~120ms                 | ~15ms        | 8K         | ✓ multilíngue | Apache 2.0 | ~1.5GB     | Alternativa ao BGE, API disponível |
| **ColBERT v2**            | ~0.700  | impraticável           | ~80ms        | 512 tokens | ✓ parcial     | MIT        | ~2GB VRAM  | Docs longos, match token-level     |
| **BGE Reranker Large v2** | 0.728   | impraticável           | ~40ms        | 8K         | ✓ multilíngue | Apache 2.0 | ~3GB VRAM  | Máxima qualidade OSS               |
| **MonoT5 3B**             | 0.726   | ~480ms                 | ~60ms        | 512 tokens | ✗ limitado    | Apache 2.0 | ~6GB RAM   | Jurídico/biomédico em inglês       |
| **Qwen3 Reranker 8B**     | 0.735+  | impraticável           | ~100ms       | 32K        | ✓ forte       | Apache 2.0 | ~16GB VRAM | Máxima qualidade OSS PT-BR         |

### Custos infra self-hosted

```
HARDWARE               MODELOS VIÁVEIS              CUSTO ESTIMADO
──────────────────────────────────────────────────────────────────
CPU (qualquer)         MiniLM-L-6, MiniLM-L-12      $0 extra (usa CPU livre)
CPU + 2GB RAM extra    BGE v2-m3, mxbai              $0 extra ou VPS ~$5/mês
GPU 4-8GB VRAM         BGE Large, ColBERT            RTX 3060: ~$200/mês server
GPU 16GB VRAM          Qwen3 8B, MonoT5              RTX 4090: ~$500+/mês server
──────────────────────────────────────────────────────────────────
```

### Quando self-hosted compensa

```
✓ Volume > 200k buscas/mês (Cohere ficaria > $400/mês)
✓ Dados sensíveis que não podem sair do servidor
✓ GPU disponível na stack (já amortizada)
✓ PT-BR com BGE v2-m3 (API cloud menos precisa)
✓ Apache 2.0 obrigatório sem custo variável
```

---

## 3. Comparativo de custos por volume

Assumindo 50 docs × ~500 tokens por busca = 25k tokens/busca.

```
VOLUME            JINA API      COHERE API    BGE v2-m3 CPU   BGE v2-m3 GPU
──────────────────────────────────────────────────────────────────────────────
1k buscas/mês     $0.025        $2.00         $0 API          $0 API
10k buscas/mês    $0.25         $20.00        $0 API          $0 API
50k buscas/mês    $1.25         $100.00       $0 API          $0 API
100k buscas/mês   $2.50         $200.00       $0 API          $0 API
500k buscas/mês   $12.50        $1.000.00     $0 API + infra  $0 API + GPU
1M buscas/mês     $25.00        $2.000.00     $0 API + infra  $0 API + GPU
──────────────────────────────────────────────────────────────────────────────
Infra self-hosted:  CPU (já existente): $0 extra
                    GPU server:         ~$200–500/mês

Break-even Jina vs GPU server:   ~500k buscas/mês
Break-even Cohere vs GPU server: ~50k buscas/mês
```

**Conclusão prática:**
- Até 50k buscas/mês → Jina API ($1.25) ou Voyage grátis — API vence
- 50k–200k buscas/mês → Jina ainda barato, Cohere começa a pesar
- Acima de 200k/mês → self-hosted com BGE v2-m3 em CPU quase sempre vence

---

## 4. Impacto na qualidade do RAG

```
MÉTRICA           SEM RERANKER    MINIML-L-6    BGE V2-M3       COHERE PRO
───────────────────────────────────────────────────────────────────────────
Precision@5       0.55–0.70       0.68–0.80     0.75–0.85       0.80–0.88
Recall@5          0.65–0.80       0.65–0.80     0.65–0.82       0.68–0.85
nDCG@10           0.60–0.72       0.66–0.75     0.71–0.80       0.74–0.84
Faithfulness      0.65–0.75       0.72–0.82     0.76–0.86       0.79–0.89
Hallucination     0.20–0.30       0.15–0.22     0.12–0.18       0.09–0.15
───────────────────────────────────────────────────────────────────────────
```

Ganho típico ao adicionar reranker: **+15–40% em Precision@5**.
O reranker é o componente de pós-retrieval com maior ganho isolado no pipeline.

---

## 5. Guia de decisão

```
VOLUME BAIXO (< 50k buscas/mês):
  Inglês:         Jina v2 API ($0.02/1M) — ~$1/mês no pior caso
  Multilíngue:    Voyage rerank-2.5 (200M tokens grátis)
  Zero config:    Cohere Rerank 4 Fast ($2/1k buscas)

VOLUME MÉDIO (50k–200k buscas/mês):
  Jina API ainda barato (~$1–5/mês)
  OU BGE v2-m3 self-hosted em CPU (sem custo extra de API)

VOLUME ALTO (> 200k buscas/mês):
  BGE v2-m3 self-hosted (CPU viável)
  OU BGE Large / Qwen3 se GPU disponível

PT-BR OBRIGATÓRIO:
  Cloud:          Cohere Rerank 4 (100+ idiomas)
  Self-hosted:    BGE v2-m3 ou Qwen3 8B

DOCS MUITO LONGOS (> 512 tokens):
  Cloud:          Voyage rerank-2.5 (32K contexto)
  Self-hosted:    BGE v2-m3 (8K) ou Qwen3 8B (32K)

GPU DISPONÍVEL:
  Máxima qualidade OSS:  Qwen3 8B (Apache 2.0, 16GB VRAM)
  Boa qualidade, menos:  BGE Large (3GB VRAM)
  Token-level:           ColBERT v2 (docs longos)
```

---

## 6. Integração

```python
# rag_settings.py

# CLOUD — Jina API (mais barata)
RETRIEVAL = {
    "reranker":       True,
    "reranker_model": "jina",
    "final_top_k":    5,
}

# CLOUD — Cohere (melhor qualidade)
RETRIEVAL = {
    "reranker":             True,
    "reranker_model":       "cohere",
    "cohere_rerank_model":  "rerank-v3.5",
    "final_top_k":          5,
}

# CLOUD — Voyage (free tier generoso)
RETRIEVAL = {
    "reranker":             True,
    "reranker_model":       "voyage",
    "voyage_rerank_model":  "rerank-2.5",
    "final_top_k":          5,
}

# SELF-HOSTED — MiniLM (padrão BuscaAI, CPU ok)
RETRIEVAL = {
    "reranker":       True,
    "reranker_model": "cross-encoder/ms-marco-MiniLM-L-6-v2",
    "final_top_k":    5,
}

# SELF-HOSTED — BGE v2-m3 (PT-BR, multilíngue)
RETRIEVAL = {
    "reranker":       True,
    "reranker_model": "BAAI/bge-reranker-v2-m3",
    "final_top_k":    5,
}
```

### Recomendação por fase

```
FASE              CLOUD                       SELF-HOSTED
────────────────────────────────────────────────────────────────────
POC               Voyage grátis (200M)        MiniLM-L-6 (CPU)
MVP (inglês)      Jina v2 (~$0–1/mês)         MiniLM-L-6 (CPU)
MVP (PT-BR)       Cohere Fast                 BGE v2-m3 (CPU)
Produção          Jina ou Voyage              BGE v2-m3 (CPU)
Alta qualidade    Cohere Pro                  Qwen3 8B (GPU)
Volume > 200k     Jina ainda ok              BGE v2-m3 auto-hospedar
────────────────────────────────────────────────────────────────────
```

---

## Fontes

- Agentset Reranker Leaderboard (fev/2026) — agentset.ai/rerankers
- FutureAGI: "Best Rerankers for RAG in 2026" (jul/2025)
- Medium: "Top 8 Rerankers: Quality vs Cost" (set/2025)
- Cohere API Pricing (mai/2026)
