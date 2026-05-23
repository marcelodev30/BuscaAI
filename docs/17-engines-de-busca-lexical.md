# Engines de Busca Lexical — Elasticsearch, OpenSearch e Meilisearch

Este documento explica as três engines de busca lexical mais relevantes que podem ser usadas como alternativa ao índice invertido próprio do BuscaAI. Cobre o que cada uma é, como funciona, quando usar, e como elas se encaixam no pipeline do framework.

---

## Por que essas engines existem

O BuscaAI tem dois momentos onde a busca lexical aparece:

1. **Pré-filtragem léxica** — reduz milhões de chunks para milhares antes da busca vetorial
2. **Busca esparsa** — uma das duas pernas da busca híbrida (junto com a densa)

Hoje os dois usam um índice invertido próprio, implementado dentro do BuscaAI. Funciona, mas tem limites:

```
Limites do índice próprio:
   • Carregado em memória do processo → não escala horizontalmente
   • Sem clustering nativo → uma máquina só
   • Sem replicação → ponto único de falha
   • Sem dashboards prontos para monitoramento
   • Manutenção própria de bugs e otimizações
```

Engines de busca lexical resolvem tudo isso — são bancos de dados especializados em busca de texto, com décadas de otimização acumulada.

---

## Onde elas entram no pipeline

```
PIPELINE ATUAL DO BUSCAAI:

   query
     ↓
   [pré-filtragem léxica]  ← índice invertido próprio (BM25)
     ↓
   [busca densa]            ← Qdrant
     ↓
   [busca esparsa]          ← também usa índice próprio
     ↓
   [fusão RRF]
     ↓
   [reranker]


COM ENGINE DE BUSCA LEXICAL:

   query
     ↓
   [pré-filtragem]    ← Elasticsearch / OpenSearch / Meilisearch
     ↓
   [busca densa]      ← Qdrant (ou a própria engine se suportar)
     ↓
   [busca esparsa]    ← Elasticsearch / OpenSearch / Meilisearch
     ↓
   [fusão RRF]
     ↓
   [reranker]
```

Em alguns casos, uma única engine pode fazer **as três coisas** — pré-filtragem, busca densa e busca esparsa — substituindo o Qdrant junto. Isso simplifica a stack, com trade-offs que veremos abaixo.

---

## 1. Elasticsearch

### O que é

Elasticsearch é o **veterano** do mercado. Criado em 2010 por Shay Banon, é o motor de busca mais usado do mundo. Foi construído em cima do Apache Lucene (a biblioteca de busca textual mais madura da indústria) e adicionou camadas de distribuição, API REST, e operações em cluster.

É o coração do Elastic Stack (anteriormente ELK Stack), que combina Elasticsearch + Logstash + Kibana — uma das pilhas mais conhecidas para análise de logs e busca empresarial. Roda em Java sobre a JVM.

### Como funciona internamente

```
Elasticsearch — arquitetura distribuída

   ┌─────────────────────────────────────────┐
   │              CLUSTER                     │
   │                                          │
   │  ┌──────────┐  ┌──────────┐  ┌────────┐│
   │  │  Master  │  │  Master  │  │ Master ││  ← gerenciam o cluster
   │  │   Node   │  │   Node   │  │  Node  ││
   │  └──────────┘  └──────────┘  └────────┘│
   │                                          │
   │  ┌──────────┐  ┌──────────┐  ┌────────┐│
   │  │   Data   │  │   Data   │  │  Data  ││  ← armazenam dados
   │  │   Node   │  │   Node   │  │  Node  ││
   │  └──────────┘  └──────────┘  └────────┘│
   │       ↓ contém ↓                         │
   │  ┌──────────────────────────────────┐  │
   │  │  ÍNDICE → SHARDS → DOCUMENTOS    │  │
   │  │  cada shard é uma fatia do índice │  │
   │  │  replicas garantem alta disponib. │  │
   │  └──────────────────────────────────┘  │
   └─────────────────────────────────────────┘
```

Conceitos-chave:

- **Índice** — o equivalente de uma "tabela" de documentos.
- **Shard** — fatia de um índice. Permite distribuir dados em múltiplos nós.
- **Replica** — cópia de um shard. Garante disponibilidade se um nó cair.
- **Document** — unidade de dado, em JSON.
- **Query DSL** — linguagem de consulta em JSON, expressiva mas verbosa.

### Funcionalidades de busca

Elasticsearch oferece:

