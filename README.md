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

### Setup em 4 comandos

```bash
# 1. inicializa o projeto
rag init

# 2. preenche as chaves de API no .env
echo "OPENAI_API_KEY=sk-..." >> .env

# 3. sobe o ambiente (Qdrant, Redis, Postgres)
rag up

# 4. ingere seus documentos
rag ingest --source ./meus-documentos/
```

### Primeira busca

```bash
rag search "qual o prazo de rescisão contratual?"
```

```
[1] score: 0.97 | contrato.pdf · página 3
    "O contrato pode ser rescindido em 30 dias mediante
     aviso prévio por escrito..."

[2] score: 0.91 | contrato.pdf · página 4
    "O aviso prévio deve ser entregue por meio físico
     ou eletrônico com confirmação de recebimento..."
```

### Chat via API

```bash
curl -X POST http://localhost:8000/chat \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "qual o prazo de rescisão?",
    "stream": false
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
│  Streaming de tokens · Histórico visível · Fontes citadas   │               
│  Acesso: http://localhost:3000                              │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                        API REST                             │
│                                                             │
│  POST /search · POST /chat · POST /ingest · ...             │
│  Controle total · Qualquer linguagem                        │
│  Para: desenvolvedor integrando o BuscaAI em outra app      │
│  Acesso: http://localhost:8000                              │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                          CLI                                │
│                                                             │
│  OPERAÇÃO                    TESTE E PESQUISA               │
│  rag ingest                  rag search "query"             │
│  rag backup                  rag chat  (sessão interativa)  │
│  rag status                                                 │
│  rag benchmark               Para: dev testando o sistema   │
│                                                             │                             
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
curl -X POST http://localhost:8000/search \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "prazo de rescisão"}'

# chat com geração de resposta
curl -X POST http://localhost:8000/chat \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "prazo de rescisão", "stream": false}'
```

### CLI — terminal para desenvolvedores

Dois modos de uso:

**Operação do sistema** — ingerir dados, fazer backup, monitorar status. São comandos que um desenvolvedor roda para administrar o framework.

**Teste e pesquisa** — `rag search` retorna os chunks recuperados sem geração de resposta (útil para debugar o retrieval). `rag chat` abre uma sessão interativa no próprio terminal, sem streaming, mantendo o histórico durante a sessão.

```bash
# modo busca — retorna chunks, sem LLM
rag search "prazo de rescisão contratual"
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
# modo chat — sessão interativa com histórico
rag chat
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
[chunking adaptativo por tipo]
      ↓
[metadados naturais extraídos]
      ↓
        ┌─────────┴──────────┐
        ↓                    ↓
[embedding denso]   [embedding esparso (SPLADE)]
        ↓                    ↓
        └─────────┬──────────┘
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
  ├── simples      → [pré-filtro] → [busca híbrida]
  ├── multi-entidade → [decomposição] → [pré-filtro] → [busca híbrida]
  └── complexa     → [decomposição] → [loop: busca → verifica → re-busca?]
                                           ↓
                                      [reranker?]
                                           ↓
                                      [LLM gera resposta]  ← só no /chat
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

# ─── Chaves de API ──────────────────────────────
OPENAI_API_KEY    = os.environ.get("OPENAI_API_KEY")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
COHERE_API_KEY    = os.environ.get("COHERE_API_KEY")

# ─── Banco vetorial ─────────────────────────────
VECTOR_STORE = {
    "backend": "qdrant",
    "host": "localhost",
    "port": 6333,
}

# ─── Embeddings ─────────────────────────────────
EMBEDDINGS = {
    "dense":  {"provider": "openai", "model": "text-embedding-3-small"},
    "sparse": {"model": "splade"},
}

# ─── Chunking ───────────────────────────────────
CHUNKING = {
    "strategy":   "recursive",   # recursive | semantic | markdown | code
    "chunk_size": 512,
    "overlap":    50,
}

# ─── Retrieval ──────────────────────────────────
RETRIEVAL = {
    "strategy":     "hybrid",    # bm25 | dense | hybrid
    "top_k":        50,
    "reranker":     True,
    "reranker_model": "cohere",
    "final_top_k":  5,
}

# ─── LLMs ───────────────────────────────────────
LLM = {
    "default": "openai",
    "providers": {
        "openai":    {"model": "gpt-4o-mini",          "temperature": 0.0},
        "anthropic": {"model": "claude-haiku-4-5",     "temperature": 0.0},
        "groq":      {"model": "llama-3.1-8b-instant", "temperature": 0.0},
        "ollama":    {"host": "localhost", "port": 11434, "model": "llama3.2"},
    }
}

# ─── Chat ───────────────────────────────────────
CHAT = {
    "provider":      "openai",
    "system_prompt": "Responda apenas com base nos documentos fornecidos.",
    "historico_max": 10,
    "stream":        False,
}

# ─── Pré-filtragem ──────────────────────────────
PRE_FILTERING = {
    "enabled":  True,
    "strategy": "bm25",
    "top_n":    50000,
}

# ─── Fontes de dados ────────────────────────────
SOURCES = {
    "banco_clientes": {
        "type":  "postgresql",
        "query": "SELECT id, titulo, conteudo FROM artigos",
    },
}

# ─── Autenticação ───────────────────────────────
AUTH = {
    "secret_key":     os.environ.get("SECRET_KEY"),
    "token_expiry":   3600,
    "refresh_expiry": 604800,
}

# ─── Cache ──────────────────────────────────────
CACHE = {"enabled": True, "backend": "redis", "ttl": 3600}

# ─── Backup ─────────────────────────────────────
BACKUP = {
    "qdrant": {
        "enabled":        True,
        "strategy":       "incremental",
        "full_every_days": 7,
        "destination":    {"type": "s3", "bucket": "meu-backup"},
    }
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
POST /auth/register    Cria novo usuário (admin only)
```

