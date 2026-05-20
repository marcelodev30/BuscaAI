# Arquitetura do Framework BuscaAI

Este arquivo descreve como o BuscaAI é montado: a visão geral, o arquivo de configuração central, a estrutura de pastas, a API e a CLI.

---

## Visão geral

O BuscaAI é um framework de RAG híbrido, modular, para desenvolvedores. A experiência de uso é:

```
O desenvolvedor:
  1. configura um arquivo central (rag_settings.py)
  2. sobe o ambiente com docker-compose
  3. consome o sistema via API HTTP ou via CLI
```

A ideia-chave: o desenvolvedor **não precisa saber de RAG** para usar. Ele configura e consome. A complexidade fica encapsulada.

```
rag_settings.py
      ↓
┌─────────────────────────────────┐
│         BUSCA AI                │
│                                 │
│  Grafo de Ingestão (LangGraph)  │
│  Grafo de Busca   (LangGraph)   │
│  Grafo de Chat    (LangGraph)   │
└─────────────────────────────────┘
      ↓
  Banco vetorial (Qdrant)
```

---

## A stack tecnológica

```
Orquestração:     LangGraph
Banco vetorial:   Qdrant (decisão final pendente — ver trade-offs)
Pré-filtro:       BM25 / índice invertido
Busca:            Híbrida (densa + esparsa + RRF)
Reranker:         Cohere ou cross-encoder (opcional)
Embeddings:       OpenAI, Cohere, local (plugável)
LLM:              OpenAI, Anthropic, Groq, Ollama (plugável)
API:              FastAPI
Fila de tarefas:  Celery + Redis
Cache:            Redis
Avaliação:        RAGAS
CLI:              Click
```

---

## O arquivo de configuração central

Inspirado no `settings.py` do Django: um único arquivo Python onde tudo é configurado. Python puro (não YAML) porque permite usar variáveis de ambiente, tem lógica condicional e dá autocompletar na IDE.

Por que Python e não YAML:

| | YAML | Python (settings) |
|---|---|---|
| Chaves de API | expostas em texto | via variável de ambiente |
| Lógica condicional | não tem | tem |
| Autocompletar na IDE | não | sim |

Estrutura do `rag_settings.py` (resumida):

```python
import os

# ─── Chaves de API ───────────────────────────────
OPENAI_API_KEY    = os.environ.get("OPENAI_API_KEY")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
COHERE_API_KEY    = os.environ.get("COHERE_API_KEY")
GROQ_API_KEY      = os.environ.get("GROQ_API_KEY")

# ─── Banco vetorial ──────────────────────────────
VECTOR_STORE = {"backend": "qdrant", "host": "localhost", "port": 6333}

# ─── Pré-filtragem léxica ────────────────────────
PRE_FILTERING = {"enabled": True, "strategy": "bm25", "top_n": 50000}

# ─── Embeddings ──────────────────────────────────
EMBEDDINGS = {
    "dense":  {"provider": "openai", "model": "text-embedding-3-small"},
    "sparse": {"model": "splade"}
}

# ─── LLMs ────────────────────────────────────────
LLM = {
    "default": "openai",
    "providers": {
        "openai":    {"model": "gpt-4o-mini",          "temperature": 0.0},
        "anthropic": {"model": "claude-haiku-4-5",     "temperature": 0.0},
        "groq":      {"model": "llama-3.1-8b-instant", "temperature": 0.0},
        "ollama":    {"host": "localhost", "port": 11434, "model": "llama3.2"}
    }
}

# ─── Funções de LLM (cada uma com seu provedor) ──
LLM_FEATURES = {
    "generation":      {"enabled": True,  "provider": "openai"},
    "query_expansion": {"enabled": False, "provider": "groq"},
    "llm_reranker":    {"enabled": False, "provider": "groq"}
}

# ─── Chunking ────────────────────────────────────
CHUNKING = {"strategy": "recursive", "chunk_size": 512, "overlap": 50}

# ─── Retrieval ───────────────────────────────────
RETRIEVAL = {
    "strategy": "hybrid", "top_k": 50,
    "reranker": True, "reranker_model": "cohere", "final_top_k": 5
}

# ─── Chat ────────────────────────────────────────
CHAT = {
    "provider": "openai", "model": "gpt-4o-mini",
    "system_prompt": "Responda apenas com base nos documentos fornecidos.",
    "historico_max": 10, "stream": False
}

# ─── Fontes de dados e agendamento ───────────────
SOURCES  = { "banco_clientes": {"type": "postgresql", "query": "SELECT ..."} }
SCHEDULE = { "banco_clientes": "0 2 * * *" }   # reingestão diária

# ─── Segurança ───────────────────────────────────
AUTH          = {"token_expiry": 3600}
ROLES         = {"admin": [...], "editor": [...], "reader": ["search"]}
RATE_LIMITING = {"enabled": True, "backend": "redis", "limits": {...}}
SECURITY      = {"prompt_injection_scan": True, "https_only": True, "cors": {...}}

# ─── Infra e qualidade ───────────────────────────
CACHE      = {"enabled": True, "backend": "redis", "ttl": 3600}
BACKUP     = {"qdrant": {...}}
BENCHMARK  = {"ragas": {...}}            # config do RAGAS (ver arquivo 09)
EVALUATION = {"enabled": True, "log_queries": True,   # monitoramento contínuo
              "latency_tracking": True, "alert_on_low_score": True}
LOGGING    = {"enabled": True, "backend": "postgresql"}

# ─── Multi-tenant (opcional) ─────────────────────
MULTITENANCY = {"enabled": False, "isolation": "collection",
                "tenant_field": "tenant_id"}
```