- **BM25** como algoritmo padrão de ranking lexical
- **Hybrid search** via kNN (HNSW) desde 2023 — combina busca textual e vetorial
- **Aggregations** — análise estatística sobre os dados (médias, contagens, percentis)
- **Fuzzy search** — tolerância a typos
- **Filtering** — filtros estruturais sobre metadados
- **Multilingual analyzers** — analisadores para português, inglês, alemão, etc.

### Pontos fortes

- **Maturidade extrema.** 15+ anos de produção em empresas de todos os tamanhos.
- **Escala para petabytes.** Suporta bilhões de documentos em clusters de centenas de nós.
- **Ecossistema enorme.** Kibana para dashboards, Logstash para ingestão, 350+ integrações.
- **Comunidade gigante.** Documentação extensa, soluções para qualquer problema no Stack Overflow.
- **Recursos avançados** — machine learning, anomaly detection, alerting nativo.

### Pontos fracos

- **Pesado.** JVM consome muita RAM: 2-4 GB mínimo só para o processo, escala rapidamente para 8-16 GB em produção.
- **Complexo.** A Query DSL é poderosa mas verbosa. Subir um cluster requer configurar dezenas de parâmetros.
- **Curva de aprendizado alta.** "Antes de fazer a primeira busca, há vários parâmetros que precisam ser configurados" — relevância, tolerância a typos, analyzers.
- **Licença SSPL** desde 2021. Não é considerada open-source pela OSI. Em 2024 voltou a oferecer opção AGPL, mas a confiança da comunidade foi afetada.

### Custo

```
Self-hosted (gratuito como software):
   Mínimo:    1 nó com 4 GB RAM            →  ~$25-50/mês de VPS
   Produção:  cluster 3 nós, 16 GB cada    →  ~$200-400/mês

Elastic Cloud (gerenciado):
   Standard:  a partir de $95/mês
   Gold:      a partir de $200/mês
   Enterprise: custom
```

### Quando usar

- Empresa já tem Elasticsearch rodando para logs/observabilidade — aproveita o que existe.
- Precisa de **analytics complexos** além de busca (dashboards, agregações pesadas).
- Vai operar em **escala muito alta** (centenas de milhões a bilhões de documentos).
- Tem equipe dedicada de DevOps para administrar.

---

## 2. OpenSearch

### O que é

OpenSearch é um **fork do Elasticsearch** feito pela AWS em 2021. Quando a Elastic mudou a licença para SSPL (restringindo seu uso por provedores cloud), a AWS pegou a última versão Apache 2.0 e continuou o desenvolvimento como projeto independente.

Hoje OpenSearch é mantido por uma fundação aberta com contribuições de AWS, SAP, Aiven, e outros. É praticamente idêntico ao Elasticsearch em conceitos, mas com licença Apache 2.0 verdadeira.

### Como funciona

A arquitetura é a mesma do Elasticsearch — mesmos conceitos de cluster, nós, índices, shards, replicas. A maior parte da API REST é compatível.

```
Elasticsearch                  OpenSearch
─────────────────             ──────────────────
Apache Lucene 9.x       →     Apache Lucene 9.x
Query DSL em JSON       →     Query DSL em JSON
Cluster/Shards/Replicas →     Cluster/Shards/Replicas
Kibana (separado)       →     OpenSearch Dashboards
   (proprietário)              (Apache 2.0, fork do Kibana)
```

### Onde divergiram desde o fork

```
ELASTICSEARCH                       OPENSEARCH
─────────────────                  ─────────────────
ML proprietário                    ML via plugins comunidade
Anomaly detection                  Anomaly detection (built-in)
Stack monitoring                   Observability suite
Security XPack                     Security plugin (built-in)
Plugins próprios                   Plugins Apache 2.0
Otimizações recentes (2024+)       Otimizações próprias
```

### Pontos fortes

- **Apache 2.0 puro** — sem amarras de licença, ideal para SaaS e cloud providers.
- **AWS friendly.** Integração nativa com AWS OpenSearch Service.
- **Compatibilidade com Elasticsearch** — migração de clientes existentes é fácil.
- **Security built-in.** Recursos de segurança que no Elasticsearch são pagos vêm grátis aqui.
- **Comunidade ativa.** Empresas grandes (AWS, SAP, Logz.io) sustentam o desenvolvimento.

### Pontos fracos

- **Mesma pesagem do Elasticsearch.** JVM, RAM alta, complexidade de operação.
- **Plugins divergentes.** Plugins comerciais da Elastic não funcionam aqui, e vice-versa.
- **Performance em alguns benchmarks** — versões recentes do Elasticsearch trouxeram otimizações que OpenSearch ainda não acompanhou em todos os casos.
- **Documentação menor** que a do Elasticsearch original (mas crescendo).

