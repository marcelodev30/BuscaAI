<div align="center">

# 🔍 BuscaAI

**Framework RAG híbrido e modular para recuperação de informação em grandes bases de dados**

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![LangGraph](https://img.shields.io/badge/LangGraph-latest-FF6B35?style=flat-square)](https://langchain-ai.github.io/langgraph/)
[![Qdrant](https://img.shields.io/badge/Qdrant-latest-DC244C?style=flat-square&logo=qdrant)](https://qdrant.tech)
[![FastAPI](https://img.shields.io/badge/FastAPI-latest-009688?style=flat-square&logo=fastapi)](https://fastapi.tiangolo.com)
[![Docker](https://img.shields.io/badge/Docker-ready-2496ED?style=flat-square&logo=docker&logoColor=white)](https://docker.com)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)

[Início Rápido](#-início-rápido) · [Formas de Interação](#-formas-de-interação) · [Arquitetura](#-arquitetura) · [API](#-api) · [CLI](#-cli) · [Contribuição](#-contribuição)

</div>

---

## O que é o BuscaAI

O **BuscaAI** é um framework de Retrieval-Augmented Generation (RAG) voltado para desenvolvedores que precisam construir sistemas de busca inteligente sobre grandes bases de dados. Ele combina busca semântica e busca lexical num pipeline híbrido orquestrado pelo LangGraph, expondo tudo por uma API REST e uma CLI.

O desenvolvedor configura um arquivo central (`rag_settings.py`), sobe o ambiente com um comando e passa a ter um sistema de recuperação de informação funcionando — sem precisar conhecer os detalhes internos de RAG.

```
rag_settings.py  →  rag up  →  rag ingest  →  rag search "sua query"
```

---

## Por que BuscaAI

| Problema                                     | Como o BuscaAI resolve                                        |
| -------------------------------------------- | ------------------------------------------------------------- |
| Busca vetorial perde termos exatos           | Busca híbrida: denso + esparso + RRF                          |
| Bases gigantescas tornam a busca lenta       | Pré-filtragem léxica reduz o universo antes da busca vetorial |
| Resultados relevantes ficam no meio da lista | Reranker cross-encoder reordena os candidatos                 |
| Ingestão de milhões de docs trava a API      | Processamento assíncrono via Celery com checkpoint e retry    |
| Difícil saber se o RAG está funcionando bem  | Avaliação integrada com RAGAS (4 métricas)                    |
| Trocar de modelo LLM exige refatoração       | Provedores plugáveis via configuração                         |

---

## Funcionalidades

- **Busca híbrida** — BM25 + embedding denso + RRF, com reranker opcional
- **Pré-filtragem léxica** — índice invertido reduz o universo antes da busca vetorial
- **Modular RAG** — pipeline como grafo LangGraph com roteamento condicional por tipo de query
- **Ingestão assíncrona** — Celery + Redis com checkpoint, retry e status em tempo real
- **Multi-source** — PDF, CSV, TXT, Markdown, PostgreSQL, MySQL
- **LLM plugável** — OpenAI, Anthropic, Groq, Gemin, Ollama (configurável por etapa do pipeline)
- **Chat com histórico** — contexto de conversa com reformulação de query e streaming
- **Avaliação RAGAS** — benchmark inline comparando estratégias de busca
- **Backup incremental** — automatizado com checkpoint diário e restauração por data
- **Três formas de interação** — Frontend web, API REST e CLI
- **Observabilidade** — logs estruturados, métricas e alertas configuráveis

---

## Início Rápido

### Pré-requisitos

- Python 3.11+
- Docker e Docker Compose
- Chave de API OpenAI (ou outro provedor configurado)

### Instalação

```bash
pip install busca-ai
```

### Setup em 3 comandos

```bash
# 1. inicializa o projeto
rag init

# 2. sobe o ambiente
rag up

# 3. ingere seus documentos
rag ingest --source ./meus-documentos/
```

### Search via API

```bash
curl -X POST http://localhost:8000/search \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "qual o prazo de rescisão?"
  }'
```

```json
{
  "resposta": "O prazo de rescisão é de 30 dias, conforme a cláusula 8.2...",
  "fontes": [
    { "fonte": "contrato.pdf", "pagina": 3, "score": 0.97 }
  ],
  "tokens_usados": 312,
  "latencia_ms": 847
}
```
---

## Formas de Interação

O BuscaAI oferece três formas de interação, cada uma voltada para um perfil e contexto diferente:

```
┌─────────────────────────────────────────────────────────────┐
│                        FRONTEND                             │
│                                                             │
│  Chatbot web com interface visual                           │
│  · Histórico visível · Fontes citadas                       │               
│  Acesso: http://localhost:3000                              │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                        API REST                             │
│                                                             │
│  POST /search · POST /search/debug · POST /ingest · ...     │
│  Controle total · Qualquer linguagem                        │
│  Para: desenvolvedor integrando o BuscaAI em outra app      │
│  Acesso: http://localhost:8000                              │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                          CLI                                │
│                                                             │
│  OPERAÇÃO                    PESQUISA E TESTE               │
│  rag ingest                  rag search "query"             │
│  rag backup                  rag search "query" --debug     │ 
│  rag status                                                 │
│  rag benchmark                                              │
└─────────────────────────────────────────────────────────────┘
```

### Frontend — chatbot web

Interface visual completa para o usuário final. histórico de conversa visível e exibição das fontes utilizadas. É o protótipo de validação do framework — o ambiente onde as métricas RAGAS são coletadas com usuários reais.

```bash
# sobe o frontend junto com o restante do ambiente
rag up
# acesse http://localhost:3000
```

### API REST 

Para desenvolvedores que precisam incorporar o BuscaAI em outra aplicação. Toda a funcionalidade está disponível via HTTP — ingestão, busca, chat com streaming, avaliação.

```bash
# busca retornando chunks crus
curl -X POST http://localhost:8000/search/debug \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "prazo de rescisão"}'

# chat com geração de resposta
curl -X POST http://localhost:8000/search \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "prazo de rescisão"}'
```

### CLI — terminal

Dois modos de uso:

**Operação do sistema** — ingerir dados, fazer backup, monitorar status. São comandos que um desenvolvedor roda para administrar o framework.

**Teste e pesquisa** — `rag search --debug` retorna os chunks recuperados sem geração de resposta (útil para debugar o retrieval). `rag search` abre uma sessão interativa no próprio terminal, mantendo o histórico durante a sessão.

```bash
# modo busca — retorna chunks, sem LLM
rag search "prazo de rescisão contratual" --debug 
```

```
Resultados para: "prazo de rescisão contratual"
Estratégia: hybrid | Candidatos pré-filtrados: 48.231 | Reranker: ativo
────────────────────────────────────────────────────────────────────────

[1] score: 0.97 | contrato.pdf · página 3
    "O contrato pode ser rescindido em 30 dias mediante
     aviso prévio por escrito..."

[2] score: 0.89 | contrato.pdf · página 4
    "O aviso prévio deve ser entregue por meio físico
     ou eletrônico com confirmação de recebimento..."
```

```bash
# modo search — sessão interativa com histórico
rag search
```

```
BuscaAI Chat — digite sua pergunta ou 'sair' para encerrar.
Estratégia: hybrid | Reranker: ativo | Modelo: gpt-4o-mini
──────────────────────────────────────────────────────────────

Você: qual o prazo de rescisão contratual?

⠿ buscando...

BuscaAI:
O prazo de rescisão é de 30 dias mediante aviso prévio por
escrito, conforme a cláusula 8.2 do contrato.

Fontes:
  [1] contrato.pdf · pág. 3 · score: 0.97
  [2] contrato.pdf · pág. 4 · score: 0.89

──────────────────────────────────────────────────────────────

Você: e qual a multa?

⠿ buscando...

BuscaAI:
A multa por descumprimento do prazo de rescisão é de 10% do
valor total do contrato, conforme a cláusula 9.1.

Fontes:
  [1] contrato.pdf · pág. 7 · score: 0.94

──────────────────────────────────────────────────────────────

Você: sair

Encerrando sessão.
```

O histórico é mantido **dentro da sessão** — a reformulação automática de query garante que "e qual a multa?" encontre os chunks corretos mesmo sendo uma query de acompanhamento. O histórico não persiste entre sessões; para persistência, use a API ou o frontend.

---

## Arquitetura

O BuscaAI é um **Modular RAG** orquestrado pelo LangGraph. Cada etapa do pipeline é um nó do grafo; as decisões (reranker sim/não, tipo de query, re-busca) são arestas condicionais.

### Fluxo de ingestão

```
fontes de dados
      ↓
[chunking]
      ↓
[metadados naturais extraídos]
                ↓
        ┌───────────────────┐
        ↓                   ↓
[embedding denso]   [embedding esparso]
        ↓                   ↓
        └───────────────────┘
                ↓
[Qdrant + índice invertido BM25]
```

### Fluxo de busca

```
query
  ↓
[cache?] ──sim──→ [retorna do cache]
  ↓ não
[classificar query]
  ↓
  ├── Simples  → [pré-filtro] → [busca híbrida] → [LLM gera resposta]
  ├── MÉDIA    → [pré-filtro] → [busca] → [reranker] → [LLM gera resposta]
  └── Multi-entidade → [decomposição] → [pré-filtro] → [busca híbrida] → [reranker] → [LLM gera resposta]
                                       
                                    
```

### Stack tecnológica

| Camada              | Tecnologia                                         |
| ------------------- | -------------------------------------------------- |
| Orquestração        | LangGraph                                          |
| Banco vetorial      | Qdrant                                             |
| Pré-filtragem       | BM25 / índice invertido                            |
| Fusão de resultados | RRF (Reciprocal Rank Fusion)                       |
| Embeddings          | OpenAI / Cohere / HuggingFace / FastEmbed (SPLADE) |
| LLM                 | OpenAI / Anthropic / Groq / Ollama                 |
| API                 | FastAPI                                            |
| Fila de tarefas     | Celery + Redis                                     |
| Banco de controle   | PostgreSQL                                         |
| Cache               | Redis                                              |
| Avaliação           | RAGAS                                              |
| CLI                 | Click                                              |
| Containers          | Docker Compose                                     |

---

## Configuração

Toda a configuração fica em um único arquivo `rag_settings.py`, inspirado no `settings.py` do Django.

```python
# rag_settings.py
import os

# ════════════════════════════════════════════════════════════
# CHAVES DE API — sempre via variável de ambiente
# ════════════════════════════════════════════════════════════

OPENAI_API_KEY    = os.environ.get("OPENAI_API_KEY")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
GOOGLE_API_KEY    = os.environ.get("GOOGLE_API_KEY")
GROQ_API_KEY      = os.environ.get("GROQ_API_KEY")
COHERE_API_KEY    = os.environ.get("COHERE_API_KEY")
VOYAGE_API_KEY    = os.environ.get("VOYAGE_API_KEY")

# ════════════════════════════════════════════════════════════
# BANCO VETORIAL
# ════════════════════════════════════════════════════════════
#
# backend: qdrant | pgvector | chroma | pinecone
#
#   qdrant   → padrão, melhor para produção, suporta híbrido nativo
#   pgvector → use se já tem Postgres e a base é pequena (<10M chunks)
#   chroma   → use para POC e desenvolvimento local (embedded)
#   pinecone → use se não quer gerenciar infra (cloud gerenciado)

VECTOR_STORE = {
    "backend": "qdrant",
    "host":    os.environ.get("QDRANT_HOST", "localhost"),
    "port":    int(os.environ.get("QDRANT_PORT", 6333)),
    "collection": "buscaai",

    # Configurações de performance
    "hnsw_m":           16,     # conexões por nó no grafo HNSW
                                # maior = mais qualidade, mais RAM
    "hnsw_ef":          128,    # profundidade de busca
                                # maior = mais preciso, mais lento
    "quantization":     False,  # True economiza RAM (~4x), perde ~5% qualidade
    "on_disk":          False,  # True para bases muito grandes (troca RAM por disco)
}

# ════════════════════════════════════════════════════════════
# EMBEDDINGS
# ════════════════════════════════════════════════════════════
#
# Embedding denso — captura significado semântico
#   provider: openai | cohere | voyage | local
#
#   openai / text-embedding-3-small  → $0.02/1M tokens, 1536 dim, padrão
#   openai / text-embedding-3-large  → $0.13/1M tokens, 3072 dim, mais preciso
#   cohere / embed-multilingual-v3   → $0.10/1M tokens, multilíngue forte
#   voyage / voyage-4-lite           → $0.02/1M tokens, contexto 32K
#   local  / BAAI/bge-m3             → gratuito, ~2GB RAM, top open-source
#   local  / all-MiniLM-L6-v2        → gratuito, ~80MB, bom para POC
#
# Embedding esparso — captura termos exatos (BM25 neural)
#   splade   → melhor qualidade, requer FastEmbed
#   bm25     → fallback simples, zero dependência extra

EMBEDDINGS = {
    "dense": {
        "provider":  "openai",
        "model":     "text-embedding-3-small",
        "dimension": 1536,
        "batch_size": 100,      # chunks por chamada de API
    },
    "sparse": {
        "model":     "splade",  # splade | bm25
    },
}

# ════════════════════════════════════════════════════════════
# CHUNKING
# ════════════════════════════════════════════════════════════
#
# strategy: recursive | semantic | markdown | auto
#
#   recursive  → padrão, divide por parágrafo > frase > palavra
#   semantic   → divide por mudança de significado (mais caro)
#   markdown   → respeita cabeçalhos #, ## e listas
#   auto       → detecta o tipo do arquivo e aplica a estratégia certa

CHUNKING = {
    "strategy":   "auto",       # recomendado: auto para bases mistas
    "chunk_size": 512,          # tokens por chunk
    "overlap":    50,           # tokens de sobreposição entre chunks, overlap alto = melhor contexto nas bordas, mais chunks redundantes

    # Sobrescreve a estratégia por tipo de arquivo
    "per_type": {
        "pdf":      "recursive",
        "markdown": "markdown",
        "csv":      "recursive",
    },
}

# ════════════════════════════════════════════════════════════
# PRÉ-FILTRAGEM LÉXICA
# ════════════════════════════════════════════════════════════
#
# Reduz o universo de busca antes da etapa vetorial.
# Evita buscar em 10M chunks quando só 50k são candidatos válidos.
#
# strategy: bm25 | elasticsearch | opensearch | meilisearch | disabled
#
#   bm25          → índice próprio do BuscaAI, zero dependência extra
#   elasticsearch → use se já tem ES rodando na empresa
#   opensearch    → use para AWS ou licença Apache 2.0 obrigatória
#   meilisearch   → use para hardware fraco ou base até ~10M chunks
#   disabled      → desliga a pré-filtragem (não recomendado em escala)

PRE_FILTERING = {
    "enabled":  True,
    "strategy": "bm25",
    "top_n":    50000,          # candidatos que passam para a busca vetorial
    "language": "pt",           # pt | en | multi
}

# ════════════════════════════════════════════════════════════
# RETRIEVAL
# ════════════════════════════════════════════════════════════
#
# strategy: bm25 | dense | hybrid
#
#   bm25    → só busca lexical, rápido, perde queries semânticas
#   dense   → só busca semântica, perde termos exatos (IDs, códigos)
#   hybrid  → os dois + RRF, melhor resultado geral ← recomendado

RETRIEVAL = {
    "strategy": "hybrid",
    "top_k": 50,           # candidatos que passam para o reranker ou para o LLM se não tiver reranker
    "RRF": True            # RRF — fusão entre busca densa e esparsa                           
    "rrf_k": 60,           # constante de fusão, padrão de mercado
}
# ════════════════════════════════════════════════════════════
# Reranker — reordena os top_k candidatos
# ════════════════════════════════════════════════════════════
#
# model: cohere | voyage | cross-encoder 

#   cohere         → $2/1k buscas, qualidade alta
#   voyage         → primeiros 200M tokens grátis, melhor em benchmarks
#   cross-encoder  → local, gratuito, ~100ms CPU ou ~10ms GPU
#   disabled       → sem reranker

RERANKR={
    "reranker": True,
    "reranker_model": "cross-encoder",  # local é mais barato em volume alto
    "final_top_k": 5,                # chunks que chegam ao LLM
}

# ════════════════════════════════════════════════════════════
# LLMs
# ════════════════════════════════════════════════════════════
#
# Provedores disponíveis para geração de resposta.
# O "default" é usado pelo endpoint /chat quando não especificado.
#
# Preços por 1M tokens (input / output) — maio 2026:
#   openai    gpt-4o-mini        $0.40  / $1.60
#   openai    gpt-4o             $2.50  / $10.00
#   anthropic claude-haiku-4-5   $1.00  / $5.00
#   anthropic claude-sonnet-4-6  $3.00  / $15.00
#   gemini    gemini-2.5-flash   $0.15  / $0.60   ← mais barato
#   groq      llama-3.1-8b       $0.05  / $0.08   ← mais rápido
#   cohere    command-r7b        $0.037 / $0.15   ← ultra barato
#   ollama    qualquer modelo    $0     (local)

LLM = {
    "default": "openai",

    "providers": {
        "openai": {
            "model":       "gpt-4o-mini",
            "temperature": 0.0,
            "max_tokens":  1000,
        },
        "anthropic": {
            "model":       "claude-haiku-4-5",
            "temperature": 0.0,
            "max_tokens":  1000,
        },
        "gemini": {
            "model":       "gemini-2.0-flash",
            "temperature": 0.0,
            "max_tokens":  1000,
        },
        "groq": {
            "model":       "llama-3.1-8b-instant",
            "temperature": 0.0,
            "max_tokens":  1000,
        },
        "cohere": {
            "model":       "command-r7b",
            "temperature": 0.0,
            "max_tokens":  1000,
        },
        "ollama": {
            "host":        os.environ.get("OLLAMA_HOST", "localhost"),
            "port":        int(os.environ.get("OLLAMA_PORT", 11434)),
            "model":       "llama3.2",
            "temperature": 0.0,
        },
    },

    # Roteamento por complexidade de query
    # Economiza 60-80% do custo usando modelos baratos para queries simples
    "routing": {
        "enabled": False,       # True para ativar o roteamento
        "simple":  "groq",      # queries de uma etapa
        "medium":  "openai",    # queries que precisam de raciocínio
        "complex": "anthropic", # queries multi-hop ou muito longas
    },
}

# ════════════════════════════════════════════════════════════
# CHAT
# ════════════════════════════════════════════════════════════

CHAT = {
    "provider": "openai",  # qual provider do bloco LLM usar
    "system_prompt": (
        "Você é um assistente especializado. "
        "Responda apenas com base nos documentos fornecidos. "
        "Se a resposta não estiver nos documentos, diga que não sabe."
    ),
    "historico_max": 10,        # número de turnos anteriores enviados ao LLM
}

# ════════════════════════════════════════════════════════════
# FUNCIONALIDADES LLM OPCIONAIS
# ════════════════════════════════════════════════════════════
#
# Cada funcionalidade adiciona uma chamada de LLM por query.
# Habilite apenas o que agrega valor real para o seu caso.

LLM_FEATURES = {
    # Query expansion — gera sinônimos antes de buscar
    # Ajuda quando o vocabulário do usuário difere dos documentos
    "query_expansion": {
        "enabled":  False,
        "provider": "groq",
    },

    # Reformulação de query de acompanhamento
    # ex: "e qual a multa?" → "qual a multa por rescisão contratual?"
    "reformulacao": {
        "enabled":  False,
        "provider": "groq",     # usa modelo barato para reformular
    },

    # Reranker via LLM — mais caro que cross-encoder, mais preciso
    "llm_reranker": {
        "enabled":  False,
        "provider": "groq",
    },
}

# ════════════════════════════════════════════════════════════
# FONTES DE DADOS
# ════════════════════════════════════════════════════════════
#
# Cada chave é um nome de source que o dev passa para `rag ingest`.
# Credenciais SEMPRE via variável de ambiente, nunca hardcoded.
#
# type: postgresql | mysql | sqlite | csv | json | api

SOURCES = {

    "artigos": {
        "type":     "postgresql",
        "host":     os.environ.get("SOURCE_PG_HOST", "localhost"),
        "port":     int(os.environ.get("SOURCE_PG_PORT", 5432)),
        "name":     os.environ.get("SOURCE_PG_DB"),
        "user":     os.environ.get("SOURCE_PG_USER"),
        "password": os.environ.get("SOURCE_PG_PASSWORD"),
    },

    "produtos": {
        "type":     "mysql",
        "host":     os.environ.get("SOURCE_MYSQL_HOST", "localhost"),
        "port":     int(os.environ.get("SOURCE_MYSQL_PORT", 3306)),
        "name":     os.environ.get("SOURCE_MYSQL_DB"),
        "user":     os.environ.get("SOURCE_MYSQL_USER"),
        "password": os.environ.get("SOURCE_MYSQL_PASSWORD"),
    },
}

# Agendamento de reingestão automática (cron syntax)
SCHEDULE = {
    "artigos":  "0 2 * * *",    # diariamente às 2h
    "produtos": "0 3 * * 0",    # toda domingo às 3h
}

# ════════════════════════════════════════════════════════════
# AUTENTICAÇÃO
# ════════════════════════════════════════════════════════════

AUTH = {
    "secret_key":     os.environ.get("SECRET_KEY"),
    "token_expiry":   3600,         # access token: 1 hora
    "refresh_expiry": 604800,       # refresh token: 7 dias
    "algorithm":      "HS256",

    # Rate limiting por papel
    "rate_limits": {
        "reader": {"search": "100/minute", "chat": "50/minute"},
        "editor": {"search": "200/minute", "chat": "100/minute", "ingest": "10/hour"},
        "admin":  {"search": "500/minute", "chat": "200/minute", "ingest": "100/hour"},
    },
}

# ════════════════════════════════════════════════════════════
# CACHE
# ════════════════════════════════════════════════════════════
#
#   redis    → produção, persiste entre restarts, compartilhado entre workers
#   disabled → sem cache

CACHE = {
    "enabled": True,
    "host":    os.environ.get("REDIS_HOST", "localhost"),
    "port":    int(os.environ.get("REDIS_PORT", 6379)),
    "ttl":     3600,            # segundos até expirar (1 hora)
    "max_size": 10000,          # máximo de queries cacheadas
}

# ════════════════════════════════════════════════════════════
# BACKUP
# ════════════════════════════════════════════════════════════
#
# destination.type: local 
#
#   local → salva em disco, bom para desenvolvimento
#   s3    → produção, durável, exige AWS_ACCESS_KEY_ID no .env

BACKUP = {
    "qdrant": {
        "enabled": True,
        "strategy": "incremental",  # incremental | full
        "full_every_days": 7,
        "schedule": "1",            # diário às 1h
        "retention_days":  30,
        "destination": {
            "type":   "local",
            "path":   "/var/backups/buscaai/qdrant",
            # Para S3, troque por:
            # "type":   "s3",
            # "bucket": os.environ.get("BACKUP_S3_BUCKET"),
            # "prefix": "buscaai/qdrant",
        },
    },
    "postgres": {
        "enabled": True,
        "schedule": "2",     # diário às 2h
        "retention_days": 30,
        "destination": {
            "type": "local",
            "path": "/var/backups/buscaai/postgres",
        },
    },
}

# ════════════════════════════════════════════════════════════
# LIMITES OPERACIONAIS
# ════════════════════════════════════════════════════════════
#
# Protege o sistema contra arquivos gigantes,
# queries abusivas e jobs que nunca terminam.

LIMITS = {
    "max_file_size_mb":      100,       # arquivos maiores são rejeitados
    "max_chunks_per_doc":    10000,     # documentos que geram mais são truncados
    "max_query_length":      2000,      # chars — queries maiores são truncadas
    "search_timeout_sec":    30,        # timeout da busca completa
    "ingest_timeout_sec":    3600,      # timeout de um job de ingestão
    "max_ingest_retries":    3,         # tentativas antes de marcar como falha
    "checkpoint_every":      1000,      # salva progresso a cada N chunks
}

# ════════════════════════════════════════════════════════════
# OBSERVABILIDADE
# ════════════════════════════════════════════════════════════

OBSERVABILITY = {
    "log_level":   "INFO",              # DEBUG | INFO | WARNING | ERROR
    "log_format":  "json",              # json | text
    "log_queries": True,                # registra cada query no banco

    # Alertas automáticos
    "alerts": {
        "score_minimo":    0.5,         # alerta se score médio cair abaixo disso
        "latencia_max_ms": 2000,        # alerta se p95 ultrapassar isso
        "email":           os.environ.get("ALERT_EMAIL"),
    },
}
```

Aponte para o arquivo via variável de ambiente:

```bash
export RAG_SETTINGS=meu_projeto.rag_settings
```

---

## API

A API expõe os seguintes grupos de endpoints:

### Autenticação

```
POST /auth/login       Autentica e retorna access + refresh token
POST /auth/refresh     Renova o access token
POST /auth/logout      Invalida o token
POST /auth/register    Cria novo usuário 
```

### Ingestão

```
POST /ingest/database          Ingere da source configurada no settings
POST /ingest/file              Upload e ingestão de arquivo
POST /ingest/url               Ingere de uma URL
POST /ingest/text              Ingere texto direto
GET  /ingest/status/{job_id}   Status e progresso do job
POST /ingest/cancel/{job_id}   Cancela job em andamento
GET  /ingest/history           Histórico de jobs
```

### Busca

```
POST /search           Busca + geração de resposta com LLM
POST /search/stream    Mesmo com streaming
POST /search/debug     Busca e retorna chunks relevantes
```

### Documentos

```
GET    /documents          Lista documentos ingeridos
GET    /documents/{id}     Detalhes de um documento
DELETE /documents/{id}     Remove documento e seus chunks
```

### Avaliação

```
POST /benchmark            Avalia pipeline com RAGAS
GET  /benchmark/history    Histórico de avaliações
```

### Administração

```
GET/POST/PUT/DELETE /admin/users     Gerencia usuários
GET  /admin/logs                     Logs do sistema
GET  /admin/usage                    Consumo de tokens e recursos

POST   /admin/backup/run             Dispara backup imediato
GET    /admin/backup/history         Lista backups disponíveis
POST   /admin/backup/restore         Restaura de um ponto
DELETE /admin/backup/{id}            Remove backup antigo
```

### Utilitários

```
GET /status    Status de todos os serviços
GET /metrics   Métricas agregadas (latência, cache hit, scores)
```

---

## CLI

A CLI é dividida em dois grupos com propósitos distintos.

### Operação do sistema

Comandos para administrar o framework — ingerir dados, monitorar, fazer backup, gerenciar usuários.

```bash
# setup
rag init                                  # inicializa o projeto com templates
rag up                                    # sobe o ambiente (docker-compose)

# ingestão
rag ingest --source ./documentos/         # ingere um diretório
rag ingest --source banco_clientes        # ingere de source do settings
rag ingest status {job_id}                # acompanha o job
rag ingest cancel {job_id}               # cancela se necessário

# backup
rag backup run                            # dispara backup imediato
rag backup restore --data "2024-05-14"    # restaura de uma data
rag backup history                        # lista backups disponíveis

# monitoramento
rag status                                # estado de todos os serviços
rag logs                                  # logs em tempo real
rag logs --filter erro                    # filtra só erros
rag logs --tail 100                       # últimas 100 linhas

# avaliação
rag benchmark \
  --query "prazo de rescisão" \
  --esperado "contrato.pdf:3" \
  --estrategias bm25,dense,hybrid \
  --ragas
```

### Teste e pesquisa

Comandos para o desenvolvedor testar o sistema e pesquisar na base sem abrir o browser ou o Postman.

```bash
# busca — retorna os chunks recuperados, sem geração de resposta
# útil para debugar o retrieval e avaliar a qualidade da busca
rag search "qual o prazo de rescisão?" --debug 
rag search "qual o prazo?" --debug --filter fonte=contrato.pdf
rag search "artigo 482 CLT" --debug --top-k 10

# chat — sessão interativa no terminal
# mantém histórico durante a sessão, sem streaming
rag search 
rag search --filter fonte=contrato.pdf     # restringe a uma fonte
rag search --model groq                    # usa um modelo específico
```

---

## Estrutura do projeto

```
busca-ai/
│
├── busca_ai/                      # pacote principal
│   ├── api/                       # camada HTTP (FastAPI)
│   │   ├── routes/                # auth, ingest, search, chat, ...
│   │   ├── middlewares.py         # JWT, rate limit, CORS
│   │   └── server.py
│   │
│   ├── ingestion/                 # pipeline de entrada
│   │   ├── loaders/               # pdf, csv, sql ...
│   │   ├── chunking/              # recursive, semantic, markdown
│   │   └── graph.py               # grafo LangGraph de ingestão
│   │
│   ├── retrieval/                 # pipeline de busca
│   │   ├── prefilter/             # BM25 / índice invertido
│   │   ├── embeddings/            # openai, cohere, local
│   │   ├── strategies/            # dense, sparse, hybrid
│   │   ├── reranker/              # cohere, cross_encoder
│   │   └── graph.py               # grafo LangGraph de busca
│   │
│   ├── generation/                # geração de resposta com LLM
│   ├── vectorstore/               # abstração do Qdrant
│   ├── sources/                   # conectores de fontes externas
│   ├── scheduler/                 # ingestão assíncrona (Celery)
│   ├── cache/                     # Redis cache
│   ├── backup/                    # backup incremental
│   ├── eval/                      # RAGAS e métricas
│   ├── observability/             # logs e métricas
│   └── conf/                      # carrega e valida o rag_settings.py
│
├── cli/                           # interface de linha de comando
├── tests/                         # testes unitários e de integração
├── docs/                          # documentação adicional
├── examples/
│   └── rag_settings.example.py    # template de configuração
│
├── pyproject.toml
├── Dockerfile
└── docker-compose.yml
```

---

## Exemplos de uso

### Busca simples via Python

```python
from busca_ai import RAGPipeline

pipeline = RAGPipeline()

# ingere um diretório
pipeline.ingest(source="./contratos/")

# faz uma busca
resultados = pipeline.search("qual o prazo de rescisão?")

for doc in resultados:
    print(f"[{doc['score']:.2f}] {doc['fonte']} — {doc['texto'][:100]}...")
```

### Chat com histórico

```python
historico = []

while True:
    query = input("Você: ")

    resposta = pipeline.chat(
        query=query,
        historico=historico
    )

    print(f"BuscaAI: {resposta['resposta']}")
    print(f"Fontes: {[f['fonte'] for f in resposta['fontes']]}\n")

    historico.append({"role": "user",      "content": query})
    historico.append({"role": "assistant", "content": resposta["resposta"]})
```

### Avaliação com RAGAS via API

```python
import httpx

resposta = httpx.post("http://localhost:8000/benchmark",
    headers={"Authorization": f"Bearer {token}"},
    json={
        "queries": [
            {
                "query": "qual o prazo de rescisão?",
                "documentos_esperados": ["contrato.pdf:3"],
                "resposta_esperada": "30 dias com aviso prévio"
            }
        ],
        "estrategias": ["bm25", "dense", "hybrid"],
        "incluir_ragas": True
    }
)

resultado = resposta.json()
print(f"Melhor estratégia: {resultado['recomendacao']['estrategia']}")
print(f"Hybrid Faithfulness: {resultado['resultados']['hybrid']['ragas']['faithfulness']:.2f}")
```

### Ingestão de banco SQL

```python
# rag_settings.py
SOURCES = {                       
    "artigos": {
        "type":     "postgresql",
        "host":     os.environ.get("POSTGRES_HOST"),
        "port":     os.environ.get("POSTGRES_PORT"),         
        "name":     os.environ.get("POSTGRES_DB"),
        "user":     os.environ.get("POSTGRES_USER"),
        "password": os.environ.get("POSTGRES_PASSWORD"),   
    },
    "dados": {
        "type":     "mysql",
        "host":     os.environ.get("MYSQL_HOST"),
        "port":     os.environ.get("MYSQL_PORT"),         
        "name":     os.environ.get("MYSQL_DB"),
        "user":     os.environ.get("MYSQL_USER"),
        "password": os.environ.get("MYSQL_PASSWORD"),
    },
}
```

```bash
rag ingest --source artigos
```

---

## Desempenho

Benchmarks realizados em hardware de referência (8 vCPUs, 32 GB RAM, SSD NVMe):

| Métrica                                      | Valor                  |
| -------------------------------------------- | ---------------------- |
| Latência p95 — busca sem reranker            | ≤ 500ms                |
| Latência p95 — busca com reranker            | ≤ 1.500ms              |
| Latência p95 — primeiro token (/chat stream) | ≤ 1.000ms              |
| Throughput                                   | 50 queries simultâneas |
| Escala testada                               | até 50M chunks         |
| Recall@5 (busca híbrida)                     | ≥ 0.80                 |
| Faithfulness RAGAS                           | ≥ 0.85                 |

---

## Desenvolvimento

### Configurar ambiente de desenvolvimento

```bash
# clonar o repositório
git clone https://github.com/seu-usuario/busca-ai.git
cd busca-ai

# criar ambiente virtual
python -m venv .venv
source .venv/bin/activate          # Linux/macOS
.venv\Scripts\activate             # Windows

# instalar dependências de desenvolvimento
pip install -e ".[dev]"

# subir serviços de desenvolvimento
docker-compose -f docker-compose.dev.yml up -d
```

### Rodar os testes

```bash
# todos os testes
pytest

# com cobertura
pytest --cov=busca_ai --cov-report=html

# só testes unitários (sem serviços externos)
pytest tests/unit/

# só testes de integração
pytest tests/integration/
```

### Adicionar um loader customizado

```python
# meu_projeto/loaders/meu_loader.py
from busca_ai.ingestion.loaders.base import BaseLoader
from busca_ai.ingestion.loaders.base import Document

class MeuLoader(BaseLoader):
    def load(self, source: str) -> list[Document]:
        # implemente aqui
        return [Document(texto="...", metadados={"fonte": source})]
```

```python
# rag_settings.py
CUSTOM_LOADERS = {
    "meu_formato": "meu_projeto.loaders.meu_loader.MeuLoader"
}
```

---

## Documentação completa

O repositório inclui documentação detalhada em `docs/`:

| Arquivo                                      | Conteúdo                                            |
| -------------------------------------------- | --------------------------------------------------- |
| `01-conceitos-fundamentais.md`               | RAG, embeddings, BM25, banco vetorial               |
| `02-estrategias-de-busca.md`                 | Densa, esparsa, híbrida, HNSW, pré-filtragem        |
| `03-estrategias-de-rag.md`                   | Modular, Hybrid, Adaptive, Graph RAG                |
| `04-chunking.md`                             | Estratégias de chunking                             |
| `05-langgraph.md`                            | Grafos de execução, estado, arestas condicionais    |
| `06-decisoes-e-tradeoffs.md`                 | Decisões de arquitetura com justificativas          |
| `07-arquitetura-do-framework.md`             | Visão geral, settings, estrutura                    |
| `08-operacao.md`                             | Ingestão assíncrona, atualização, backup, segurança |
| `09-avaliacao.md`                            | RAGAS e métricas de retrieval                       |                      
               
---

## Contribuição

Contribuições são bem-vindas. Por favor, siga o processo:

1. Fork o repositório
2. Crie um branch para sua feature (`git checkout -b feature/minha-feature`)
3. Escreva testes para as mudanças
4. Certifique-se que todos os testes passam (`pytest`)
5. Abra um Pull Request descrevendo o que foi feito

### Diretrizes

- Siga o estilo de código do projeto (configurado no `pyproject.toml`)
- Novos módulos devem implementar a interface base correspondente
- Mudanças de comportamento devem ser refletidas na documentação
- PRs sem testes não serão aceitos

---

## Licença

Distribuído sob a licença MIT. Veja [LICENSE](LICENSE) para mais informações.

---

## Citação

Se você usar o BuscaAI em sua pesquisa, por favor cite:

```bibtex
@software{buscaai2024,
  title  = {BuscaAI: Framework RAG Híbrido e Modular para Recuperação de Informação em Grandes Bases de Dados},
  year   = {2024},
  url    = {https://github.com/seu-usuario/busca-ai}
}
```

---

<div align="center">

Construído com LangGraph · Qdrant · FastAPI 

</div>