### Ingestão

```
POST /ingest                   Ingere da source configurada no settings
POST /ingest/file              Upload e ingestão de arquivo
POST /ingest/url               Ingere de uma URL
POST /ingest/text              Ingere texto direto
GET  /ingest/status/{job_id}   Status e progresso do job
POST /ingest/cancel/{job_id}   Cancela job em andamento
GET  /ingest/history           Histórico de jobs
```

### Busca e chat

```
POST /search           Busca e retorna chunks relevantes
POST /search/batch     Múltiplas queries em uma chamada
POST /chat             Busca + geração de resposta com LLM
POST /chat/stream      Mesmo com streaming
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
GET /health    Status de todos os serviços
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
rag search "qual o prazo de rescisão?"
rag search "qual o prazo?" --filter fonte=contrato.pdf
rag search "artigo 482 CLT" --top-k 10

# chat — sessão interativa no terminal
# mantém histórico durante a sessão, sem streaming
# reformulação automática de query de acompanhamento
rag chat
rag chat --filter fonte=contrato.pdf     # restringe a uma fonte
rag chat --model groq                    # usa um modelo específico
```

**Diferença entre `rag search` e `rag chat`:**

|            | `rag search`          | `rag chat`                 |
| ---------- | --------------------- | -------------------------- |
| Retorna    | chunks crus com score | resposta gerada pelo LLM   |
| Usa LLM    | não                   | sim                        |
| Histórico  | não                   | sim (dentro da sessão)     |
| Streaming  | não                   | não (resultado completo)   |
| Uso típico | debugar o retrieval   | testar o pipeline completo |

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
        "query":    "SELECT id, titulo, conteudo FROM artigos",
    },
    "dados": {
        "type":     "mysql",
        "host":     os.environ.get("MYSQL_HOST"),
        "port":     os.environ.get("MYSQL_PORT"),         
        "name":     os.environ.get("MYSQL_DB"),
        "user":     os.environ.get("MYSQL_USER"),
        "password": os.environ.get("MYSQL_PASSWORD"),
        "query":    "SELECT id, titulo, descricao FROM produtos",
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
| `13-revisao-sistematica-literatura.md`       | Estado da arte 2024–2026                            |
| `15-requisitos-funcionais-nao-funcionais.md` | Requisitos do sistema                               |

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

## Roadmap

- [ ] Suporte a GraphRAG como estratégia opcional
- [ ] Self-RAG e Corrective RAG como modos premium configuráveis
- [ ] Dashboard web de monitoramento
- [ ] Suporte a dados multimodais (imagens, áudio)
- [ ] Integração com Langfuse para observabilidade avançada
- [ ] Benchmarks comparativos publicados

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

Construído com LangGraph · Qdrant · FastAPI · Celery

</div>