### Custo

```
Self-hosted (gratuito como software):
   Mesmos custos do Elasticsearch self-hosted
   Mínimo:    ~$25-50/mês de VPS
   Produção:  ~$200-400/mês

AWS OpenSearch Service:
   t3.small.search:     ~$25-50/mês
   m6g.large.search:    ~$130/mês
   r6g.large.search:    ~$160/mês (mais RAM, melhor para busca)
   Cluster produção:    ~$500-2.000/mês

Aiven OpenSearch:        a partir de $120/mês
```

### Quando usar

- Quer recursos do Elasticsearch sem amarras de licença.
- Já está no ecossistema AWS — OpenSearch Service é o caminho natural.
- Precisa de SaaS sem riscos legais — Apache 2.0 elimina dúvidas.
- Está em setor regulado que exige software 100% open-source comprovado.

---

## 3. Meilisearch

### O que é

Meilisearch é uma engine de busca **leve, rápida e focada em simplicidade**. Criada em 2018 por desenvolvedores frustrados com a complexidade do Elasticsearch, foi escrita do zero em **Rust**, priorizando velocidade e baixo consumo de recursos.

O foco do Meilisearch não é log analytics ou data warehousing — é **busca de produto e aplicação**. Para casos onde o usuário digita uma query e quer resultados imediatos (search-as-you-type), poucos sistemas ganham dela.

### Como funciona

A arquitetura é radicalmente diferente das outras duas — em vez de um cluster distribuído por padrão, Meilisearch foi feito para rodar em um nó só, focado em latência baixa.

```
Meilisearch — arquitetura monolítica leve

   ┌─────────────────────────────────────────┐
   │           Processo Meilisearch          │
   │                                          │
   │  ┌────────────────────────────────────┐ │
   │  │  Tokenização customizada           │ │
   │  │  (suporte nativo a 50+ idiomas)    │ │
   │  └────────────────────────────────────┘ │
   │                  ↓                       │
   │  ┌────────────────────────────────────┐ │
   │  │  Estruturas FST                    │ │
   │  │  (Finite State Transducer)         │ │
   │  │  para lookup ultra rápido          │ │
   │  └────────────────────────────────────┘ │
   │                  ↓                       │
   │  ┌────────────────────────────────────┐ │
   │  │  LMDB (Lightning Memory-Mapped DB)  │ │
   │  │  storage persistente eficiente     │ │
   │  └────────────────────────────────────┘ │
   │                                          │
   └─────────────────────────────────────────┘

   Sem JVM. Sem cluster por padrão. ~200-500MB de RAM.
```

Conceitos-chave:

- **Index** — coleção de documentos (JSON).
- **Tasks** — operações assíncronas (a maioria das mutações é assíncrona).
- **Searchable attributes** — quais campos são pesquisáveis (default: todos).
- **Filterable attributes** — campos que aceitam filtros estruturados.
- **Ranking rules** — regras de relevância customizáveis.

### Funcionalidades de busca

- **BM25** como base, mas com várias regras de ranking customizáveis acima.
- **Typo tolerance built-in** — corrige typos automaticamente, sem configuração.
- **Faceted search** — agregações simples (não tão poderosas quanto Elasticsearch).
- **Vector search desde 2024** — kNN integrado, ainda menos maduro que Qdrant.
- **Highlighting** — destaca trechos que casam com a query.
- **Multi-tenant** via tenant tokens.

### Pontos fortes

- **Leveza.** 200-500 MB de RAM básico, escala bem até dezenas de milhões de documentos.
- **Setup em minutos.** "Plug-and-play" — defaults funcionam bem para a maioria dos casos.
- **API simples.** REST limpo, SDKs em todas as linguagens, sem Query DSL complexa.
- **Velocidade.** Resultados em <50ms, ideal para search-as-you-type.
- **Rust.** Sem overhead de JVM, footprint pequeno, sem garbage collector pausando consultas.
- **MIT license.** Totalmente livre, sem amarras.

### Pontos fracos

- **Escala menor.** Não foi feito para bilhões de documentos. Limite prático é dezenas de milhões.
- **Sem analytics complexos.** Agregações simples, mas nada perto de Elasticsearch aggregations.
- **Vector search recente.** Funciona, mas o Qdrant é mais maduro para vetores.
- **Sem clustering open-source.** A versão self-hosted é mono-nó. Replicação só na versão Cloud (Pro/Enterprise) ou via solução custom.
- **Ecossistema menor.** Sem o equivalente do Kibana built-in (existem dashboards de terceiros).