Nem todos os blocos são obrigatórios. O mínimo para o framework funcionar são as chaves de API, o `VECTOR_STORE` e o `EMBEDDINGS`. Os demais (`CACHE`, `BACKUP`, `EVALUATION`, `MULTITENANCY`, etc.) têm valores-padrão sensatos e só precisam ser declarados se o dev quiser mudar o comportamento padrão. `BENCHMARK` e `EVALUATION` são coisas distintas: `BENCHMARK` configura a comparação de estratégias sob demanda; `EVALUATION` configura o monitoramento contínuo das queries reais em produção (ambos detalhados no arquivo de avaliação).

O framework lê esse arquivo via uma variável de ambiente que aponta para ele, exatamente como o Django faz:

```bash
export RAG_SETTINGS=meu_projeto.rag_settings
```

---

## Estrutura de pastas

```
busca-ai/
│
├── busca_ai/                       ← pacote principal
│   │
│   ├── api/                        ← camada HTTP (FastAPI)
│   │   ├── routes/
│   │   │   ├── auth.py
│   │   │   ├── ingest.py
│   │   │   ├── search.py
│   │   │   ├── chat.py
│   │   │   ├── documents.py
│   │   │   ├── benchmark.py
│   │   │   ├── admin.py
│   │   │   └── backup.py
│   │   ├── middlewares.py          ← auth, rate limit, cors
│   │   └── server.py
│   │
│   ├── ingestion/                  ← pipeline de entrada
│   │   ├── loaders/                ← pdf, csv, sql
│   │   ├── chunking/               ← recursive, semantic, markdown, code
│   │   └── graph.py                ← grafo LangGraph de ingestão
│   │
│   ├── retrieval/                  ← pipeline de busca
│   │   ├── embeddings/             ← openai, cohere, local
│   │   ├── prefilter/              ← pré-filtragem léxica (BM25, índice invertido)
│   │   ├── strategies/             ← dense, sparse, hybrid
│   │   ├── reranker/               ← cohere, cross_encoder
│   │   └── graph.py                ← grafo LangGraph de busca
│   │
│   ├── vectorstore/                ← abstração do banco vetorial
│   │   ├── base.py                 ← interface comum
│   │   └── qdrant.py
│   │
│   ├── sources/                    ← conectores de origem de dados
│   │   ├── postgresql.py
│   │   └── mysql.py
│   │  
│   │
│   ├── scheduler/                  ← ingestão agendada
│   ├── cache/                      ← cache de queries (redis, memória)
│   ├── backup/                     ← backup incremental + restore
│   ├── eval/                       ← RAGAS, métricas de retrieval
│   ├── observability/              ← logs e métricas
│   └── conf/                       ← carrega e valida o rag_settings.py
│
├── cli/                            ← interface de linha de comando
│   ├── commands/
│   │   ├── init.py / up.py / login.py
│   │   ├── ingest.py / search.py / chat.py
│   │   ├── benchmark.py / backup.py
│   │   ├── status.py / logs.py / users.py
│   └── main.py
│
├── tests/
├── docs/
├── examples/
│   └── rag_settings.example.py     ← template que o dev copia
├── pyproject.toml
├── Dockerfile
└── docker-compose.yml
```

