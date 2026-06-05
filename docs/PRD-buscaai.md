# PRD — BuscaAI
**Product Requirements Document**
**Versão 1.0 — maio 2026**

---

## Sumário

1. [Visão do produto](#1-visão-do-produto)
2. [Problema](#2-problema)
3. [Usuários](#3-usuários)
4. [Objetivos e métricas de sucesso](#4-objetivos-e-métricas-de-sucesso)
5. [Funcionalidades](#5-funcionalidades)
6. [Fora do escopo](#6-fora-do-escopo)
7. [Arquitetura e decisões técnicas](#7-arquitetura-e-decisões-técnicas)
8. [Roadmap](#8-roadmap)
9. [Riscos](#9-riscos)

---

## 1. Visão do produto

**BuscaAI** é um framework Python de Retrieval-Augmented Generation (RAG)
híbrido e modular para desenvolvedores que precisam construir sistemas de
busca inteligente sobre grandes bases de dados heterogêneas.

```
O desenvolvedor configura um arquivo (rag_settings.py),
sobe o ambiente com um comando e passa a ter um sistema
de recuperação de informação funcionando —
sem precisar conhecer os detalhes internos de RAG.

rag_settings.py → rag up → rag ingest → rag search "query"
```

**Missão:** eliminar a barreira técnica entre ter uma base de dados
e ter um sistema de busca inteligente sobre ela.

---

## 2. Problema

### 2.1 O problema central

Empresas e pesquisadores têm grandes volumes de documentos — contratos, laudos,
relatórios, artigos, manuais — e precisam que pessoas possam fazer perguntas em
linguagem natural e receber respostas baseadas nesses documentos.

Construir isso do zero exige conhecimento profundo de:
- Modelos de embedding e bancos vetoriais
- Estratégias de busca híbrida (BM25 + vetorial + RRF)
- Chunking, pré-processamento de documentos
- Orquestração de pipelines LLM
- Infraestrutura de ingestão assíncrona
- Avaliação de qualidade (RAGAS, métricas de retrieval)

**A maioria dos desenvolvedores não tem esse conhecimento** — e não deveria
precisar ter para construir um sistema de busca.

### 2.2 O que existe hoje

| Solução atual | Limitação |
|---|---|
| LangChain / LlamaIndex | Frameworks genéricos, muita configuração, sem opinião sobre stack |
| OpenAI Assistants | Lock-in total, sem controle sobre retrieval, caro em escala |
| Soluções enterprise (Elastic, Cohere) | Caras, difíceis de customizar, vendor lock-in |
| Construir do zero | Leva meses, requer especialista em RAG |

### 2.3 A lacuna

Não existe um framework Python com opinião clara que:
- Seja fácil de instalar (`pip install busca-ai`)
- Funcione out-of-the-box com boas configurações padrão
- Seja 100% open-source (sem lock-in obrigatório)
- Suporte busca híbrida de verdade (não só vetorial)
- Tenha avaliação de qualidade integrada

---

## 3. Usuários

### 3.1 Usuário primário — o desenvolvedor

O desenvolvedor é quem instala, configura e opera o BuscaAI.
Ele não é necessariamente especialista em Machine Learning ou RAG.

**Perfil:**
- Conhece Python e REST APIs
- Tem experiência com Docker e ambientes de desenvolvimento
- Entende bancos de dados, mas não necessariamente bancos vetoriais

**Necessidades:**
- Setup rápido — quer ver funcionando em menos de 30 minutos
- Documentação clara com exemplos reais
- Configuração simples, sem conhecimento de RAG

**Frustrações atuais:**
- LangChain tem muitas abstrações para entender
- Ferramentas enterprise são caras e fechadas


## 4. Objetivos e métricas de sucesso

### 4.1 Objetivos do produto

```
O1 — Facilidade de adoção
     Dev consegue ter o sistema funcionando em < 30 minutos.

O2 — Qualidade de retrieval
     Recall@5 ≥ 0.75 e Faithfulness ≥ 0.80 out-of-the-box,
     sem tuning manual pelo desenvolvedor.

O4 — Sem lock-in
     Stack 100% open-source disponível — zero dependência de
     API externa obrigatória.

O5 — Extensível
     Dev consegue adicionar novo conector, embedding ou LLM
     sem alterar o core do framework.
```

### 4.2 Métricas de sucesso (KPIs)

**Adoção:**
```
Tempo de setup (pip install → primeira busca):   ≤ 30 minutos
Documentação suficiente para começar sem suporte: sim
```

**Qualidade (benchmark padrão):**
```
Recall@5 (busca híbrida):         ≥ 0.75
Precision@5:                      ≥ 0.70
Faithfulness (RAGAS):             ≥ 0.80
Hallucination Rate:               ≤ 0.15
Latência p95 (sem reranker):      ≤ 500ms
Latência p95 (com reranker):      ≤ 1.500ms
```

**Escalabilidade:**
```
Chunks suportados:                ? 
Queries simultâneas:              ?
Throughput de ingestão:           ? chunks/minuto
```
---

## 5. Funcionalidades

Organizado por prioridade e fase de entrega.

### 5.1 MVP — entrega obrigatória

#### Ingestão

| # | Funcionalidade | Descrição |
|---|---|---|
| F01 | Ingestão de arquivos | PDF, CSV, TXT, Markdown, DOCX — com pré-processamento completo |
| F02 | Ingestão de bancos SQL | PostgreSQL, MySQL, SQLite via SQLAlchemy — query configurável |
| F03 | Chunking adaptativo | Recursive, Markdown, Auto — detecta tipo e aplica estratégia |
| F04 | Pré-processamento PDF | 7 operações de limpeza + extração de metadados naturais |
| F05 | Deduplicação | Hash SHA-256 — skip automático se doc não mudou |


#### Busca e retrieval

| # | Funcionalidade | Descrição |
|---|---|---|
| F06 | Busca híbrida | Lexical + vetorial + RRF — tudo dentro do banco escolhido |
| F07 | Pré-filtragem lexical | 1º estágio, reduz universo antes da Busca híbrida |
| F08 | Reranker | Cross-encoder local ou API (Cohere, Voyage, Jina) |
| F09 | Filtros de metadados | Por fonte, data, tipo, coleção via payload do banco |

#### Geração

| # | Funcionalidade | Descrição |
|---|---|---|
| F10 | Geração de resposta | OpenAI, Anthropic, Groq, Gemini, Ollama — plugável |
| F11 | Chat com histórico | Reformulação de query de acompanhamento, sessão |
| F12 | Citação de fontes | Resposta inclui doc_id, fonte, página, score |

#### Operação

| # | Funcionalidade | Descrição |
|---|---|---|
| F13 | Avaliação RAGAS | Faithfulness, Answer Relevance, Context Precision/Recall |
| F14 | Backup automático | Banco vetorial — incremental diário, full semanal |
| F15 | Auth JWT | Roles: admin, editor, reader — rate limiting por role |
| F16 | Observabilidade | Métricas Prometheus, logs JSON, alertas configuráveis |
| F17 | Configuração central | rag_settings.py — toda config em um arquivo, credenciais via env |

#### Interfaces

| # | Funcionalidade | Descrição |
|---|---|---|
| F18 | API REST | FastAPI — OpenAPI 3.0 gerado automaticamente |
| F19 | CLI | Ingestão, busca, backup, avaliação, chat interativo |
| F20 | Frontend web | React — chatbot de validação com histórico e fontes |

### 5.2 v1.x — roadmap próximo

| # | Funcionalidade | Justificativa |
|---|---|---|
| F21 | Roteamento de query | Classifica complexidade, escolhe pipeline adequado |
| F22 | Conectores cloud | S3, Google Drive, Notion, Confluence |
| F23 | RAG Fusion | Múltiplas variações de query + RRF para maior recall |
| F24 | RAPTOR | Indexação hierárquica — chunks + resumos |
| F25 | SDK Python | `from busca_ai import RAGPipeline` sem API |
| F26 | Query expansion | Gera sinônimos antes de buscar (LLM barato) |
| F27 | HyDE | Hypothetical Document Embedding para queries vagas |
| F28 | Ingestão assíncrona | Celery + Redis|
---


## 7. Arquitetura e decisões técnicas

### 7.1 As duas arquiteturas de busca

O BuscaAI suporta duas arquiteturas — o desenvolvedor escolhe uma:

```
OPÇÃO A — OpenSearch
  busca lexical (BM25) + vetorial na mesma engine
  hybrid via RSF nativo
  ideal: lexical é o foco, custo menor

OPÇÃO B — Qdrant
  vetor denso + esparso (SPLADE) no mesmo ponto
  hybrid via RRF
  ideal: Quando qualidade é o foco
```

O chunk vive sempre **dentro do banco**. Não existe índice BM25
separado carregado em memória.

### 7.2 Decisões de arquitetura consolidadas

| Decisão | Escolha | Razão |
|---|---|---|
| Paradigma RAG | Modular RAG (Gao et al. 2024) | Plugabilidade |
| Orquestração | LangGraph | Grafos condicionais, suporta todos os padrões de fluxo |
| Banco vetorial  | Qdrant | Apache 2.0, melhor Filtered HNSW, menor RAM |
| Embedding denso  (API) | OpenAI text-3-small | $0.02/1M, ecossistema amplo |
| Embedding denso  (Local) | BGE-M3 | Apache 2.0, denso + esparso + PT-BR |
| Reranker  | MiniLM-L-6 local | Zero custo de API, CPU suficiente |
| Fusão | RRF (k=60) | Robusto, sem normalização de scores |
| Avaliação | RAGAS | Padrão de mercado, 4 métricas automáticas |
| API | FastAPI | OpenAPI automático, async nativo |
| Anti lock-in | Stack 100% Local possível | Qdrant + BGE-M3 + Ollama |

### 7.3 Pipeline de retrieval

```
PRE_RETRIEVAL   → transformação de query (HyDE, expansão, reformulação)
     ↓
RETRIEVAL       → lexical + vetorial + fusão
     ↓
POST_RETRIEVAL  → reranker → score mínimo → compressão → prompt packing
     ↓
GENERATION      → LLM → resposta com fontes
```

### 7.4 Configuração em 4 blocos de retrieval

```python
PRE_RETRIEVAL = {
    "query_expansion": {"enabled": False, "provider": "groq"},
    "hyde":            {"enabled": False, "provider": "groq"},
    "reformulation":   {"enabled": False,  "provider": "groq"},
}

RETRIEVAL = {
    "strategy": "hybrid",   # hybrid | dense | lexical
    "top_k":    50,
    "rrf_k":    60,
    "first_stage": {        # pré filtros lexical 
        "enabled":  True,
        "top_n":    50000,
        "language": "pt",
    },
}

POST_RETRIEVAL = {
    "reranker": {
        "enabled":     True,
        "model":       "cross-encoder",
        "provider":    "local",
        "final_top_k": 5,
    },
    "min_score":           {"enabled": False, "threshold": 0.5},
    "context_compression": {"enabled": False},
    "prompt_packing":      {"enabled": False},
}
```

---

## 8. Roadmap

### Fase 1 — MVP (TRL 2-3 / POC)

**Objetivo:** sistema funcionando end-to-end com qualidade suficiente para validar o conceito.

```
ENTREGÁVEIS
  ✓ Pipeline de ingestão completo (PDF, CSV, SQL)
  ✓ Busca híbrida (Qdrant com esparso)
  ✓ Reranker local (MiniLM)
  ✓ Chat com histórico e streaming
  ✓ Avaliação RAGAS integrada
  ✓ API REST + CLI + Frontend
  ✓ Docker Compose (rag up = tudo funcionando)
  ✓ Backup automático

MARCOS
  M1: pipeline de ingestão testado com 3 tipos de documento
  M2: busca híbrida com Recall@5 ≥ 0.75 em dataset de avaliação
  M3: chat com histórico, reformulação e streaming
  M4: docker-compose up → funcionando em < 5 minutos
```

### Fase 2 — v1.x (produto)

**Objetivo:** produto estável, com conectores adicionais e extensibilidade validada.

```
ENTREGÁVEIS
  → Conectores S3, Google Drive, Notion
  → RAG Fusion e HyDE
  → SDK Python (sem API)
  → Two-stage retrieval (cascade com IDs)
  → Documentação completa em docs/
```

---

## 9. Riscos

| # | Risco | Probabilidade | Impacto | Mitigação |
|---|---|---|---|---|
| R1 | Qualidade de retrieval abaixo do esperado em domínios específicos | Média | Alto | Avaliação com dataset real do domínio antes do lançamento; fine-tuning de embedding como plano B |
| R2 | Latência acima do SLA em bases grandes (> 10M) | Média | Alto | Benchmarks com VectorDBBench; quantização de vetores; cluster Qdrant |
| R3 | Custo de API de embedding/LLM excede orçamento | Baixa | Médio | Cache agressivo; roteamento por complexidade; stack OSS como fallback |
| R4 | Mudança de licença de dependência crítica (Qdrant, etc.) | Baixa | Alto | Anti-lock-in no design: toda dependência é plugável; OpenSearch como alternativa Apache 2.0 |
| R5 | Alucinação em domínio crítico (saúde, jurídico) | Média | Muito alto | Faithfulness threshold obrigatório ≥ 0.95; negative rejection; human-in-the-loop recomendado |
| R6 | Complexidade de configuração afasta desenvolvedores | Média | Alto | Settings com padrões sensatos; `rag init` gera template pronto; documentação com exemplos reais |
| R7 | Concorrência de ferramentas maiores (LangChain, LlamaIndex) | Alta | Médio | Foco em opinionated stack + busca híbrida real + avaliação integrada — diferencial claro |

---