### Custo

```
Self-hosted (gratuito como software):
   1 nó com 1 GB RAM             →  ~$5-10/mês de VPS pequena
   1 nó com 4 GB RAM (até 5M docs)→ ~$15-25/mês de VPS
   1 nó com 16 GB RAM             →  ~$50-80/mês

Meilisearch Cloud:
   Build:        $30/mês  (100k documentos, ideal para dev)
   Pro:          $300/mês (1M documentos, com replicação)
   Production:   custom   (volumes grandes, alta disponibilidade)
```

### Quando usar

- POC, desenvolvimento local, hardware fraco.
- Bases de até ~10 milhões de documentos.
- Search-as-you-type, autocomplete, busca de produto em e-commerce.
- Time pequeno sem DevOps dedicado.
- Quando a simplicidade vale mais que recursos avançados.

---

## Comparação detalhada

```
                       ELASTICSEARCH    OPENSEARCH       MEILISEARCH
═══════════════════════════════════════════════════════════════════════
ORIGEM                 2010 (Shay Banon) 2021 (AWS fork) 2018 (Meili SAS)
LINGUAGEM              Java (JVM)        Java (JVM)      Rust
LICENÇA                SSPL/AGPL (2021+) Apache 2.0      MIT
───────────────────────────────────────────────────────────────────────
PERFORMANCE
RAM mínima             2-4 GB            2-4 GB          200-500 MB
RAM produção típica    8-32 GB/nó        8-32 GB/nó      1-8 GB
Latência típica        10-50ms           10-50ms         5-30ms
───────────────────────────────────────────────────────────────────────
ESCALA
Documentos             Bilhões           Bilhões         Dezenas de milhões
Cluster nativo         Sim (multi-nó)    Sim (multi-nó)  Não (open-source)
                                                          Sim (Cloud)
Petabytes              Sim               Sim             Não
───────────────────────────────────────────────────────────────────────
BUSCA
BM25                   ✓ nativo          ✓ nativo        ✓ nativo
Hybrid search          ✓ kNN/HNSW        ✓ kNN/HNSW      ✓ kNN (recente)
Vector search          ✓ maduro          ✓ maduro        ✓ básico
Fuzzy / typo           ✓ configurável    ✓ configurável  ✓ automático
Multilingual           ✓ 30+ idiomas     ✓ 30+ idiomas   ✓ 50+ idiomas
Aggregations           ✓ avançadas       ✓ avançadas     ✓ básicas
───────────────────────────────────────────────────────────────────────
ECOSSISTEMA
Dashboards             Kibana (pago)     OpenSearch Dash Não built-in
SDKs                   Python, JS, etc.  Python, JS, etc. Python, JS, etc.
Integrações            350+              ~200             ~50
───────────────────────────────────────────────────────────────────────
OPERAÇÃO
Curva de aprendizado   Alta              Alta            Baixa
Configuração inicial   Horas a dias      Horas a dias    Minutos
Manutenção             Complexa          Complexa        Simples
DevOps dedicado        Recomendado       Recomendado     Não necessário
───────────────────────────────────────────────────────────────────────
CUSTO
Self-hosted (small)    $50/mês           $50/mês         $10/mês
Self-hosted (médio)    $300/mês          $300/mês        $50/mês
Cloud entry-level      $95/mês           $70/mês         $30/mês
Cloud produção         $500-2000/mês     $500-2000/mês   $300-1000/mês
═══════════════════════════════════════════════════════════════════════
```

---

## Como elas se encaixam no BuscaAI

### Cenário 1 — Usar como pré-filtragem léxica (substitui índice próprio)

A engine assume o papel do índice invertido caseiro. O Qdrant continua sendo o banco vetorial.

```python
# rag_settings.py

PRE_FILTERING = {
    "enabled":  True,
    "strategy": "elasticsearch",   # bm25 (próprio) | elasticsearch | opensearch | meilisearch
    "host":     "localhost",
    "port":     9200,
    "index":    "buscaai_lexical",
    "top_n":    50000,
}

VECTOR_STORE = {
    "backend": "qdrant",
    "host":    "localhost",
    "port":    6333,
}
```

**Quando faz sentido:** quando o BuscaAI rodará em escala grande (>10M chunks), ou quando a empresa já tem Elasticsearch/OpenSearch rodando para outros fins.

### Cenário 2 — Usar como busca esparsa na híbrida (junto com o Qdrant)

A engine faz a busca lexical, o Qdrant faz a densa, e o BuscaAI funde os dois com RRF.