A camada `vectorstore/base.py` define uma **interface comum** — qualquer banco vetorial (Qdrant, Pinecone...) implementa essa interface, então trocar de banco não quebra o resto do código.

---

## A API

Os endpoints, agrupados por função:

```
AUTENTICAÇÃO
POST /auth/login, /auth/refresh, /auth/logout, /auth/register

INGESTÃO
POST /ingest, /ingest/file, /ingest/url, /ingest/text, /ingest/source
GET  /ingest/status/{job_id}, /ingest/history
POST /ingest/cancel/{job_id}

DOCUMENTOS
GET    /documents, /documents/{id}
DELETE /documents/{id}

BUSCA E CHAT
POST /search, /search/batch
POST /chat, /chat/stream

AVALIAÇÃO
POST /benchmark
GET  /benchmark/history

ADMINISTRAÇÃO
GET/POST/PUT/DELETE /admin/users
GET  /admin/logs, /admin/usage

BACKUP
POST   /admin/backup/run, /admin/backup/restore
GET    /admin/backup/history
DELETE /admin/backup/{id}

UTILITÁRIOS
GET /health, /metrics
```

Diferença entre `/search` e `/chat`:
- `/search` retorna os chunks crus recuperados.
- `/chat` busca os chunks, passa para a LLM e retorna uma resposta gerada (com as fontes), suportando histórico de conversa e streaming.

---

## A CLI

A linha de comando é importante para um framework dev-first — o desenvolvedor não precisa abrir um cliente HTTP para nada. A CLI é, por baixo, apenas um cliente HTTP da própria API (nada é duplicado).

```bash
rag init        # cria rag_settings.py, docker-compose.yml, .env
rag up          # sobe o ambiente (docker-compose up)
rag login       # autentica e salva o token

rag ingest --source ./documentos/
rag ingest --source banco_clientes

rag search "qual o prazo de rescisão?"
rag search "qual o prazo?" --filter fonte=contrato.pdf

rag chat "qual o prazo de rescisão?" --stream

rag benchmark --query "prazo de rescisão" \
              --esperado "contrato.pdf:3" \
              --estrategias bm25,dense,hybrid --ragas

rag backup run / restore --data "2024-05-14" / history
rag status      # mostra estado de Qdrant, Redis, Postgres, workers, jobs
rag logs        # logs do sistema
rag users list / create / delete
```

O comando `rag` fica disponível automaticamente quando o pacote é instalado, via configuração no `pyproject.toml`:

```toml
[project.scripts]
rag = "cli.main:main"
```

---

## Subindo tudo: docker-compose

O desenvolvedor sobe o sistema inteiro com um comando. O `docker-compose.yml` orquestra todos os serviços:

```yaml
services:
  api:       # a API FastAPI
  worker:    # os workers Celery que processam ingestões
  qdrant:    # o banco vetorial
  redis:     # fila de tarefas + cache
```

```bash
docker-compose up    # sistema inteiro no ar
```

---

## Como o desenvolvedor usa, do zero

```bash
# 1. instala
pip install busca-ai

# 2. inicializa o projeto
rag init

# 3. preenche o rag_settings.py e o .env

# 4. sobe o ambiente
rag up

# 5. ingere dados
rag ingest --source ./documentos/

# 6. busca
rag search "qual o prazo de rescisão?"
```

Ou consumindo a API diretamente de outra aplicação:

```python
import httpx
resp = httpx.post("http://localhost:8000/chat",
                  json={"query": "qual o prazo de rescisão?"},
                  headers={"Authorization": f"Bearer {token}"})
```
