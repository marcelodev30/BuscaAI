# Requisitos Funcionais e Não Funcionais — BuscaAI
**Versão 2.0 — maio 2026**

Documento consolidado derivado da revisão bibliográfica, levantamento tecnológico
e das decisões de arquitetura do projeto BuscaAI. Cada requisito tem origem
rastreável em literatura, benchmark ou decisão técnica documentada.

---

## Sumário

- [Visão geral](#visão-geral)
- [Requisitos Funcionais](#requisitos-funcionais)
  - [Ingestão e indexação](#ingestão-e-indexação-rf-01-a-rf-08)
  - [Retrieval](#retrieval-rf-09-a-rf-14)
  - [Geração e chat](#geração-e-chat-rf-15-a-rf-18)
  - [Operação e infraestrutura](#operação-e-infraestrutura-rf-19-a-rf-26)
  - [Interfaces](#interfaces-rf-27-a-rf-30)
- [Requisitos Não Funcionais](#requisitos-não-funcionais)
  - [Performance](#performance-rnf-01-a-rnf-04)
  - [Qualidade](#qualidade-rnf-05-a-rnf-08)
  - [Segurança](#segurança-rnf-09-a-rnf-11)
  - [Operação](#operação-rnf-12-a-rnf-16)
  - [Arquitetura](#arquitetura-rnf-17-a-rnf-20)
- [Matriz de rastreabilidade](#matriz-de-rastreabilidade)
- [O que está fora do escopo](#o-que-está-fora-do-escopo)

---

## Visão geral

O BuscaAI é um **framework RAG híbrido, modular e genérico** para desenvolvedores.
Fornece pipeline completo de ingestão, busca, geração e operação,
configurável por um único arquivo central (`rag_settings.py`).

```
USUÁRIO DIRETO:     desenvolvedor de software
USUÁRIO FINAL:      pessoa que usa a aplicação construída com o framework
CASO DE USO BASE:   recuperação de informação sobre bases heterogêneas
                    via linguagem natural
PARADIGMA:          Modular RAG (Gao et al. 2024)
```

---

## Requisitos Funcionais

### Ingestão e indexação (RF-01 a RF-08)

---

#### RF-01 — Ingestão de arquivos locais

| Campo | Valor |
|---|---|
| Prioridade | Alta |
| Escopo | MVP |
| Origem | Modular RAG — módulo Indexing |

**O que faz:**
Ingere documentos de múltiplos formatos armazenados localmente
ou em sistemas de arquivos acessíveis.

**Formatos obrigatórios:**
```
PDF     → PyMuPDF — extração página por página com metadados
CSV     → pandas — cada linha vira um documento
TXT     → leitura direta com detecção de encoding
Markdown → mistune — preserva estrutura de cabeçalhos
HTML    → BeautifulSoup4 — remove tags, extrai texto limpo
DOCX    → python-docx — parágrafos e tabelas
PPTX    → python-pptx — slides como documentos separados
JSON    → configura campos via settings
Código  → tree-sitter — respeita funções, classes, imports
```

**Formatos opcionais (roadmap):**
```
XLSX, imagens (OCR via Tesseract), áudio (transcrição)
```

**Comportamento:**
- Detecção automática de tipo por mime-type
- Loader customizado registrável via settings
- Arquivo inválido ou corrompido: erro descritivo, não falha silenciosa
- Limite de tamanho configurável (padrão: 100 MB por arquivo)

**Critério de aceitação:**
Diretório com PDF, CSV, MD e TXT processado sem intervenção manual.
Banco de controle registra chunks gerados por arquivo e status.

---

#### RF-02 — Ingestão de bancos de dados relacionais

| Campo | Valor |
|---|---|
| Prioridade | Alta |
| Escopo | MVP |
| Origem | Requisito operacional — dados corporativos |

**O que faz:**
Conecta a bancos SQL e ingere linhas como documentos,
com query configurável pelo desenvolvedor.

**Bancos suportados:**
```
PostgreSQL  → psycopg2 via SQLAlchemy
MySQL       → mysqlclient via SQLAlchemy
SQL Server  → pyodbc via SQLAlchemy
SQLite      → built-in Python via SQLAlchemy
Oracle      → cx_Oracle via SQLAlchemy (opcional)
```

**Comportamento:**
- Query SELECT configurável em settings
- Paginação automática (cursor-based, 1.000 rows/página)
- Campo `text_field` define qual coluna é o texto principal
- `metadata_fields` define quais colunas viram payload de filtro
- Atualização incremental via `incremental_field` (ex: `updated_at`)
- Credenciais sempre via variável de ambiente, nunca hardcoded

**Critério de aceitação:**
Query `SELECT id, titulo, conteudo FROM artigos WHERE publicado = true`
executada com paginação, gerando um chunk por linha com metadados `id` e `titulo`.

---

#### RF-03 — Ingestão de fontes externas (roadmap)

| Campo | Valor |
|---|---|
| Prioridade | Média |
| Escopo | v1.x |
| Origem | Requisito de mercado |

**O que faz:**
Conectores para serviços de terceiros via API.

**Fontes planejadas:**
```
Amazon S3       → boto3 — varredura de bucket por prefixo
Google Drive    → Drive SDK v3 + OAuth2
Notion          → Notion API oficial
Confluence      → Confluence Cloud REST API
SharePoint      → Microsoft Graph API
GitHub/GitLab   → webhooks de push + API de conteúdo
```

**Critério de aceitação:**
Bucket S3 com PDFs processado com credenciais via IAM Role,
sem AWS keys no código ou settings.

---

#### RF-04 — Estratégias de chunking configuráveis

| Campo | Valor |
|---|---|
| Prioridade | Alta |
| Escopo | MVP |
| Origem | Sarthi et al. 2024, prática de mercado |

**O que faz:**
Divide documentos em chunks com estratégia adaptada ao tipo de conteúdo.

**Estratégias obrigatórias:**
```
recursive   → padrão — divide por §, frase, token
              chunk_size padrão: 512 tokens
              overlap padrão: 50 tokens

markdown    → respeita #, ##, ###, listas e blocos de código
              ideal para wikis, READMEs, documentação

semantic    → usa embedding para detectar mudança de significado
              divide onde o tema muda, não por tamanho
              mais preciso, requer modelo de embedding na ingestão
```

**Estratégia automática (modo `auto`):**
```
PDF/TXT/DOCX  → recursive
Markdown/HTML → markdown
Sem extensão  → recursive (fallback)
```

**Parâmetros configuráveis:**
```
chunk_size:  8 – 4096 tokens
overlap:     0 – 50% do chunk_size
per_type:    estratégia diferente por tipo de arquivo
```

**Critério de aceitação:**
PDF de 50 páginas dividido sem cortar sentenças no meio.
Overlap configurado preserva contexto nas bordas dos chunks.

---

#### RF-05 — Geração de embeddings densos e esparsos

| Campo | Valor |
|---|---|
| Prioridade | Alta |
| Escopo | MVP |
| Origem | Lassance et al. 2023 (hybrid search) |

**O que faz:**
Gera dois tipos de embedding por chunk — denso (semântico) e esparso (léxico).

**Provedores de embedding denso:**
```
Cloud API:
  openai    → text-embedding-3-small ($0.02/1M) — padrão
              text-embedding-3-large ($0.13/1M) — premium
  voyage    → voyage-4-lite ($0.02/1M), voyage-4-large ($0.12/1M)
  cohere    → embed-v3-multilingual ($0.10/1M)
  google    → text-embedding-005 ($0.006/1M) — mais barato
  amazon    → titan-embed-v2 ($0.02/1M)

Self-hosted:
  local     → BAAI/bge-m3 (denso + esparso unificado, Apache 2.0)
              dimensão: 1024, contexto: 8K, 100+ idiomas
  local     → all-MiniLM-L6-v2 (leve, 80MB, inglês, POC)
  local     → nomic-embed-text-v1.5 (500MB, 8K contexto)
  huggingface → qualquer modelo do Hub via model_name
```

**Embedding esparso:**
```
splade   → SPLADE++ via FastEmbed — padrão (melhor qualidade)
bm25     → índice invertido clássico — fallback sem GPU
bge-m3-sparse → gerado pelo BGE-M3 junto ao denso
```

**Comportamento:**
- Batch de 100 chunks por chamada de API (configurável)
- Retry com backoff exponencial (3 tentativas, padrão)
- Custo rastreado por chunk no banco de controle
- Suporte a Matryoshka (dimensão reduzível sem re-indexar)

**Critério de aceitação:**
100 chunks processados → Qdrant contém vetor denso + esparso por chunk_id.
Falha na API → retry automático e log de erro sem interromper ingestão.

---

#### RF-06 — Deduplicação e atualização incremental

| Campo | Valor |
|---|---|
| Prioridade | Alta |
| Escopo | MVP |
| Origem | Requisito operacional |

**O que faz:**
Evita reingestão desnecessária e mantém a base atualizada
de forma eficiente.

**Comportamento:**
```
Deduplicação:
  hash SHA-256 do conteúdo gerado na ingestão
  se hash já existe → skip (documento não mudou)
  se hash novo → ingere normalmente
  se hash diferente para mesmo source_id → re-ingere (dado atualizou)

Atualização incremental (SQL):
  campo updated_at > última ingestão → re-ingere apenas os novos
  cursor salvo no PostgreSQL (tabela ingestion_cursors)

Deleção:
  DELETE /documents/{id} → remove chunks do Qdrant, BM25, controle
  mantém hash no controle como "deletado" para evitar re-ingestão
```

**Critério de aceitação:**
Reingestão de base sem mudanças → 0 novos chunks processados.
1 documento alterado → apenas esse documento re-indexado.

---

#### RF-07 — Ingestão assíncrona com fila de tarefas

| Campo | Valor |
|---|---|
| Prioridade | Alta |
| Escopo | MVP |
| Origem | Requisito de volume — bases grandes |

**O que faz:**
Processa ingestões de grande volume em background sem bloquear a API.

**Comportamento:**
```
POST /ingest          → retorna job_id em < 1s, processamento em background
GET /ingest/{job_id}  → status, progresso %, tempo estimado, chunks/s
DELETE /ingest/{job_id} → cancela job em andamento

Estados do job:
  queued → processing → completed | failed | cancelled

Workers: Celery + Redis
Concorrência: configurável (padrão: 4 workers)
```

**Critério de aceitação:**
POST /ingest com 100k docs → resposta em < 1s com job_id.
GET /ingest/{id} atualiza progresso a cada 5 segundos.

---

#### RF-08 — Checkpoint, retry e tolerância a falhas

| Campo | Valor |
|---|---|
| Prioridade | Alta |
| Escopo | MVP |
| Origem | Requisito operacional |

**O que faz:**
Garante que ingestões longas não precisem recomeçar do zero em caso de falha.

**Comportamento:**
```
Checkpoint:
  salvo a cada 1.000 chunks (configurável)
  armazenado no Redis com TTL de 7 dias
  ao reiniciar, retoma do último checkpoint

Retry automático:
  máximo 3 tentativas por job (configurável)
  backoff exponencial: 1s → 2s → 4s
  após 3 falhas → status failed, chunks no log de erros

Dead letter:
  chunks que falharam 3x → tabela ingestion_errors no PostgreSQL
  disponível para reprocessamento manual via CLI
```

**Critério de aceitação:**
Worker interrompido a 60% do processamento → ao reiniciar, retoma do chunk 60%, não do zero.

---

### Retrieval (RF-09 a RF-14)

---

#### RF-09 — Pré-filtragem léxica (BM25)

| Campo | Valor |
|---|---|
| Prioridade | Alta |
| Escopo | MVP |
| Origem | Lassance et al. 2023 — first-stage retrieval |

**O que faz:**
Antes da busca vetorial, aplica BM25 sobre índice invertido
para reduzir o universo de busca.

**Engines suportadas:**
```
bm25          → índice invertido próprio — padrão, zero dependência
meilisearch   → engine Rust leve, 200MB RAM, até 50M docs
opensearch    → Apache 2.0, JVM, escala Lucene, bilhões de docs
elasticsearch → SSPL/AGPL, mais features, bilhões de docs
```

**Comportamento:**
```
top_n:     50.000 candidatos retornados (configurável)
language:  pt | en | multi — afeta stopwords e tokenização
threshold: score mínimo BM25 (configurável, padrão: desabilitado)
```

**Critério de aceitação:**
Base de 1M chunks → pré-filtragem retorna no máximo 50k candidatos.
Latência da pré-filtragem < 30ms em índice próprio.

---

#### RF-10 — Busca híbrida com RRF

| Campo | Valor |
|---|---|
| Prioridade | Alta |
| Escopo | MVP |
| Origem | Cormack et al. 2009 (RRF), Sharma 2025 (hybrid recomendado) |

**O que faz:**
Executa busca densa e esparsa em paralelo, funde os rankings com RRF.

**Estratégias:**
```
hybrid  → BM25 + densa + RRF — padrão recomendado
dense   → só busca semântica
sparse  → só busca lexical
bm25    → BM25 puro sobre índice invertido
```

**Comportamento:**
```
top_k:    50 candidatos para o reranker (configurável)
rrf_k:    60 — constante de fusão RRF (configurável)
filtros:  metadados aplicados via Filtered HNSW no Qdrant
          ex: source="contrato.pdf", data>"2024-01-01"
```

**Critério de aceitação:**
Recall@5 da busca híbrida > Recall@5 da busca densa ou esparsa isoladas,
medido em dataset de avaliação com ground truth.

---

#### RF-11 — Reranking pós-retrieval

| Campo | Valor |
|---|---|
| Prioridade | Média |
| Escopo | MVP (opcional) |
| Origem | Khattab & Zaharia 2020 (ColBERT), Sharma 2025 |

**O que faz:**
Reordena os top-K candidatos com cross-encoder mais preciso.

**Modelos suportados:**
```
cross-encoder   → ms-marco-MiniLM-L-6-v2 — padrão local, Apache 2.0
                  ms-marco-MiniLM-L-12-v2 — melhor qualidade local
                  BAAI/bge-reranker-v2-m3 — multilíngue, PT-BR

cloud API:
  cohere          → rerank-v3.5 ($2/1k buscas)
  voyage          → rerank-2.5 (200M tokens grátis)
  jina            → reranker-v2 ($0.02/1M — mais barato)
  pinecone        → rerank-v0 ($0.08/1M)
```

**Comportamento:**
```
reranker: true/false — ativado via settings
top_k:    50 candidatos entram, final_top_k saem (padrão: 5)
fallback: se reranker falhar → retorna sem reranking (degradação graciosa)
condicional: pode ser ativado só para queries complexas
```

**Critério de aceitação:**
Com reranker ativo: Precision@5 superior ao sem reranker, em dataset de avaliação.
Falha no reranker: resposta retornada sem erro (degradação graciosa).

---

#### RF-13 — Roteamento adaptativo de queries

| Campo | Valor |
|---|---|
| Prioridade | Média |
| Escopo | MVP (leve) |
| Origem | Jeong et al. 2024 (Adaptive RAG) |

**O que faz:**
Direciona cada query para o pipeline mais adequado
evitando custo desnecessário.

**Rotas disponíveis:**
```
llm_direto    → query simples que o LLM responde sem retrieval
rag_padrao    → pipeline híbrido completo
rag_simples   → busca densa sem reranker (queries simples)
sql           → query sobre dados estruturados → SQL direto
web           → query sobre informações recentes (roadmap)
```

**Classificador:**
```
heuristica  → zero custo, baseado em regras (padrão)
llm_barato  → Groq classifica com ~$0.001/query
```

#### RF-14 — Cache de queries

| Campo | Valor |
|---|---|
| Prioridade | Alta |
| Escopo | MVP |
| Origem | Requisito de performance |


**Tipos:**
```
exact       → hash SHA-256 da query — padrão
              hit: mesma query → resposta instantânea em < 3ms

semantic    → similaridade semântica entre queries
              hit: query similar (threshold configurável: 0.95) → cache
              mais caro: requer embedding da query mesmo em hit

dois níveis → L1: memória do processo (< 1ms, 500 queries)
              L2: Redis (2ms, ilimitado)
```

**Invalidação:**
```
ttl:          expiração por tempo (padrão: 1h busca, 30min chat)
versioned:    incrementa versão da base ao indexar novo doc
by_document:  remove chaves que referenciam o doc atualizado
```

**Critério de aceitação:**
Mesma query duas vezes → segunda resposta em < 3ms.
Cache hit rate esperado: 30–60% em chatbots corporativos.

---

### Geração e chat (RF-15 a RF-18)

---

#### RF-15 — Geração de resposta com LLM

| Campo | Valor |
|---|---|
| Prioridade | Alta |
| Escopo | MVP |
| Origem | Lewis et al. 2020 (RAG seminal) |

**O que faz:**
Gera resposta em linguagem natural baseada nos chunks recuperados.

**Provedores suportados:**
```
openai      → gpt-4o-mini ($0.40/$1.60), gpt-4o ($2.50/$10)
anthropic   → claude-haiku-4-5 ($1/$5), claude-sonnet-4-6 ($3/$15)
google      → gemini-2.5-flash ($0.15/$0.60), gemini-2.5-pro ($1.25/$10)
groq        → llama-3.1-8b-instant ($0.05/$0.08) — mais rápido
cohere      → command-r7b ($0.0375/$0.15) — mais barato
ollama      → qualquer modelo GGUF local — zero custo de API
```

**Comportamento:**
```
system_prompt:  configurável pelo desenvolvedor
temperature:    padrão 0.0 (determinístico)
max_tokens:     configurável (padrão: 1.000)
streaming:      suportado via SSE em /chat/stream
citação:        fontes incluídas na resposta (doc_id, título, trecho)
fallback:       se LLM falhar → retorna chunks sem geração
```

**Critério de aceitação:**
Faithfulness (RAGAS) ≥ 0.80 em dataset de avaliação.
Streaming inicia primeiro token em < 1s (TTFT).

---

#### RF-16 — Histórico de conversa

| Campo | Valor |
|---|---|
| Prioridade | Alta |
| Escopo | MVP |
| Origem | Requisito de UX |

**O que faz:**
Mantém contexto da conversa entre turnos, permitindo perguntas de acompanhamento.

**Comportamento:**
```
historico_max:    10 turnos anteriores enviados ao LLM (configurável)
persistência:     salvo no PostgreSQL por session_id
ttl_session:      expiração da sessão (padrão: 24h)
reformulação:     queries de acompanhamento reformuladas antes da busca
sumarização:      quando histórico longo → LLM resume mensagens antigas
                  ativa quando tokens do histórico > 50% do token budget
```

**Critério de aceitação:**
"e qual a multa?" após "qual o prazo de rescisão?" →
busca usa query reformulada com contexto completo.

---

#### RF-17 — Roteamento entre provedores por complexidade

| Campo | Valor |
|---|---|
| Prioridade | Média |
| Escopo | MVP |
| Origem | Requisito de custo — economia 60–80% |

**O que faz:**
Usa modelos baratos para queries simples e modelos premium para queries complexas.

**Comportamento:**
```
routing.enabled: true/false
routing.simple:  "groq"      → queries de uma etapa
routing.medium:  "openai"    → queries com raciocínio
routing.complex: "anthropic" → queries multi-hop ou longas

Classificação: heurística (grátis) ou LLM barato (~$0.001)
```

**Critério de aceitação:**
70% das queries → modelo barato.
Custo total ≤ 40% do custo de usar sempre o modelo premium.

---

#### RF-18 — Avaliação de qualidade com RAGAS

| Campo | Valor |
|---|---|
| Prioridade | Média |
| Escopo | MVP |
| Origem | Es et al. 2024 (RAGAS) |

**O que faz:**
Avalia automaticamente a qualidade do pipeline RAG com métricas padronizadas.

**Métricas calculadas:**
```
Retrieval:
  Recall@5, Precision@5, MRR, NDCG@10, Hit Rate@5

Geração (RAGAS):
  Faithfulness          ≥ 0.80 (meta padrão)
  Answer Relevance      ≥ 0.78
  Context Precision     ≥ 0.75
  Context Recall        ≥ 0.75 (requer ground truth)
  Hallucination Rate    ≤ 0.15
```

**Comportamento:**
```
rag eval --dataset golden.json      → avalia com dataset local
rag eval --auto --n 100             → gera perguntas automaticamente e avalia
GET /eval/latest                    → métricas da última avaliação
POST /eval/run                      → dispara avaliação assíncrona
```

**Critério de aceitação:**
Comando `rag eval` retorna relatório com todas as métricas em < 10min para 100 queries.

---

### Operação e infraestrutura (RF-19 a RF-26)

---

#### RF-19 — Backup automático

| Campo | Valor |
|---|---|
| Prioridade | Alta |
| Escopo | MVP |
| Origem | Requisito operacional |

**O que faz:**
Salva snapshots periódicos do banco vetorial e do banco de controle.

**Comportamento:**
```
Qdrant:
  estratégia:     incremental diário + full semanal
  destino:        local (padrão) ou S3
  retenção:       30 dias
  schedule:       0 1 * * * (1h toda madrugada)

PostgreSQL:
  ferramenta:     pg_dump
  destino:        local ou S3
  schedule:       0 2 * * * (2h toda madrugada)
  retenção:       30 dias

Restauração:
  rag backup restore --date 2026-05-20
```

**Critério de aceitação:**
Backup diário executado automaticamente.
Restauração completa em < 30min para base de 1M vetores.

---

#### RF-20 — Autenticação e autorização

| Campo | Valor |
|---|---|
| Prioridade | Alta |
| Escopo | MVP |
| Origem | Requisito de segurança |

**O que faz:**
Controla acesso à API com JWT e roles.

**Comportamento:**
```
Roles:
  admin   → todos os endpoints incluindo ingestão e configuração
  editor  → busca + ingestão, sem configuração de sistema
  reader  → só busca e chat

JWT:
  access token:  1 hora (configurável)
  refresh token: 7 dias (configurável)
  algoritmo:     HS256
  secret key:    via variável de ambiente SECRET_KEY

Endpoints públicos (sem auth):
  GET /health
  GET /metrics (opcional, configurável)
```

**Critério de aceitação:**
Token expirado → 401 Unauthorized.
Role reader tentando POST /ingest → 403 Forbidden.

---

#### RF-21 — Rate limiting

| Campo | Valor |
|---|---|
| Prioridade | Alta |
| Escopo | MVP |
| Origem | Requisito de segurança e estabilidade |

**O que faz:**
Limita número de requisições por endpoint por usuário.

**Comportamento:**
```
Por role (configurável):
  reader:  100 buscas/min, 50 chats/min
  editor:  200 buscas/min, 100 chats/min, 10 ingestões/hora
  admin:   500 buscas/min, 200 chats/min, 100 ingestões/hora

Resposta ao limite:
  HTTP 429 Too Many Requests
  Header Retry-After com tempo de espera
```

**Critério de aceitação:**
101ª busca do reader em 1 minuto → 429 com Retry-After.

---

#### RF-22 — Agendamento de reingestão

| Campo | Valor |
|---|---|
| Prioridade | Média |
| Escopo | MVP |
| Origem | Requisito operacional |

**O que faz:**
Reindexa fontes automaticamente em períodos configurados.

**Comportamento:**
```
Configuração por source em settings:
  artigos:   "0 2 * * *"   → diariamente às 2h
  produtos:  "0 3 * * 0"   → toda domingo às 3h
  docs:      on_change      → monitora mudanças no diretório

Modo:
  incremental → só re-ingere o que mudou (padrão)
  full        → apaga e reindexa tudo
```

**Critério de aceitação:**
Schedule configurado → ingestão disparada automaticamente no horário.
Log de execução disponível no PostgreSQL.

---

#### RF-23 — Multi-tenancy

| Campo | Valor |
|---|---|
| Prioridade | Baixa |
| Escopo | v1.x |
| Origem | Requisito de produto SaaS |

**O que faz:**
Isola dados de múltiplos clientes na mesma infraestrutura.

**Comportamento:**
```
Isolamento lógico:
  namespace por tenant no Qdrant
  prefixo tenant_id nas chaves Redis
  schema separado no PostgreSQL por tenant (ou tabelas com tenant_id)

Isolamento físico (roadmap):
  Weaviate multi-tenant com storage isolado
  Qdrant collections separadas por tenant
```

**Critério de aceitação:**
Query do tenant A não retorna chunks do tenant B em nenhum cenário.

---

#### RF-24 — Observabilidade e métricas

| Campo | Valor |
|---|---|
| Prioridade | Alta |
| Escopo | MVP |
| Origem | Requisito operacional |

**O que faz:**
Expõe métricas operacionais para monitoramento e diagnóstico.

**Métricas expostas em GET /metrics:**
```
Pipeline:
  queries_total, queries_cache_hit, cache_hit_rate
  latencia_p50, latencia_p95, latencia_p99
  score_medio_retrieval, faithfulness_media

Ingestão:
  docs_ingeridos_total, chunks_total
  tokens_usados_total, custo_total_usd
  jobs_em_andamento, jobs_falhos

Sistema:
  qdrant_vetores_total, qdrant_ram_mb
  redis_keys_total, redis_memory_mb
  pg_connections_ativas
```

**Alertas configuráveis:**
```
score_medio < 0.50      → alerta (retrieval degradando)
latencia_p95 > 2000ms   → alerta
faithfulness < 0.70     → alerta
custo_diario > limite   → alerta
```

**Critério de aceitação:**
GET /metrics responde em < 100ms com todas as métricas em formato Prometheus.

---

#### RF-25 — Limites operacionais

| Campo | Valor |
|---|---|
| Prioridade | Alta |
| Escopo | MVP |
| Origem | Requisito de estabilidade |

**O que faz:**
Define limites que protegem o sistema contra abusos e erros operacionais.

**Limites configuráveis:**
```
max_file_size_mb:       100    → arquivos maiores são rejeitados
max_chunks_per_doc:   10.000   → documentos que geram mais são truncados
max_query_length:      2.000   → caracteres — queries maiores truncadas
search_timeout_sec:       30   → timeout da busca completa
ingest_timeout_sec:    3.600   → timeout de um job de ingestão
max_ingest_retries:        3   → tentativas antes de marcar como falha
checkpoint_every:      1.000   → salva progresso a cada N chunks
```

**Critério de aceitação:**
Arquivo de 150MB → HTTP 413 com mensagem descritiva.
Query de 5.000 chars → truncada em 2.000 com aviso no log.

---

#### RF-26 — Configuração centralizada

| Campo | Valor |
|---|---|
| Prioridade | Alta |
| Escopo | MVP |
| Origem | Decisão arquitetural — inspirado no Django settings |

**O que faz:**
Toda configuração do sistema concentrada em um único arquivo Python.

**Comportamento:**
```
Arquivo:    rag_settings.py (qualquer localização)
Ativação:   export RAG_SETTINGS=meu_projeto.rag_settings
Credenciais: SEMPRE via variável de ambiente (os.environ.get)
             NUNCA hardcoded no settings

Blocos configuráveis:
  VECTOR_STORE, EMBEDDINGS, CHUNKING, PRE_FILTERING,
  RETRIEVAL, LLM, CHAT, LLM_FEATURES, SOURCES, SCHEDULE,
  AUTH, CACHE, BACKUP, LIMITS, OBSERVABILITY
```

**Critério de aceitação:**
Trocar banco vetorial de Qdrant para pgvector → uma linha no settings.
Trocar LLM de OpenAI para Groq → uma linha no settings.
Sem alteração de código.

---

### Interfaces (RF-27 a RF-30)

---

#### RF-27 — API REST

| Campo | Valor |
|---|---|
| Prioridade | Alta |
| Escopo | MVP |
| Origem | Requisito de integração |

**Endpoints obrigatórios:**
```
POST /search               → busca sem geração, retorna chunks
POST /chat                 → busca + geração, retorna resposta
GET  /chat/stream          → streaming SSE da geração
POST /ingest               → inicia ingestão assíncrona
GET  /ingest/{job_id}      → status do job
DELETE /ingest/{job_id}    → cancela job
GET  /documents            → lista documentos indexados
DELETE /documents/{id}     → remove documento
GET  /health               → status de saúde dos componentes
GET  /metrics              → métricas Prometheus
POST /auth/token           → gera JWT
POST /auth/refresh         → renova JWT
```

**Especificação:**
- OpenAPI 3.0 gerado automaticamente pelo FastAPI em `/docs`
- Versionamento: `/api/v1/`
- Content-Type: application/json
- Autenticação: Bearer token (JWT)

**Critério de aceitação:**
GET /docs retorna Swagger UI funcional com todos os endpoints.
Curl com token válido → 200. Sem token → 401.

---

#### RF-28 — CLI (Command Line Interface)

| Campo | Valor |
|---|---|
| Prioridade | Alta |
| Escopo | MVP |
| Origem | Requisito de DevX |

**Comandos obrigatórios:**
```
rag ingest --source artigos          → ingere source específico
rag ingest --all                     → ingere todas as sources
rag ingest --all --full              → reingestão completa
rag ingest --status {job_id}         → status do job

rag search "query"                   → busca e exibe chunks
rag chat                             → modo chat interativo no terminal
rag chat --history                   → chat com histórico persistido

rag eval --dataset golden.json       → avaliação com dataset
rag eval --auto --n 100              → gera queries e avalia

rag backup create                    → cria backup imediato
rag backup restore --date 2026-05-20 → restaura backup

rag config validate                  → valida rag_settings.py
rag health                           → status de todos os componentes
```

**Critério de aceitação:**
`rag search "prazo de rescisão"` retorna top-5 chunks formatados em < 500ms.
`rag chat` inicia modo interativo com histórico de conversa.

---

#### RF-29 — Frontend web (chatbot de validação)

| Campo | Valor |
|---|---|
| Prioridade | Média |
| Escopo | MVP |
| Origem | Requisito de validação e demonstração |

**O que faz:**
Interface visual para testar e demonstrar o pipeline.

**Tecnologia:** React + Tailwind CSS + Vite

**Funcionalidades:**
```
Chat:
  janela de conversa com histórico
  streaming de tokens em tempo real
  exibição das fontes usadas (citações)
  indicador de latência por resposta

Busca:
  campo de busca com resultados paginados
  score de relevância por chunk
  filtros por metadata

Administração (simples):
  status dos componentes
  métricas básicas (cache hit rate, latência)
```

**Critério de aceitação:**
Chat funcional em localhost:3000.
Streaming visível (tokens aparecem progressivamente).
Fontes exibidas abaixo da resposta.

---

#### RF-30 — SDK Python (roadmap)

| Campo | Valor |
|---|---|
| Prioridade | Baixa |
| Escopo | v1.x |
| Origem | Requisito de DX para integração programática |

**O que faz:**
Permite usar o BuscaAI como biblioteca Python sem subir a API.

**Interface planejada:**
```python
from busca_ai import RAGPipeline

rag = RAGPipeline(settings="meu_projeto.rag_settings")
rag.ingest("./docs/")
resultados = rag.search("qual o prazo de rescisão?")
resposta = rag.chat("qual o prazo de rescisão?")
```

---

## Requisitos Não Funcionais

### Performance (RNF-01 a RNF-04)

---

#### RNF-01 — Latência de busca

| Campo | Valor |
|---|---|
| Prioridade | Alta |
| Origem | Benchmarks Qdrant + FastAPI, expectativa de UX |

```
Busca sem reranker:    p95 ≤ 500ms   (padrão recomendado)
Busca com reranker:    p95 ≤ 1.500ms (com cross-encoder CPU)
Resposta completa:     p95 ≤ 3.000ms (com LLM geração)
Cache hit:             p99 ≤ 10ms

Decomposição de latência (sem reranker):
  Pré-filtro BM25:      5–30ms
  Busca vetorial HNSW:  20–80ms
  RRF fusão:            < 5ms
  Overhead API:         10–30ms
  Total:                40–150ms

Degradação aceitável:
  Com reranker (CPU):   +80–300ms
  Com reformulação:     +300–800ms
  Com expansão query:   +500–1.500ms
```

**Critério de aceitação:**
1.000 queries de teste → p95 latência de busca ≤ 500ms sem reranker.
Medição via `rag eval --latency`.

---

#### RNF-02 — Escalabilidade da base de dados

| Campo | Valor |
|---|---|
| Prioridade | Alta |
| Origem | Benchmarks Qdrant (1.840 QPS @ 1M vetores) |

```
Volume suportado:
  Mínimo validado:   100k chunks    (Chroma embedded, dev)
  Padrão MVP:        5M chunks      (Qdrant single node, 32GB RAM)
  Meta de escopo:    50M chunks     (Qdrant cluster)
  Teórico máximo:    100M+ chunks   (Qdrant cluster + quantização)

RAM estimada (Qdrant, vetores float32):
  100k × 1536d:   ~0.6 GB
  1M × 1536d:     ~6 GB
  5M × 1536d:     ~30 GB
  50M × 1536d:    ~300 GB (exige cluster ou quantização)

Com quantização int8 (4× economia):
  50M × 1536d:    ~75 GB (viável em cluster de 3 nós 32GB cada)
```

**Critério de aceitação:**
Base de 1M chunks → latência p95 ≤ 500ms com Recall@5 ≥ 0.75.

---

#### RNF-03 — Throughput e concorrência

| Campo | Valor |
|---|---|
| Prioridade | Alta |
| Origem | FastAPI async + Celery benchmarks |

```
Queries simultâneas:   ≥ 50 (target padrão de produção)
Jobs de ingestão:      paralelo via Celery workers (configurável)
RPS API:               ≥ 100 req/s (endpoints simples como /health)

Escalabilidade horizontal:
  API (FastAPI):    múltiplas instâncias via load balancer
  Workers (Celery): adicionar workers sem alterar código
  Qdrant:           cluster com múltiplos nós de dados
```

**Critério de aceitação:**
50 queries simultâneas → sem degradação de latência acima de 20%.
Teste de carga com Locust ou k6.

---

#### RNF-04 — Disponibilidade

| Campo | Valor |
|---|---|
| Prioridade | Alta |
| Origem | Requisito operacional |

```
Target:          99% de uptime (≤ 7.3h de downtime/mês)
Single-node:     suficiente para MVP

Degradação graciosa:
  Reranker indisponível   → retorna resultado sem reranking
  LLM indisponível        → retorna chunks sem geração
  Cache indisponível      → pipeline sem cache (latência maior)
  Ingestão indisponível   → busca continua funcionando normalmente

Health check:    GET /health retorna status de cada componente
                 com timeout de 5s por componente
```

**Critério de aceitação:**
Qdrant reiniciando → API retorna 503 com mensagem descritiva em < 1s.
Qdrant voltando → API retorna 200 automaticamente (sem restart necessário).

---

### Qualidade (RNF-05 a RNF-08)

---

#### RNF-05 — Acurácia de retrieval

| Campo | Valor |
|---|---|
| Prioridade | Alta |
| Origem | RAGAS benchmarks (Es et al. 2024), literatura RAG 2024–2026 |

```
Métricas mínimas (dataset de avaliação padrão):

Retrieval:
  Recall@5:           ≥ 0.75
  Precision@5:        ≥ 0.70
  MRR:                ≥ 0.70
  NDCG@10:            ≥ 0.72
  Hit Rate@5:         ≥ 0.85

Geração:
  Faithfulness:       ≥ 0.80
  Answer Relevance:   ≥ 0.78
  Context Precision:  ≥ 0.75
  Hallucination Rate: ≤ 0.15

Metas por domínio (quando aplicável):
  Saúde / Jurídico:
    Faithfulness:       ≥ 0.95
    Hallucination Rate: ≤ 0.05
```

**Critério de aceitação:**
`rag eval --dataset golden.json` com 100 queries → todas as métricas dentro das metas.
Relatório salvo em PostgreSQL e acessível via GET /eval/latest.

---

#### RNF-06 — Robustez do retrieval

| Campo | Valor |
|---|---|
| Prioridade | Média |
| Origem | Sharma 2025 — noise robustness em RAG |

```
Noise robustness:
  Com 30% de chunks irrelevantes injetados no contexto:
  Faithfulness não deve cair mais que 15%

Negative rejection:
  Quando nenhum chunk relevante existe na base:
  Sistema deve responder "não encontrei informações suficientes"
  em vez de alucinar (hallucination = 0 nesse cenário)

Counterfactual robustness:
  Contexto com informação incorreta não deve
  dominar o conhecimento parametrizado do LLM
```

**Critério de aceitação:**
Query fora do domínio da base → resposta de "não sei" em vez de alucinação.

---

#### RNF-07 — Consistência de configuração

| Campo | Valor |
|---|---|
| Prioridade | Alta |
| Origem | Decisão arquitetural |

```
Validação:
  rag config validate → detecta campos obrigatórios ausentes
                      → detecta tipos incorretos
                      → detecta combinações incompatíveis
                      → avisa sobre credenciais hardcoded

Falha clara:
  Configuração inválida → mensagem descritiva na inicialização
                        → não sobe silenciosamente com config errada

Defaults sensatos:
  Sem configuração → sistema funciona em modo mínimo (Chroma + índice próprio)
```

---

#### RNF-08 — Qualidade de código

| Campo | Valor |
|---|---|
| Prioridade | Média |
| Origem | Requisito de manutenibilidade |

```
Cobertura de testes:    ≥ 80% nas funções críticas do pipeline
Type hints:             obrigatórios em todas as funções públicas
Documentação:           docstring em todas as classes e funções públicas
Linting:                flake8 + black + isort sem erros
Segredos:               bandit scan sem credenciais hardcoded
CI/CD:                  testes + linting em todo pull request
```

---

### Segurança (RNF-09 a RNF-11)

---

#### RNF-09 — Segurança de comunicação

| Campo | Valor |
|---|---|
| Prioridade | Alta |
| Origem | Requisito de compliance |

```
Transporte:
  HTTPS obrigatório em produção (TLS 1.2+)
  CORS configurável (lista de origens permitidas)

Autenticação:
  JWT com HS256 (mínimo)
  Token expiry configurável
  Refresh token com rotação

Headers de segurança:
  X-Content-Type-Options: nosniff
  X-Frame-Options: DENY
  Content-Security-Policy
  Strict-Transport-Security (HSTS)
```

---

#### RNF-10 — Proteção contra ataques

| Campo | Valor |
|---|---|
| Prioridade | Alta |
| Origem | OWASP Top 10 |

```
SQL injection:
  Queries sempre parametrizadas via SQLAlchemy ORM
  Nunca concatenação de string com input do usuário

Prompt injection:
  Conteúdo de documentos sanitizado antes de ir ao LLM
  System prompt define fronteiras claras
  Logs de queries suspeitas

Path traversal:
  Caminhos de arquivo validados antes de abrir
  Acesso restrito ao diretório de docs configurado

Rate limiting:
  Proteção contra brute force e DoS (RF-21)
  Bloqueio automático de IPs com excesso de 429
```

---

#### RNF-11 — Gestão de credenciais

| Campo | Valor |
|---|---|
| Prioridade | Alta |
| Origem | Boas práticas de segurança |

```
Credenciais:
  NUNCA no código ou nos settings
  SEMPRE via variável de ambiente
  .env no .gitignore obrigatório
  .env.example com placeholders (sem valores reais) no repositório

Detecção:
  bandit scan detecta secrets hardcoded no CI
  truffleHog opcional para scan do histórico git

Rotação:
  SECRET_KEY rotacionável sem downtime (múltiplas chaves ativas)
```

---

### Operação (RNF-12 a RNF-16)

---

#### RNF-12 — Portabilidade e conteinerização

| Campo | Valor |
|---|---|
| Prioridade | Alta |
| Origem | Requisito de deployment |

```
Docker:
  Dockerfile para API (Python + FastAPI)
  Dockerfile para workers (Celery)
  Dockerfile para frontend (Node + React)

Docker Compose:
  docker-compose up → sobe toda a stack em um comando
  Serviços: api, worker, qdrant, postgres, redis, frontend

Compatibilidade:
  Linux (Ubuntu 22.04+)
  macOS (Apple Silicon e x86)
  Windows WSL2
  Kubernetes (Helm chart — roadmap)
```

**Critério de aceitação:**
`docker compose up` → sistema funcional em < 5 minutos em máquina limpa.

---

#### RNF-13 — Manutenibilidade

| Campo | Valor |
|---|---|
| Prioridade | Alta |
| Origem | Requisito de longo prazo |

```
Modularidade:
  cada componente isolado em seu módulo (ingestion/, retrieval/, etc.)
  interfaces bem definidas entre módulos
  troca de componente sem alterar outros

Configurabilidade:
  toda mudança de comportamento via settings
  sem magic numbers no código

Migrations:
  Alembic para versionamento do schema PostgreSQL
  scripts de migração versionados e reversíveis
  alembic upgrade head → aplica todas as migrations pendentes

Changelog:
  CHANGELOG.md atualizado a cada versão
  conventional commits (feat, fix, docs, refactor)
```

---

#### RNF-14 — Extensibilidade

| Campo | Valor |
|---|---|
| Prioridade | Alta |
| Origem | Requisito central do framework |

```
Interfaces base (ABC):
  BaseLoader      → adicionar novo conector de dados
  BaseEmbedder    → adicionar novo modelo de embedding
  BaseVectorStore → adicionar novo banco vetorial
  BaseReranker    → adicionar novo reranker
  BaseLLMProvider → adicionar novo provedor de LLM

Padrão de registro:
  loader customizado registrado em settings sem alterar core
  pipeline customizado via LangGraph StateGraph
```

**Critério de aceitação:**
Novo loader implementando BaseLoader → funciona sem modificar o core.

---

#### RNF-15 — Observabilidade operacional

| Campo | Valor |
|---|---|
| Prioridade | Alta |
| Origem | Requisito operacional |

```
Logs:
  formato JSON estruturado
  nível configurável (DEBUG, INFO, WARNING, ERROR)
  log de cada query: latência, score, tokens, custo
  log de cada ingestão: chunks, erros, duração

Métricas:
  endpoint /metrics no formato Prometheus
  integração opcional com Grafana (dashboard JSON disponível)

Rastreamento:
  trace distribuído opcional via OpenTelemetry
  integração com Langfuse para rastreamento de LLM

Alertas:
  email configurável para: score cai abaixo do threshold,
  latência acima do limite, custo diário excedido
```

---

#### RNF-16 — Custo operacional

| Campo | Valor |
|---|---|
| Prioridade | Média |
| Origem | Requisito financeiro |

```
Estratégias obrigatórias:
  cache de queries:     reduz custo de LLM em 30–60%
  pré-filtragem léxica: reduz volume de embedding por query
  batch API:            50% off para ingestão em lote

Estratégias opcionais:
  roteamento por complexidade: economia de 60–80% no LLM
  quantização vetorial:        reduz RAM do Qdrant em 4–16×
  embedding local:             elimina custo de API de embedding

Rastreamento de custo:
  custo por query rastreado (tokens × preço)
  custo por job de ingestão rastreado
  relatório mensal disponível via GET /metrics/cost

Cenários estimados (mai/2026):
  POC (100k chunks, 5k queries/mês):    ~$55/mês
  Produção (5M chunks, 100k queries):   ~$430–600/mês
  Escala (50M chunks, 1M queries):      ~$2.100+/mês
```

---

### Arquitetura (RNF-17 a RNF-20)

---

#### RNF-17 — Paradigma Modular RAG

| Campo | Valor |
|---|---|
| Prioridade | Alta |
| Origem | Gao et al. 2024 — estado da arte |

```
O pipeline deve seguir o paradigma Modular RAG:
  6 módulos: Indexing, Pre-Retrieval, Retrieval,
             Post-Retrieval, Orchestration, Generation

Orquestração: LangGraph StateGraph
  arestas condicionais para roteamento adaptativo
  estado explícito compartilhado entre módulos
  suporte futuro a loops (Self-RAG, CRAG)

Plugabilidade:
  cada módulo substituível via settings sem alterar outros
  Naive e Advanced RAG como casos especiais configuráveis
```

---

#### RNF-18 — Reprodutibilidade de resultados

| Campo | Valor |
|---|---|
| Prioridade | Média |
| Origem | Requisito científico |

```
Determinismo:
  temperature=0.0 por padrão
  seed configurável (quando suportado pela API)
  mesma query + mesma base → mesma resposta

Versionamento:
  versão do modelo de embedding salva no PostgreSQL
  versão do LLM salva no log de queries
  possível reproduzir resultado de uma query histórica
```

---

#### RNF-19 — Compatibilidade de API

| Campo | Valor |
|---|---|
| Prioridade | Média |
| Origem | Requisito de produto |

```
Versionamento:
  /api/v1/ — versão atual
  v1 mantida por mínimo 12 meses após lançamento de v2

Backward compatibility:
  novos campos opcionais, nunca remover campos existentes
  deprecação com aviso mínimo de 1 versão antes de remoção

OpenAPI:
  spec 3.0 gerada automaticamente
  disponível em /openapi.json e /docs
```

---

#### RNF-20 — Independência de fornecedor (anti-lock-in)

| Campo | Valor |
|---|---|
| Prioridade | Alta |
| Origem | Decisão arquitetural central |

```
O framework não deve ter dependência obrigatória de nenhum
fornecedor proprietário.

Evidências:
  LLM:           plugável (OpenAI, Anthropic, Groq, Ollama local)
  Embedding:     plugável (API ou modelo local)
  Vector store:  plugável (Qdrant, pgvector, Chroma)
  Reranker:      plugável (API ou cross-encoder local)
  Pre-filter:    plugável (próprio, Meilisearch, OpenSearch)

Stack mínima 100% open-source e self-hosted:
  Qdrant + BGE-M3 + Ollama + PostgreSQL + Redis + FastAPI
  → zero dependência de API externa
  → zero custo de API
```

---

## Matriz de rastreabilidade

| Requisito | Fonte literária | Decisão técnica | Módulo de implementação |
|---|---|---|---|
| RF-01 | Modular RAG (Gao 2024) | Loaders por tipo | `ingestion/loaders/` |
| RF-02 | Req. operacional | SQLAlchemy ORM | `ingestion/loaders/sql.py` |
| RF-04 | Lassance 2023 | BM25 próprio | `retrieval/prefilter/` |
| RF-05 | Cormack 2009, Sharma 2025 | Hybrid + RRF | `retrieval/strategies/` |
| RF-06 | Khattab 2020, Sharma 2025 | Cross-encoder | `retrieval/reranker/` |
| RF-07 | Lewis 2020 | FastAPI + LLM | `generation/` |
| RF-08 | Req. reformulação | LLM barato (Groq) | `retrieval/pre/rewrite.py` |
| RF-09 | Req. volume | Celery + Redis | `ingestion/tasks.py` |
| RF-10 | Req. resiliência | Checkpoint Redis | `ingestion/checkpoint.py` |
| RF-14 | Req. performance | Redis cache | `cache/` |
| RF-18 | Es et al. 2024 | RAGAS | `eval/` |
| RNF-01 | Benchmarks Qdrant | HNSW tuning | `vectorstore/qdrant.py` |
| RNF-05 | Es et al. 2024 | RAGAS metrics | `eval/metrics.py` |
| RNF-17 | Gao et al. 2024 | LangGraph | `retrieval/graph.py` |

---

## O que está fora do escopo

```
FORA DO MVP                       RAZÃO
───────────────────────────────────────────────────────────────
Self-RAG                          4-8 LLM calls/query — custo proibitivo
Corrective RAG (CRAG)             dependência de busca web externa
GraphRAG                          LLM por chunk na ingestão — inviável em escala
Agentic RAG                       complexidade alta, fora do escopo de framework
Fine-tuning de modelos            fora do escopo de RAG
Treinamento de embeddings         fora do escopo de framework
Dados multimodais (imagem/áudio)  complexidade alta, v2.0+
Streaming de ingestão (Kafka)     caso de uso específico
Dashboard de analytics próprio    usa Grafana externo
SDK em outras linguagens          só Python no MVP
Multi-tenant com isolamento físico v1.x
GraphRAG mode                     v2.0+

ROADMAP CLARO (v1.x):
  Conectores S3, Drive, Notion, Confluence
  SDK Python (`from busca_ai import RAGPipeline`)
  Multi-tenancy lógico
  RAG Fusion como estratégia adicional
  RAPTOR como estratégia de chunking
  Self-RAG como modo premium (configurável)
```