```python
RETRIEVAL = {
    "strategy":     "hybrid",
    "dense_backend":  "qdrant",
    "sparse_backend": "opensearch",   # busca esparsa via OpenSearch BM25
    "top_k":          50,
    "reranker":       True,
}
```

**Quando faz sentido:** quando o BM25 do índice próprio mostra limites (qualidade ou desempenho), e a empresa quer uma engine especializada.

### Cenário 3 — Substituir tudo (vector store + lexical)

Usar a engine como banco unificado — ela faz pré-filtragem, busca densa e esparsa em um único serviço.

```python
VECTOR_STORE = {
    "backend": "opensearch",        # mesma engine para tudo
    "host":    "localhost",
    "port":    9200,
}

PRE_FILTERING = {
    "enabled":  True,
    "strategy": "opensearch",       # usa a mesma engine
}
```

**Quando faz sentido:** quando o objetivo é simplificar a stack (um serviço a menos), ou quando o volume não justifica ter Qdrant separado. Tem trade-off: o Qdrant é mais maduro em vetores que Elasticsearch/OpenSearch.

### Cenário 4 — Caso hardware fraco (Meilisearch)

Meilisearch é leve o suficiente para rodar em paralelo com o BuscaAI em um único notebook.

```python
PRE_FILTERING = {
    "enabled":  True,
    "strategy": "meilisearch",
    "host":     "localhost",
    "port":     7700,
}

# Qdrant ainda é o banco vetorial, ou Chroma embedded se for ainda mais leve
VECTOR_STORE = {
    "backend": "chroma",
}
```

**Quando faz sentido:** POC, dev local, demos, hardware modesto.

---

## Tabela de decisão

```
SEU CONTEXTO                                 ENGINE RECOMENDADA
─────────────────────────────────────────────────────────────────
Empresa já usa Elasticsearch                 Elasticsearch
Empresa AWS, sem stack preexistente          OpenSearch
Precisa de logs + busca + analytics          Elasticsearch ou OpenSearch
Hardware fraco / dev local                   Meilisearch
POC ou MVP rápido                             Meilisearch
Base < 10M docs                               Meilisearch ou índice próprio
Base 10M-100M docs                            OpenSearch ou índice próprio
Base > 100M docs                              Elasticsearch ou OpenSearch
Time pequeno sem DevOps                       Meilisearch
Setor regulado (SaaS, governo)                OpenSearch (Apache 2.0)
Já tem Qdrant rodando bem                    Manter índice próprio do BuscaAI
─────────────────────────────────────────────────────────────────
```

---

## E o índice próprio do BuscaAI?

A pergunta natural: se essas engines são tão boas, por que o BuscaAI tem índice próprio?

**Razões para manter o índice próprio como padrão:**

1. **Zero dependência externa.** Funciona sem subir Elasticsearch ou OpenSearch.
2. **Suficiente para a maioria dos casos.** Até alguns milhões de chunks, o índice próprio resolve bem.
3. **Setup imediato.** Não exige nem mesmo o Meilisearch.
4. **Customização total.** Stopwords, tokenização e ranking adaptados ao caso de uso brasileiro.

**Razões para oferecer engines como alternativas:**

1. **Escala.** Acima de 10-50M chunks, engines especializadas ganham.
2. **Infraestrutura existente.** Empresas frequentemente já têm uma das três rodando.
3. **Hardware fraco.** Meilisearch pode rodar onde o BuscaAI inteiro não rode.
4. **Recursos avançados.** Aggregations, fuzzy avançado, multi-tenant maduro.

Por isso a estratégia recomendada para o BuscaAI é: **índice próprio como padrão, engines como opção plugável via settings**.

---

## Resumo executivo

```
ELASTICSEARCH
  → Veterano, robusto, pesado
  → Empresas grandes com analytics complexos
  → Cuidado com a licença SSPL

OPENSEARCH
  → Fork Apache 2.0 do Elasticsearch
  → Praticamente igual em recursos
  → Padrão para AWS e regulamentados

MEILISEARCH
  → Leve, simples, rápido
  → Bases médias, POC, hardware fraco
  → Foco em search-as-you-type

ÍNDICE PRÓPRIO DO BUSCAAI
  → Padrão out-of-the-box
  → Zero dependência
  → Suficiente para a maioria dos casos
```

Todas as três são **excelentes opções** para o pipeline RAG quando o caso de uso justifica. A flexibilidade do BuscaAI permite plugar qualquer uma delas via configuração, sem refatorar código.
