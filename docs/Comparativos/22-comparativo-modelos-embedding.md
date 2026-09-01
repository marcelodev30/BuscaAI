# Comparativo de Modelos de Embedding — 2026

Dados baseados no MTEB Leaderboard (abr/2026), Ailog RAG (abr/2026),
TokenMix (abr/2026), AwesomeAgents (abr/2026) e BuildMVPFast (mar/2026).

> **Nota sobre custos:** embeddings são dramaticamente mais baratos que LLMs.
> Mesmo a 100M tokens/mês, o modelo mais caro aqui (Voyage large a $0.12/1M)
> custa apenas $12/mês. Para a maioria dos projetos, **API de embedding é
> mais barata que self-hosted** quando considerado o custo de infra.
> Self-hosted compensa acima de 50M embeddings/mês em produção contínua.

---

## Sumário

1. [Cloud API](#1-cloud-api)
2. [Self-hosted (open-source)](#2-self-hosted)
3. [Comparativo de custos por volume](#3-comparativo-de-custos-por-volume)
4. [Embedding esparso — hybrid search](#4-embedding-esparso)
5. [Guia de decisão](#5-guia-de-decisão)
6. [Integração com o BuscaAI](#6-integração-com-o-buscaai)

---

## 1. Cloud API

Modelos acessados via chamada HTTP — sem infra, sem GPU, sem modelo local.

| Modelo | MTEB Score | Dimensões | Contexto | Multilíngue | Esparso | Custo / 1M tokens | Free tier | Melhor para |
|---|---|---|---|---|---|---|---|---|
| **Gemini Embedding 2** | **67.71** | 3072 | 32K | ✓ 100+ idiomas | ✗ | $0.025/1M | ✓ generoso | Melhor MTEB retrieval, multimodal, mais barato premium |
| **Voyage voyage-4-large** | ~67.0 | 2048 | 32K | ✓ multilíngue | ✗ | $0.12/1M | 200M tokens | Top RAG, jurídico, financeiro |
| **Cohere Embed v4** | 65.2 | 1536 | **128K** | ✓ 100+ idiomas | ✗ | $0.12/1M | Trial | Docs muito longos, multilíngue enterprise |
| **OpenAI text-3-large** | 64.6 | 3072 | 8K | ⚠ parcial | ✗ | $0.13/1M | — | Ecossistema OpenAI, Matryoshka, qualidade premium |
| **Voyage voyage-4** | ~65.0 | 1024 | 32K | ✓ multilíngue | ✗ | $0.06/1M | 200M tokens | Boa qualidade, custo intermediário |
| **Cohere Embed v3 Multilingual** | ~63.5 | 1024 | 8K | ✓ 100+ idiomas | ✗ | $0.10/1M | Trial | Multilíngue, pair com Cohere Rerank |
| **OpenAI text-3-small**  | 62.3 | 1536 | 8K | ⚠ parcial | ✗ | $0.02/1M | — | Padrão BuscaAI, melhor custo-benefício API |
| **Voyage voyage-4-lite** | ~61.0 | 1024 | 32K | ✓ multilíngue | ✗ | $0.02/1M | 200M tokens | Mesmo preço OpenAI small + 32K contexto |
| **Jina Embeddings v3** | ~63.0 | 1024 | 32K | ✓ multilíngue | ✗ | $0.02/1M | — | Custo-benefício, docs longos |
| **Google text-embedding-005** | ~63.0 | 768 | 2K | ✓ multilíngue | ✗ | **$0.006/1M** | ✓ generoso | Mais barato cloud, já usa GCP |
| **Amazon Titan V2** | ~62.0 | 1024 | 8K | ✓ parcial | ✗ | $0.02/1M | AWS free tier | Já usa AWS |

### Custos cloud reais — ingestão de 1M chunks × 500 tokens = 500M tokens

```
Google text-005         → $3.00      ← mais barato
OpenAI text-3-small     → $10.00     ← padrão BuscaAI
Voyage voyage-4-lite    → $10.00     (ou grátis no free tier de 200M)
Jina Embeddings v3      → $10.00
Voyage voyage-4         → $30.00
Cohere Embed v3 Multi   → $50.00
Cohere Embed v4         → $60.00
Voyage voyage-4-large   → $60.00
OpenAI text-3-large     → $65.00

Com Batch API (50% off):
OpenAI text-3-small     → $5.00 ← usando Batch API
```

### Quando API compensa

```
✓ Volume < 50M embeddings/mês (a maioria dos projetos)
✓ Time sem GPU ou servidor dedicado
✓ Ingestão eventual — não contínua
✓ POC e MVP — simplifica stack
✓ Voyage 4-lite ou OpenAI small: ingestão de 1M docs custa ~$10
```

---

## 2. Self-hosted

Modelos que rodam localmente — custo de API zero, paga só o hardware.

| Modelo | MTEB Score | Dimensões | Contexto | Multilíngue | Esparso | Licença | RAM/VRAM | Melhor para |
|---|---|---|---|---|---|---|---|---|
| **NV-Embed-v2** | **72.31** | 4096 | 32K | ⚠ parcial | ✗ | CC-BY-NC-4.0 | ~16GB VRAM | Melhor MTEB OSS — não comercial |
| **Jina v5 text-small** | 71.7 (v2) | 1024 | 8K | ✓ multilíngue | ✗ | Apache 2.0 | ~2GB VRAM | Melhor qualidade/tamanho Apache 2.0 |
| **Qwen3-Embedding-8B** | 70.58 | 4096 | 32K | ✓ forte | ✗ | Apache 2.0 | ~16GB VRAM | Máxima qualidade OSS comercial, PT-BR |
| **BGE-M3**  | 63.0 | 1024 | 8K | ✓ 100+ idiomas | ✓ SPLADE | Apache 2.0 | ~2GB | Padrão OSS BuscaAI — denso+esparso+PT-BR |
| **mxbai-embed-large-v1** | ~64.5 | 1024 | 512 tokens | ⚠ parcial | ✗ | Apache 2.0 | ~1.5GB | Leve, CPU ok, custo zero |
| **nomic-embed-text-v1.5** | ~62.0 | 768 | 8K | ⚠ parcial | ✗ | Apache 2.0 | ~500MB | Hardware fraco, POC local |
| **all-MiniLM-L6-v2** | ~56.0 | 384 | 256 tokens | ✗ inglês | ✗ | Apache 2.0 | ~80MB | Dev local ultrarrápido |

### Custos infra self-hosted

```
HARDWARE                    MODELOS VIÁVEIS              CUSTO ESTIMADO
────────────────────────────────────────────────────────────────────────
CPU (qualquer máquina)      MiniLM, nomic-embed           $0 extra
CPU + 2GB RAM               BGE-M3, mxbai                 $0 ou VPS ~$10/mês
GPU 2-4GB VRAM              BGE-M3, Jina v5               RTX 3060: ~$150/mês
GPU 16GB VRAM               Qwen3-8B, NV-Embed-v2         RTX 4090: ~$400+/mês
────────────────────────────────────────────────────────────────────────
```

### Quando self-hosted compensa

```
✓ Volume > 50M embeddings/mês em produção contínua
✓ Reindexação frequente (mudança de base regularmente)
✓ Dados que não podem sair do servidor (LGPD, saúde)
✓ GPU já disponível na stack (custo amortizado)
✓ PT-BR com BGE-M3 (qualidade melhor que APIs genéricas)
✓ Hybrid search nativo com BGE-M3 (denso + esparso juntos)
```

---

## 3. Comparativo de custos por volume

```
VOLUME MENSAL     GOOGLE API    OPENAI SMALL    BGE-M3 CPU    QWEN3 GPU
──────────────────────────────────────────────────────────────────────────
1M tokens         $0.006        $0.02           $0 API        $0 API
10M tokens        $0.06         $0.20           $0 API        $0 API
100M tokens       $0.60         $2.00           $0 API        $0 API
500M tokens       $3.00         $10.00          $0 API        $0 API
1B tokens         $6.00         $20.00          $0 API        $0 API
5B tokens         $30.00        $100.00         $0 + infra    $0 + GPU
10B tokens        $60.00        $200.00         $0 + infra    $0 + GPU
──────────────────────────────────────────────────────────────────────────
Infra self-hosted: CPU (existente): $0 extra | GPU server: ~$150–400/mês

Break-even OpenAI small vs CPU server:   ~5B tokens/mês
Break-even Google text-005 vs CPU:       ~25B tokens/mês
```

**Conclusão prática:**
- Para a maioria dos projetos RAG: **API é mais barata no total**
- Ingestão de 100k docs × 500 tokens = 50M tokens = **$1 com OpenAI small**
- Self-hosted só vence acima de ~50M tokens/mês em ingestão contínua

---

## 4. Embedding Esparso

Para hybrid search no BuscaAI, é preciso embedding denso (semântico) + esparso (léxico).

### Opção A — Dois modelos separados (API + local)

```
Denso:   OpenAI text-3-small  → API ($0.02/1M)
Esparso: SPLADE++ via FastEmbed → local (gratuito, ~500MB)

Custo: só o denso via API
Complexidade: dois modelos, mas simples de configurar
```

### Opção B — BGE-M3 unificado (self-hosted)

```
BGE-M3 gera denso + esparso + colBERT em uma única inferência

Custo: $0 API, ~2GB RAM
Vantagem: um único modelo faz tudo
Desvantagem: servidor local necessário
```

### Opção C — Qdrant faz o esparso internamente

```
Você fornece só embedding denso (qualquer API)
Qdrant v1.9+ gera BM25 internamente

Custo: só o denso via API
Complexidade: menor — Qdrant cuida do esparso
Qualidade: BM25 básico, menor que SPLADE
```

### Suporte por modelo

```
BGE-M3              → ✓ denso + esparso + colBERT (Apache 2.0)
SPLADE++ (FastEmbed)→ ✓ dedicado esparso (gratuito, local)
OpenAI / Voyage     → ✗ só denso (esparso via Qdrant ou SPLADE separado)
Cohere / Google     → ✗ só denso
Voyage 4-nano       → ✗ só denso (mas Apache 2.0, gratuito)
```

---

## 5. Guia de decisão

```
PRIORIDADE: CUSTO MÍNIMO (API)
  Mais barato cloud:     Google text-005 ($0.006/1M)
  Melhor custo-benefício: OpenAI text-3-small ($0.02/1M)
  Free tier generoso:    Voyage 4-lite (200M tokens grátis)

PRIORIDADE: CUSTO ZERO (self-hosted)
  Sem GPU, PT-BR:        BGE-M3 (~2GB RAM) ← padrão OSS BuscaAI
  Sem GPU, inglês:       nomic-embed (~500MB) ou mxbai (~1.5GB)
  GPU 2GB:               Jina v5 (Apache 2.0, MTEB 71.7)
  GPU 16GB:              Qwen3-8B (Apache 2.0, MTEB 70.58)

PRIORIDADE: MELHOR QUALIDADE (API)
  Retrieval geral:       Gemini Embedding 2 ($0.025/1M)
  RAG especializado:     Voyage voyage-4-large ($0.12/1M)
  Docs muito longos:     Cohere Embed v4 (128K contexto)
  Ecossistema OpenAI:    text-3-large ($0.13/1M)

PRIORIDADE: MELHOR QUALIDADE (self-hosted)
  Apache 2.0, GPU:       Qwen3-8B (MTEB 70.58)
  Não-comercial, GPU:    NV-Embed-v2 (MTEB 72.31)

CASOS ESPECIAIS
  PT-BR sem GPU:         BGE-M3 (100+ idiomas, Apache 2.0)
  PT-BR com GPU:         Qwen3-8B
  Hybrid search OSS:     BGE-M3 (único denso+esparso Apache 2.0)
  Contexto > 8K tokens:  Cohere v4 (128K) ou Voyage (32K) ou Jina v3 (32K)
  Multimodal:            Gemini Embedding 2
  Volume > 50M/mês:      avaliar self-hosted
  Apache 2.0 comercial:  BGE-M3, Qwen3, Jina v5, nomic, mxbai

CHECKLIST:
  □ Base em PT-BR?           → BGE-M3 ou Cohere/Voyage multilíngue
  □ Chunks > 8K tokens?      → Cohere v4 (128K) ou Voyage (32K)
  □ Hybrid search?           → BGE-M3 (único OSS nativo)
  □ Apache 2.0 comercial?    → exclui NV-Embed-v2 e Jina v3
  □ Volume > 50M tokens/mês? → avaliar self-hosted
  □ Dados on-premise?        → self-hosted obrigatório
  □ Multimodal?              → Gemini Embedding 2
```

---

## 6. Integração com o BuscaAI

```python
# rag_settings.py

# CLOUD — OpenAI (padrão API, mais popular)
EMBEDDINGS = {
    "dense": {
        "provider":   "openai",
        "model":      "text-embedding-3-small",
        "dimension":  1536,
        "batch_size": 100,
    },
    "sparse": {"model": "splade"},   # local via FastEmbed
}

# CLOUD — Google (mais barato)
EMBEDDINGS = {
    "dense": {
        "provider":  "google",
        "model":     "text-embedding-005",
        "dimension": 768,
    },
    "sparse": {"model": "splade"},
}

# CLOUD — Voyage (melhor RAG)
EMBEDDINGS = {
    "dense": {
        "provider":  "voyage",
        "model":     "voyage-4-large",
        "dimension": 2048,
    },
    "sparse": {"model": "splade"},
}

# CLOUD — Cohere (multilíngue, docs longos)
EMBEDDINGS = {
    "dense": {
        "provider":  "cohere",
        "model":     "embed-multilingual-v3.0",
        "dimension": 1024,
    },
    "sparse": {"model": "splade"},
}

# SELF-HOSTED — BGE-M3 (padrão OSS, denso+esparso unificado)
EMBEDDINGS = {
    "dense": {
        "provider":  "local",
        "model":     "BAAI/bge-m3",
        "dimension": 1024,
    },
    "sparse": {
        "model": "bge-m3-sparse",   # mesmo modelo, saída esparsa
    },
}

# SELF-HOSTED — Qwen3 (máxima qualidade OSS)
EMBEDDINGS = {
    "dense": {
        "provider":  "local",
        "model":     "Qwen/Qwen3-Embedding-8B",
        "dimension": 4096,
    },
    "sparse": {"model": "splade"},
}
```

### Recomendação por fase

```
FASE              CLOUD                        SELF-HOSTED
──────────────────────────────────────────────────────────────────
POC               OpenAI small ($0.02/1M)      nomic-embed (500MB)
MVP (inglês)      OpenAI small                 mxbai (1.5GB CPU)
MVP (PT-BR)       Voyage lite (free 200M)      BGE-M3 (2GB CPU)
Produção API      OpenAI small ou Voyage lite  —
Produção OSS      —                            BGE-M3 ← padrão BuscaAI
Alta qualidade    Gemini ou Voyage large        Qwen3-8B (GPU)
Docs longos       Cohere v4 (128K ctx)         Jina v5 (8K)
Vol > 50M/mês     avaliar custo real           BGE-M3 auto-hospedar
──────────────────────────────────────────────────────────────────
```

---

## Fontes

- MTEB Leaderboard — huggingface.co/spaces/mteb/leaderboard (abr/2026)
- Ailog RAG: "Best Embedding Models 2025" (abr/2026)
- TokenMix: "Text Embedding Models 2026" (abr/2026)
- AwesomeAgents: "Embedding Models Pricing" (abr/2026)
- BuildMVPFast: "Voyage 3.5 vs OpenAI vs Cohere 2026" (mar/2026)
