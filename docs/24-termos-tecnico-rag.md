# Termos Técnico de RAG

Todos os termos, métricas, dimensões, unidades de medida e conceitos
que aparecem em pipelines RAG — do embedding ao LLM final.

---

## Sumário

1. Dimensões e tamanhos
2. Métricas de retrieval
3. Métricas de geração e qualidade
4. Benchmarks e leaderboards
5. Métricas de performance operacional
6. Métricas de custo
7. Termos de indexação
8. Termos de chunking
9. Termos de embedding
10. Termos de retrieval
11. Termos de pós-retrieval e reranking
12. Termos de geração
13. Termos de avaliação
14. Termos de infraestrutura
15. Siglas e abreviações

---

## 1. Dimensões e tamanhos

### Dimensões de vetores

```
Dimensionalidade (d)
  Número de valores numéricos em um vetor de embedding.
  Determina a "riqueza" da representação semântica.

  Exemplos práticos:
    all-MiniLM-L6-v2        → 384d   (leve, POC)
    Google text-embedding-005→ 768d   (médio)
    BGE-M3                  → 1024d  (bom equilíbrio)
    OpenAI text-3-small     → 1536d  (padrão de mercado)
    OpenAI text-3-large     → 3072d  (premium)
    NV-Embed-v2             → 4096d  (topo)

  Impacto no armazenamento (float32, 4 bytes por dimensão):
    1 vetor × 1536d × 4 bytes = 6.144 bytes ≈ 6 KB por chunk
    1M vetores × 1536d         = ~6 GB de RAM no banco vetorial
    1M vetores × 384d          = ~1.5 GB de RAM
```

```
Dimensão reduzida (Matryoshka / MRL)
  Técnica que permite truncar vetores sem re-treinar o modelo.
  OpenAI text-3-small suporta: 1536d → 512d → 256d
  Economizia RAM no banco vetorial com perda mínima de qualidade.

  1536d → 512d: 3x menos RAM, ~92% da qualidade
  1536d → 256d: 6x menos RAM, ~85% da qualidade
```

### Tamanho de contexto

```
Context window (janela de contexto)
  Quantidade máxima de tokens que um modelo processa por chamada.
  Afeta diretamente o tamanho máximo de chunk suportado.

  Embeddings:
    all-MiniLM-L6-v2        → 256 tokens
    OpenAI text-3-small     → 8.192 tokens
    BGE-M3                  → 8.192 tokens
    Voyage voyage-4-lite    → 32.768 tokens
    Cohere Embed v4         → 131.072 tokens  (128K — maior disponível)

  LLMs:
    GPT-4o-mini             → 128.000 tokens
    Claude Sonnet 4.6       → 200.000 tokens
    Gemini 2.5 Pro          → 1.048.576 tokens (1M — maior disponível)
```

### Tamanho de chunk

```
Chunk size (tamanho de chunk)
  Número de tokens por fragmento de texto após chunking.
  Trade-off: chunks maiores = mais contexto, pior precisão.
             chunks menores = mais precisão, menos contexto.

  Valores típicos:
    128–256 tokens  → chunks muito pequenos, alta precisão, baixo contexto
    512 tokens      → padrão de mercado, bom equilíbrio
    1024 tokens     → chunks médios, contexto maior
    2048+ tokens    → apenas com modelos de embedding de contexto longo

Overlap (sobreposição)
  Tokens compartilhados entre chunks consecutivos.
  Evita cortar informação no limite entre chunks.

  Valores típicos:
    0 tokens    → sem sobreposição (risco de perder contexto)
    50 tokens   → padrão BuscaAI
    128 tokens  → sobreposição alta (mais redundância)
    20%–25%     → regra de porcentagem comum

  Fórmula de chunks por documento:
    n_chunks = ceil((doc_tokens - overlap) / (chunk_size - overlap))
```

### Parâmetros HNSW

```
HNSW_M (M)
  Número de conexões bidirecionais por nó no grafo HNSW.
  Controla o trade-off qualidade × RAM × velocidade de inserção.

  Valores típicos: 8, 16, 32, 64
  Padrão Qdrant: 16
  Mais alto → mais qualidade, mais RAM, inserção mais lenta
  Mais baixo → menos qualidade, menos RAM

HNSW_EF_CONSTRUCT (ef_construct)
  Tamanho da fila dinâmica durante a construção do índice.
  Afeta qualidade do índice construído e tempo de inserção.

  Valores típicos: 100–500
  Padrão Qdrant: 100
  Mais alto → melhor qualidade do índice, construção mais lenta

HNSW_EF (ef / ef_search)
  Tamanho da fila dinâmica durante a busca.
  Afeta recall e latência por query.

  Valores típicos: 64–512
  Padrão Qdrant: 128
  Mais alto → maior recall, maior latência
```

---

## 2. Métricas de retrieval

### Recall@K

```
O que mede:
  Dos chunks REALMENTE relevantes que existem na base,
  quantos o sistema recuperou nos top-K resultados?

Fórmula:
  Recall@K = |relevantes_recuperados ∩ top-K| / |total_relevantes|

Escala: 0.0 a 1.0 (quanto mais alto, melhor)

Exemplo:
  Base tem 8 chunks relevantes para a query.
  Sistema retornou 6 deles no top-10.
  Recall@10 = 6/8 = 0.75

Valores de referência:
  < 0.60  → ruim — resposta incompleta
  0.60–0.75 → aceitável
  0.75–0.90 → bom
  > 0.90  → excelente

Por que importa:
  Recall baixo = LLM não tem a informação necessária → resposta errada.
  É a métrica mais crítica do retrieval.
```

### Precision@K

```
O que mede:
  Dos K chunks retornados pelo sistema,
  quantos são realmente relevantes para a query?

Fórmula:
  Precision@K = |relevantes ∩ top-K| / K

Escala: 0.0 a 1.0

Exemplo:
  Sistema retornou 5 chunks (K=5).
  4 deles são relevantes.
  Precision@5 = 4/5 = 0.80

Valores de referência:
  < 0.50  → ruim — muito ruído para o LLM
  0.50–0.70 → aceitável
  0.70–0.85 → bom
  > 0.85  → excelente

Por que importa:
  Precision baixa = LLM recebe muito contexto irrelevante → alucinação.
```

### MRR (Mean Reciprocal Rank)

```
O que mede:
  Quão alto na lista ranqueada o PRIMEIRO chunk relevante aparece?
  Mede se o sistema coloca o melhor resultado no topo.

Fórmula:
  MRR = (1/N) × Σ (1 / rank_i)
  onde rank_i = posição do primeiro chunk relevante na query i

Escala: 0.0 a 1.0

Exemplo:
  Query 1: primeiro relevante na posição 1 → 1/1 = 1.00
  Query 2: primeiro relevante na posição 3 → 1/3 = 0.33
  Query 3: primeiro relevante na posição 2 → 1/2 = 0.50
  MRR = (1.00 + 0.33 + 0.50) / 3 = 0.61

Valores de referência:
  < 0.55  → ruim
  0.55–0.70 → aceitável
  0.70–0.85 → bom
  > 0.85  → excelente
```

### MAP (Mean Average Precision)

```
O que mede:
  Média da precisão calculada em cada posição onde um
  chunk relevante aparece na lista. Penaliza rankings desordenados.

Fórmula:
  AP = Σ (Precision@k × relevante_k) / total_relevantes
  MAP = média dos AP sobre todas as queries

Escala: 0.0 a 1.0
Uso: mais completo que MRR mas mais difícil de interpretar.
```

### NDCG@K (Normalized Discounted Cumulative Gain)

```
O que mede:
  Os chunks mais relevantes estão nas primeiras posições?
  Diferente de Recall/Precision, considera relevância GRADUAL
  (muito relevante > relevante > parcialmente relevante).

Fórmula:
  DCG@K = Σ (rel_i / log2(i+1))  para i=1 até K
  IDCG@K = DCG do ranking perfeito (ideal)
  NDCG@K = DCG@K / IDCG@K

Escala: 0.0 a 1.0

Exemplo:
  Posição 1: relevância 3 → 3/log2(2) = 3.00
  Posição 2: relevância 1 → 1/log2(3) = 0.63
  Posição 3: relevância 2 → 2/log2(4) = 1.00
  DCG@3 = 4.63

Valores de referência em RAG:
  < 0.60  → ruim
  0.60–0.72 → aceitável
  0.72–0.85 → bom
  > 0.85  → excelente

Por que importa:
  NDCG penaliza colocar um chunk mediocre antes de um excelente.
  Reflete melhor a experiência do usuário que Recall ou Precision.
```

### Hit Rate

```
O que mede:
  Em quantas queries pelo menos UM chunk relevante
  apareceu nos top-K resultados?

Fórmula:
  Hit Rate@K = queries_com_hit / total_queries

Escala: 0.0 a 1.0

Exemplo:
  100 queries testadas.
  92 tiveram pelo menos 1 chunk relevante no top-5.
  Hit Rate@5 = 0.92

Mais fácil de calcular que Recall, mas menos informativo.
```

### R-Precision

```
O que mede:
  Precisão nos top-R resultados, onde R = número total de
  chunks relevantes para aquela query.

Fórmula:
  R-Precision = |relevantes ∩ top-R| / R

Útil quando cada query tem um número diferente de chunks relevantes.
```

---

## 3. Métricas de geração e qualidade

### Faithfulness (Fidelidade)

```
O que mede:
  Cada afirmação da resposta está suportada pelos chunks fornecidos?
  Mede alucinação factual — LLM inventou algo que não está no contexto?

Fórmula (RAGAS):
  1. Extrai todas as afirmações atômicas da resposta.
  2. Para cada afirmação, verifica se pode ser inferida do contexto.
  3. Faithfulness = afirmações_suportadas / total_afirmações

Escala: 0.0 a 1.0

Exemplo:
  Resposta tem 5 afirmações. 4 estão no contexto. 1 foi inventada.
  Faithfulness = 4/5 = 0.80

Valores de referência:
  < 0.70  → ruim — muito alucinação
  0.70–0.80 → aceitável
  0.80–0.90 → bom
  > 0.90  → excelente

Para saúde e jurídico: exigir > 0.95.
```

### Answer Relevance (Relevância da Resposta)

```
O que mede:
  A resposta gerada realmente responde a query original?
  Detecta respostas tangenciais ou que fogem do assunto.

Como o RAGAS mede:
  1. Usa LLM para gerar N perguntas a partir da resposta.
  2. Calcula similaridade semântica entre as perguntas geradas
     e a query original.
  3. Answer Relevance = média das similaridades

Escala: 0.0 a 1.0

Valores de referência:
  < 0.65  → resposta não responde a pergunta
  0.65–0.78 → aceitável
  0.78–0.88 → bom
  > 0.88  → excelente
```

### Context Precision

```
O que mede:
  Dos chunks fornecidos ao LLM, quantos foram realmente
  úteis para gerar a resposta?
  Detecta ruído no contexto.

Fórmula (RAGAS):
  Context Precision = chunks_úteis_na_resposta / chunks_fornecidos

Escala: 0.0 a 1.0

Exemplo:
  5 chunks enviados ao LLM. LLM usou 4. 1 foi ignorado.
  Context Precision = 4/5 = 0.80

Por que importa:
  Context Precision baixa = custo desnecessário de tokens +
  risco de "lost in the middle" + potencial confusão do LLM.
```

### Context Recall

```
O que mede:
  Todas as informações necessárias para a resposta correta
  estavam presentes nos chunks fornecidos?

Fórmula (RAGAS):
  Compara afirmações da ground truth com os chunks.
  Context Recall = afirmações_da_gt_suportadas_nos_chunks / total_gt

Escala: 0.0 a 1.0
Requer ground truth (resposta correta de referência).
```

### Hallucination Rate

```
O que mede:
  Proporção de afirmações na resposta que NÃO têm suporte
  nos documentos fornecidos.

Fórmula:
  Hallucination Rate = 1 - Faithfulness

Escala: 0.0 (perfeito) a 1.0 (tudo inventado)

Targets por domínio:
  Uso geral:  < 0.15
  Corporativo: < 0.10
  Saúde:      < 0.05
  Jurídico:   < 0.05
```

### Groundedness

```
O que mede:
  Versão alternativa de Faithfulness usada por alguns frameworks.
  Cada claim da resposta tem uma citação verificável?

Diferença de Faithfulness:
  Faithfulness: afirmação está logicamente suportada pelo contexto
  Groundedness: afirmação cita explicitamente a fonte no contexto
```

### Coherence (Coerência)

```
O que mede:
  A resposta é logicamente consistente internamente?
  As afirmações não se contradizem?

Avaliada por LLM-as-judge (modelo avalia a resposta).
Escala: 1–5 ou 0.0–1.0
```

### Fluency (Fluência)

```
O que mede:
  A resposta é gramaticalmente correta e bem escrita?

Avaliada por LLM-as-judge.
Escala: 1–5
```

### Answer Correctness

```
O que mede:
  Combinação de Faithfulness + Answer Relevance ponderados.
  Métrica composta do RAGAS para qualidade geral da resposta.

Fórmula (RAGAS):
  Answer Correctness = w1 × Faithfulness + w2 × Answer Relevance
  Pesos padrão: w1=0.75, w2=0.25

Escala: 0.0 a 1.0
```

---

## 4. Benchmarks e leaderboards

### MTEB (Massive Text Embedding Benchmark)

```
O que é:
  Principal benchmark de modelos de embedding.
  56+ datasets cobrindo 8 tarefas diferentes.

Tarefas avaliadas:
  Retrieval       → busca de documentos relevantes (BEIR)
  STS             → Semantic Textual Similarity
  Classification  → classificação de texto
  Clustering      → agrupamento semântico
  Reranking       → ordenar documentos por relevância
  PairClassification → identificar pares similares
  Summarization   → avaliar qualidade de resumos
  BitextMining    → encontrar traduções paralelas

Datasets de retrieval incluídos (subconjunto BEIR):
  MSMARCO, HotpotQA, FEVER, DBPedia, TREC-COVID,
  NFCorpus, NQ, FiQA-2018, ArguAna, Touche-2020,
  Quora, SCIDOCS, SciFact, CQADupStack

Score MTEB (geral):
  Média ponderada sobre todas as tarefas e datasets.
  Modelos topo em mai/2026:
    NV-Embed-v2         → 72.31  (OSS, não comercial)
    Qwen3-Embedding-8B  → 70.58  (OSS, Apache 2.0)
    Gemini Embedding 2  → 67.71  (cloud API)
    Voyage voyage-4-large → ~67.0 (cloud API)

Por que importa para RAG:
  Score alto em MTEB Retrieval ≠ necessariamente melhor para o seu domínio.
  Sempre avaliar com seus dados reais.
```

### BEIR (Benchmarking IR)

```
O que é:
  Subconjunto do MTEB focado especificamente em retrieval.
  18 datasets de domínios heterogêneos.
  Testa generalização do modelo para domínios não vistos no treino.

Por que é importante:
  Um modelo pode ter alto MTEB geral mas baixo BEIR
  se foi treinado especificamente nos datasets MTEB.
  BEIR mede capacidade de generalização.
```

### RAGAS Score

```
O que é:
  Score composto calculado pelo framework RAGAS.
  Combina múltiplas métricas em uma nota final.

Componentes:
  Faithfulness + Answer Relevance + Context Precision + Context Recall

Cada componente ponderado igualmente por padrão.
Pode ser customizado com pesos diferentes por caso de uso.
```

### TruLens TruEval

```
Framework de avaliação da TruEra/Snowflake.
RAG Triad: Answer Relevance + Context Relevance + Groundedness.
Alternativa ao RAGAS com foco em observabilidade.
```

### LlamaIndex Evaluation

```
Framework de avaliação nativo do LlamaIndex.
Métricas: Faithfulness, Relevancy, Correctness.
Integrado com OpenAI Evals.
```

### HellaSwag / MMLU / HumanEval

```
Benchmarks de capacidade geral de LLMs.
Não específicos para RAG, mas usados para selecionar o modelo base.

MMLU: conhecimento geral (57 assuntos)
HumanEval: geração de código
HellaSwag: raciocínio de senso comum
```

### VectorDBBench

```
Benchmark específico para bancos vetoriais.
Mede: QPS, latência p99, recall@10, uso de RAM.

Métricas principais:
  QPS (Queries Per Second) @ recall 99%
  Latência p99 @ recall 99%
  RAM usage durante operação

Resultados mai/2026 (1M vetores, 1536d):
  Qdrant:    ~1.840 QPS, p99 ~35ms
  Milvus:    ~1.200 QPS, p99 ~50ms
  pgvector:  ~400  QPS, p99 ~45ms
```

### Agentset Reranker Leaderboard

```
Benchmark específico para rerankers.
Mede nDCG@10 em múltiplos datasets de retrieval.

Formato de score:
  nDCG@10 médio sobre todos os datasets testados.
  Valores típicos dos melhores: 0.69–0.74
```

---

## 5. Métricas de performance operacional

### Latência

```
Latência total de uma query (end-to-end)
  Tempo desde a query do usuário até a resposta final.
  Inclui todas as etapas do pipeline.

Latência de retrieval
  Tempo até retornar os chunks (sem geração).
  Meta BuscaAI: p95 ≤ 500ms

Latência p50 (mediana)
  50% das queries completam em menos que esse tempo.

Latência p95
  95% das queries completam em menos que esse tempo.
  Padrão de SLA mais usado.

Latência p99
  99% das queries completam em menos que esse tempo.
  Detecta outliers e casos piores.

TTFT (Time To First Token)
  Tempo até o primeiro token da resposta começar a aparecer.
  Crítico para UX em streaming.
  Meta: < 1s para boa experiência

Valores típicos por etapa (BuscaAI padrão):
  Pré-filtragem BM25:   5–30ms
  Busca vetorial:       20–80ms
  RRF fusão:            <5ms
  Cross-encoder (30 docs): 80–150ms (CPU)
  LLM geração:          200ms–2s (depende do modelo)
  Cache hit:            1–3ms
  Total sem reranker:   50–150ms
  Total com reranker:   200–600ms
  Total com LLM:        500ms–3s
```

### Throughput

```
QPS (Queries Per Second)
  Número de queries que o sistema processa por segundo.

RPS (Requests Per Second)
  Equivalente ao QPS mas para a API HTTP.

Concurrent queries (queries simultâneas)
  Número de queries processadas em paralelo.
  Meta BuscaAI: 50 queries simultâneas.

Tokens por segundo (tok/s)
  Velocidade de geração do LLM.
  Groq Llama 3.1 8B: 500+ tok/s (mais rápido cloud)
  GPT-4o: ~80–120 tok/s
  Claude Sonnet: ~60–100 tok/s
```

### Uptime e disponibilidade

```
Uptime %
  Percentual de tempo que o sistema está disponível.

  99%     = até 87.6h de downtime/ano (~7.3h/mês)
  99.9%   = até 8.76h/ano (~43.8min/mês)
  99.99%  = até 52.6min/ano (~4.4min/mês)

SLA (Service Level Agreement)
  Acordo formal sobre uptime mínimo garantido.

RTO (Recovery Time Objective)
  Quanto tempo para o sistema voltar após falha.

RPO (Recovery Point Objective)
  Quanto de dados pode ser perdido em caso de falha.
  (ex: RPO 4h = backups a cada 4 horas)
```

---

## 6. Métricas de custo

### Custo de tokens

```
Token
  Unidade de cobrança das APIs de LLM e embedding.
  1 token ≈ 4 caracteres ≈ 0.75 palavras (inglês)
  1 token ≈ 3.5 caracteres (PT-BR, idiomas com acentos)

  "A metformina trata diabetes" = ~6 tokens
  Chunk de 512 tokens ≈ ~385 palavras

Input tokens
  Tokens enviados ao modelo (query + contexto + system prompt).
  Cobrados por 1M tokens.

Output tokens
  Tokens gerados na resposta.
  Geralmente 3–10x mais caros que input.

1M tokens
  Unidade padrão de preço das APIs.
  1 livro médio ≈ 100.000 tokens
  1M tokens ≈ 10 livros médios

Exemplo de cálculo:
  Query: 50 tokens input
  Contexto (5 chunks × 500 tokens): 2.500 tokens input
  System prompt: 200 tokens input
  Resposta: 400 tokens output
  Total: 2.750 input + 400 output

  Custo (GPT-4o-mini: $0.40 input / $1.60 output por 1M):
  = (2.750 × 0.40 + 400 × 1.60) / 1.000.000
  = (1.100 + 640) / 1.000.000
  = $0.00174 por query
  = $1.74 por 1.000 queries
```

### Custo de embedding

```
Custo de ingestão (one-time)
  Custo para gerar embeddings de todos os documentos da base.
  Pago uma vez (ou quando a base muda).

  Exemplo: 100k docs × 500 tokens = 50M tokens
  OpenAI text-3-small: 50M × $0.02/1M = $1.00

Custo de query embedding
  Custo para embedar a query de cada usuário.
  Queries são curtas (~50 tokens), custo mínimo.

  Exemplo: 10.000 queries/mês × 50 tokens = 500k tokens
  OpenAI text-3-small: 500k × $0.02/1M = $0.01/mês (insignificante)
```

### Custo de reranking

```
Por 1M tokens
  Jina v2: $0.02/1M
  Pinecone: $0.08/1M
  Cohere: $2.00/1M

Por 1k buscas (50 docs × 500 tokens = 25M tokens por 1k buscas)
  Jina: $0.50/1k buscas
  Cohere: $2.00/1k buscas

Custo mensal para 10k buscas:
  Jina:   $5/mês
  Cohere: $20/mês
  MiniLM: $0 (self-hosted)
```

---

## 7. Termos de indexação

```
Índice vetorial
  Estrutura de dados que armazena vetores e permite busca
  eficiente por similaridade.

HNSW (Hierarchical Navigable Small World)
  Algoritmo de índice vetorial aproximado.
  Cria um grafo em camadas para busca eficiente.
  Padrão em Qdrant, Weaviate, pgvector.

IVF (Inverted File Index)
  Alternativa ao HNSW. Divide o espaço em clusters (células).
  Busca apenas nos clusters mais próximos.
  Mais econômico em RAM, menos preciso.

Flat / Exact Search
  Busca exata por força bruta. Compara query com todos os vetores.
  100% de recall mas O(n) — não escala para bases grandes.
  Adequado até ~100k vetores.

Quantização escalar (SQ / int8)
  Comprime vetores float32 (4 bytes) para int8 (1 byte).
  Reduz RAM em 4x com ~1% de perda de recall.

Quantização binária (BQ)
  Comprime vetores para 1 bit por dimensão.
  Reduz RAM em 32x com maior perda de qualidade.
  BBQ (Better Binary Quantization) do Elasticsearch mitiga a perda.

Product Quantization (PQ)
  Divide vetor em subvetores, quantiza cada um.
  Compressão mais agressiva (até 64x), qualidade intermediária.

Payload / Metadata
  Dados associados a cada vetor no banco vetorial.
  Usados para filtros: source, doc_id, data, tipo, tenant_id, etc.

Upsert
  Operação de insert-or-update em banco vetorial.
  Se o ID já existe: atualiza. Se não: insere.

Collection (coleção)
  Conjunto de vetores no mesmo espaço dimensional no Qdrant.
  Equivalente a uma tabela em SQL.

Shard
  Fragmento de um índice em bancos distribuídos.
  Permite distribuir dados entre múltiplos nós.

Replica
  Cópia de um shard para alta disponibilidade.
```

### BM25 e índice invertido

```
BM25 (Best Match 25)
  Algoritmo de ranking léxico. Evolução do TF-IDF.
  Considera frequência do termo, raridade e tamanho do documento.

  Parâmetros:
    k1: saturação de frequência de termo (padrão: 1.2–2.0)
        alto → frequência pesa mais
        baixo → satura rapidamente
    b:  normalização por tamanho (padrão: 0.75)
        1.0 → normalização total
        0.0 → sem normalização

TF (Term Frequency)
  Frequência com que um termo aparece em um documento.

IDF (Inverse Document Frequency)
  Raridade do termo na coleção.
  Termos raros têm IDF alto (mais discriminativos).
  Termos comuns ("de", "o", "a") têm IDF baixo.

Índice invertido
  Estrutura que mapeia: token → lista de documentos que o contêm.
  Base de qualquer engine de busca lexical.

Stopwords
  Palavras muito comuns removidas antes da indexação.
  PT-BR: "de", "a", "o", "que", "em", "para"...

Stemming
  Reduz palavras à raiz. "correndo" → "corr"
  Aumenta recall mas perde precisão.

Lemmatização
  Reduz à forma base. "correndo" → "correr"
  Mais preciso que stemming, mais caro computacionalmente.

Tokenização
  Processo de dividir texto em tokens individuais.
  "olá mundo" → ["olá", "mundo"]
```

---

## 8. Termos de chunking

```
Chunking
  Processo de dividir documentos longos em fragmentos menores
  para indexação e retrieval.

Chunk
  Um fragmento de texto com tamanho definido.
  Unidade mínima de retrieval no RAG.

Chunk size
  Tamanho do chunk em tokens. Ver seção 1.

Overlap (sobreposição)
  Tokens repetidos entre chunks consecutivos. Ver seção 1.

Recursive chunking
  Divide o texto em hierarquia: parágrafo → frase → palavra.
  Tenta não cortar dentro de unidades semânticas naturais.

Semantic chunking
  Divide o texto onde ocorre mudança de significado.
  Usa embedding para detectar fronteiras semânticas.
  Mais preciso, mais caro.

Fixed-size chunking
  Divide em chunks de exatamente N tokens, independente de contexto.
  Simples, pode cortar sentenças no meio.

Sliding window
  Janela deslizante com overlap. Equivalente a recursive com overlap alto.

Sentence chunking
  Divide em chunks de N sentenças.
  Mais natural que fixed-size para textos narrativos.

Hierarchical chunking (RAPTOR)
  Chunks + resumos dos chunks + resumos dos resumos.
  Permite responder queries gerais e específicas.

Parent chunk
  Chunk maior que engloba múltiplos child chunks.
  Usado no pattern "small-to-big retrieval":
  recupera child (preciso) e envia parent (com mais contexto) ao LLM.

Proposition-based chunking
  Divide texto em afirmações atômicas (proposições).
  Cada chunk = uma afirmação factual independente.
  Máxima precisão, custo computacional alto (requer LLM).
```

---

## 9. Termos de embedding

```
Embedding
  Representação numérica densa de texto em espaço vetorial.
  Textos semanticamente similares ficam próximos.

Vetor denso
  Embedding padrão. Todas as dimensões têm valores.
  Captura semântica.

Vetor esparso
  Embedding onde a maioria dos valores é zero.
  Captura termos léxicos. Base do SPLADE.

Embedding multilíngue
  Modelo treinado em múltiplos idiomas.
  Permite busca cross-lingual (query PT, doc EN).

Bi-encoder
  Arquitetura que codifica query e documentos SEPARADAMENTE.
  Eficiente para retrieval em larga escala.
  Limitação: não vê interação entre query e documento.

Cross-encoder
  Arquitetura que processa query e documento JUNTOS.
  Muito mais preciso que bi-encoder.
  Caro — não escala para bases grandes (usado no reranking).

Sentence Transformer
  Classe de modelos baseados em BERT/RoBERTa para embeddings.
  Treinados com contrastive learning para similaridade semântica.

Contrastive learning
  Técnica de treino que aproxima pares positivos e afasta negativos.
  Base do treino de modelos de embedding modernos.

Hard negatives
  Exemplos negativos difíceis (similares mas não relevantes).
  Usados no treino para melhorar discriminação do modelo.

Fine-tuning de embedding
  Adaptar um modelo de embedding pré-treinado para domínio específico.
  Pode melhorar 10–20% em domínios técnicos (jurídico, médico).

Cosine similarity (similaridade de cosseno)
  Medida de similaridade entre vetores.
  Ignora magnitude, foca na direção.

  cos(A, B) = (A · B) / (|A| × |B|)

  Escala: -1.0 (opostos) a 1.0 (idênticos)
  Valores típicos em RAG:
    > 0.90: muito similar
    0.75–0.90: similar
    0.60–0.75: relacionado
    < 0.60: pouco relacionado

Dot product (produto escalar)
  Alternativa ao cosseno. Considera magnitude.
  Mais rápido de calcular. Padrão quando vetores são normalizados.

Euclidean distance (distância euclidiana)
  Distância geométrica entre vetores.
  Menos usada em RAG que cosseno.

L2 normalization
  Normaliza vetores para magnitude = 1.
  Após normalização, dot product = cosine similarity.

MRL (Matryoshka Representation Learning)
  Técnica de treino que permite truncar dimensões.
  Vetor de 1536d pode ser truncado para 512d sem re-treinar.

SPLADE (SParse Lexical AnD Expansion)
  Modelo que gera vetores esparsos no espaço do vocabulário.
  Combina BM25 léxico com entendimento semântico.
  BGE-M3 inclui SPLADE internamente.
```

---

## 10. Termos de retrieval

```
Retrieval / Recuperação
  Etapa de buscar chunks relevantes para uma query.

Dense retrieval (busca densa)
  Busca por similaridade semântica via embeddings.

Sparse retrieval (busca esparsa)
  Busca léxica via BM25 ou SPLADE.

Hybrid retrieval (busca híbrida)
  Combinação de dense + sparse com fusão de rankings.

RRF (Reciprocal Rank Fusion)
  Algoritmo de fusão de rankings.
  score = Σ 1/(k + rank_i), onde k=60 (padrão)
  Robusto, sem necessidade de normalizar scores.

ANN (Approximate Nearest Neighbor)
  Busca aproximada de vizinhos mais próximos.
  Troca um pouco de recall por muito ganho de velocidade.
  HNSW é a implementação ANN mais usada em RAG.

kNN (k-Nearest Neighbors)
  Busca pelos K vetores mais próximos.
  Exact kNN = busca exata (lenta em escala)
  Approximate kNN = ANN (rápido em escala)

Top-K
  Número de candidatos retornados pelo retrieval.
  Tipicamente K=50 antes do reranker, K=5 para o LLM.

MMR (Maximal Marginal Relevance)
  Algoritmo de diversificação de resultados.
  Penaliza chunks muito similares entre si.
  λ controla trade-off relevância × diversidade.

Pre-filtering (pré-filtragem)
  Filtro léxico antes da busca vetorial.
  Reduz universo de busca de milhões para dezenas de milhares.

Metadata filtering
  Filtros estruturais por campos do payload.
  Ex: source="contrato.pdf" AND data > "2024-01-01"
  Filtered HNSW no Qdrant permite filtros sem degradar performance.

Multi-index retrieval
  Busca em múltiplos índices especializados simultaneamente.

Query routing
  Direcionar queries para o pipeline mais adequado.

Query expansion
  Gerar variações da query para aumentar recall.

HyDE (Hypothetical Document Embedding)
  Gerar resposta hipotética e usar seu embedding para buscar.
  Melhora recall em queries curtas ou vagas.

Step-back prompting
  Abstrair a query para um nível conceitual mais alto.
  Buscar contexto geral + específico.

Query decomposition
  Dividir queries complexas em sub-queries independentes.

Multi-hop retrieval
  Retrieval em múltiplas rodadas.
  Resposta da rodada 1 informa a busca da rodada 2.
```

---

## 11. Termos de pós-retrieval e reranking

```
Reranking
  Reordenar os candidatos do retrieval por relevância.
  Usa cross-encoder mais preciso que o bi-encoder inicial.

nDCG@10
  Métrica padrão de qualidade de rerankers.
  Normalized Discounted Cumulative Gain nos top-10 resultados.

Cross-encoder reranker
  Processa (query, chunk) juntos. Muito mais preciso que bi-encoder.

LLM reranker
  Usa LLM para avaliar e ordenar relevância dos candidatos.

Context compression
  Remover partes irrelevantes dos chunks antes de enviar ao LLM.

Prompt packing
  Organizar chunks no prompt para mitigar "lost in the middle".

Lost in the middle
  Fenômeno onde LLMs ignoram informações no meio do contexto longo.
  Lembram melhor o início e o fim.

Knowledge strips
  Decompor chunks em afirmações atômicas.
  Descartar afirmações irrelevantes. Reconstruir contexto limpo.

Score threshold (threshold de score)
  Score mínimo para um chunk ser considerado relevante.
  Chunks abaixo do threshold são descartados.

Citation grounding
  LLM é instruído a citar a fonte de cada afirmação na resposta.

Final top-K
  Número de chunks enviados ao LLM após reranking.
  Tipicamente 3–10.
```

---

## 12. Termos de geração

```
RAG (Retrieval-Augmented Generation)
  Paradigma que combina retrieval de documentos com geração de LLM.
  LLM recebe query + contexto recuperado → gera resposta.

Augmented prompt
  Prompt que inclui query + chunks recuperados + system prompt.

System prompt
  Instrução permanente que define comportamento do LLM.
  "Responda apenas com base nos documentos fornecidos."

Few-shot prompting
  Incluir exemplos de perguntas e respostas no prompt.
  Guia o LLM para o formato desejado.

Chain-of-thought (CoT)
  Instruir o LLM a mostrar seu raciocínio passo a passo.
  Melhora qualidade em perguntas complexas.

Temperature
  Controla aleatoriedade da geração.
  0.0 = determinístico (mesmo output para mesmo input)
  0.7–1.0 = criativo e variado
  Para RAG: usar 0.0 ou próximo (mais factual)

Max tokens
  Limite máximo de tokens na resposta gerada.

Streaming
  Enviar tokens da resposta conforme são gerados.
  Melhora UX — usuário vê a resposta aparecendo.
  SSE (Server-Sent Events) ou WebSocket.

Context window utilization
  Percentual da janela de contexto usado.
  Alto utilization = risco de truncar contexto importante.

Token budget
  Limite de tokens definido para o contexto do RAG.
  system_prompt + chunks + query + resposta ≤ context_window

Prompt injection
  Ataque onde conteúdo malicioso nos documentos tenta
  manipular o comportamento do LLM.

Grounding
  Ancorar a resposta do LLM em fontes documentadas.
  Reduz alucinação.
```

---

## 13. Termos de avaliação

```
RAGAS
  Framework de avaliação de RAG (Es et al. 2024).
  4 métricas: Faithfulness, Answer Relevance,
              Context Precision, Context Recall.
  Usa LLM como juiz.

LLM-as-judge
  Usar um LLM para avaliar a qualidade das respostas de outro LLM.
  Padrão em avaliações automáticas de RAG.

Ground truth
  Resposta correta de referência para uma query.
  Necessária para Context Recall e Answer Correctness.

Golden dataset
  Conjunto de queries + ground truths curado manualmente.
  Base para avaliação sistemática do pipeline.

A/B testing
  Comparar dois pipelines com o mesmo conjunto de queries.
  Identifica qual configuração tem melhor performance.

Offline evaluation
  Avaliar com dataset pré-construído. Rápido e reproduzível.

Online evaluation
  Avaliar com queries reais em produção.
  Mais representativo, mais difícil de controlar.

Human evaluation
  Avaliadores humanos julgam qualidade das respostas.
  Gold standard — mais preciso mas lento e caro.

Component evaluation
  Avaliar cada componente do pipeline separadamente.
  Retrieval score separado de generation score.

End-to-end evaluation
  Avaliar o pipeline completo de ponta a ponta.
  Captura interações entre componentes.

Ablation study
  Remover componentes para medir seu impacto individual.
  "Como Faithfulness muda sem o reranker?"

Regression testing
  Verificar que mudanças não pioram métricas existentes.
  Parte do CI/CD do pipeline RAG.
```

---

## 14. Termos de infraestrutura

```
Pipeline
  Sequência de transformações aplicadas a dados ou queries.

Worker
  Processo que executa tarefas assíncronas (Celery).

Job
  Unidade de trabalho enfileirada (ex: ingerir um documento).

Queue (fila)
  Estrutura para processamento assíncrono de jobs (Redis/RabbitMQ).

Checkpoint
  Salvar progresso intermediário para retomar em caso de falha.

Retry
  Retentar uma operação que falhou.
  Backoff exponencial: espera 1s, 2s, 4s, 8s entre tentativas.

Dead letter queue (DLQ)
  Fila para jobs que falharam após todas as tentativas.

Cache hit
  Query encontrada no cache → resposta instantânea.

Cache miss
  Query não encontrada no cache → pipeline completo executado.

TTL (Time To Live)
  Tempo até um item no cache expirar.

Cache invalidation
  Remover itens do cache quando os dados subjacentes mudam.

Rate limiting
  Limitar número de requisições por unidade de tempo.
  Protege contra sobrecarga e abuso.

Backpressure
  Mecanismo para limitar a taxa de ingestão quando o sistema está sobrecarregado.

Observability
  Capacidade de entender o estado interno do sistema
  por meio de logs, métricas e traces.

Prometheus
  Sistema de coleta de métricas time-series.

Grafana
  Plataforma de visualização de métricas.

Langfuse
  Plataforma de observabilidade específica para LLMs e RAG.
  Rastreia chamadas, latência, custo e qualidade.

Span / Trace
  Unidades de rastreamento distribuído.
  Permitem ver quanto tempo cada etapa do pipeline levou.

p50 / p95 / p99
  Percentis de latência.
  p99 = 99% das requisições completam em menos que esse tempo.

SLO (Service Level Objective)
  Meta interna de performance. Ex: p95 latência ≤ 500ms.

SLA (Service Level Agreement)
  Acordo formal com penalidades se SLO não for cumprido.

Multi-tenancy
  Múltiplos clientes (tenants) usando a mesma infraestrutura
  com isolamento de dados e recursos.

Namespace
  Isolamento lógico de dados dentro de um serviço.
  Cada tenant tem seu namespace no Qdrant.
```

---

## 15. Siglas e abreviações

```
ANN   Approximate Nearest Neighbor
API   Application Programming Interface
BBQ   Better Binary Quantization
BEIR  Benchmarking Information Retrieval
BM25  Best Match 25
CoT   Chain-of-Thought
CPU   Central Processing Unit
DLQ   Dead Letter Queue
DPR   Dense Passage Retrieval (Karpukhin et al. 2020)
ELSER Elastic Learned Sparse EncodeR
FLOP  Floating Point Operation
GPRC  gRPC (Google Remote Procedure Call)
GPU   Graphics Processing Unit
HNSW  Hierarchical Navigable Small World
HyDE  Hypothetical Document Embedding
IDF   Inverse Document Frequency
IVF   Inverted File (index)
JSON  JavaScript Object Notation
JWT   JSON Web Token
KV    Key-Value
LLM   Large Language Model
MAP   Mean Average Precision
MMLU  Massive Multitask Language Understanding
MQL   Metadata Query Language
MRR   Mean Reciprocal Rank
MRL   Matryoshka Representation Learning
MTEB  Massive Text Embedding Benchmark
NLP   Natural Language Processing
NDCG  Normalized Discounted Cumulative Gain
OCR   Optical Character Recognition
ORM   Object-Relational Mapping
PG    PostgreSQL
PQ    Product Quantization
QPS   Queries Per Second
RAG   Retrieval-Augmented Generation
RAPTOR Recursive Abstractive Processing for Tree-Organized Retrieval
RRF   Reciprocal Rank Fusion
RPO   Recovery Point Objective
RTO   Recovery Time Objective
SDK   Software Development Kit
SLA   Service Level Agreement
SLO   Service Level Objective
SPLADE SParse Lexical AnD Expansion
SQ    Scalar Quantization
SSE   Server-Sent Events
STS   Semantic Textual Similarity
TF    Term Frequency
TTFT  Time To First Token
TTL   Time To Live
VRAM  Video RAM (memória da GPU)
```

---

## Referências das métricas

```
RAGAS framework: Es et al. (2024). RAGAS: Automated Evaluation of RAG.
MTEB benchmark: Muennighoff et al. (2023). MTEB: Massive Text Embedding Benchmark.
BEIR benchmark: Thakur et al. (2021). BEIR: Benchmarking IR with Diverse Datasets.
BM25: Robertson & Zaragoza (2009). The Probabilistic Relevance Framework.
RRF: Cormack et al. (2009). Reciprocal Rank Fusion. SIGIR.
HNSW: Malkov & Yashunin (2020). Efficient ANN Search.
SPLADE: Formal et al. (2021). SPLADE: Sparse Lexical and Expansion.
MRL: Kusupati et al. (2022). Matryoshka Representation Learning.
HyDE: Gao et al. (2022). Precise Zero-Shot Retrieval with HyDE.
```

---

## 16. Paradigmas e tipos de RAG

```
Naive RAG
  Pipeline RAG básico e linear. Proposto por Lewis et al. (2020).
  Etapas: indexação → retrieval → geração. Sem otimizações.
  Baseline de qualidade. Adequado para POC.

Advanced RAG
  Evolução do Naive com otimizações antes e depois do retrieval.
  Pré-retrieval: query expansion, HyDE, reformulação.
  Pós-retrieval: reranking, compressão de contexto.
  Ainda mantém estrutura linear.

Modular RAG
  Paradigma dominante em 2024–2026 (Gao et al. 2024).
  Pipeline como grafo configurável de módulos plugáveis.
  6 módulos: Indexing, Pre-Retrieval, Retrieval,
             Post-Retrieval, Orchestration, Generation.
  Naive e Advanced RAG são casos especiais de Modular RAG.

Adaptive RAG
  Pipeline adapta-se à complexidade da query (Jeong et al. 2024).
  Queries simples: LLM responde direto (sem retrieval).
  Queries médias: retrieval padrão.
  Queries complexas: retrieval multi-hop.

Self-RAG
  LLM decide ativamente quando buscar, o que buscar e avalia resultados.
  5 reflection tokens: RETRIEVE, ISREL, ISSUP, ISUSE, ISCON.
  4–8 chamadas de LLM por query. Máxima qualidade, custo alto.
  Asai et al. (2024), ICLR.

CRAG (Corrective RAG)
  Avalia qualidade dos documentos recuperados.
  Três estados: CORRECT, AMBIGUOUS, INCORRECT.
  Se INCORRECT: descarta e faz busca web.
  Knowledge strips: decompõe chunks em afirmações atômicas.
  Yan et al. (2024), arXiv:2401.15884.

GraphRAG
  Extrai entidades e relações durante ingestão → grafo de conhecimento.
  Dois modos: LOCAL (entidade específica) e GLOBAL (comunidades).
  Leiden algorithm para detecção de comunidades.
  Edge et al. (2024), Microsoft Research.

Agentic RAG
  LLM age como agente: planeja, usa ferramentas, itera.
  RAG é uma das ferramentas do agente (junto com calculadora, SQL, etc.).
  Maior flexibilidade. Custo muito alto (5–20 LLM calls/query).

RAG Fusion
  Gera múltiplas variações da query → retrieval para cada uma → RRF.
  Aumenta recall em domínios com vocabulário variado.

RAPTOR
  Recursive Abstractive Processing for Tree-Organized Retrieval.
  Indexação hierárquica: chunks → resumos → resumos dos resumos.
  Permite responder queries gerais e específicas na mesma base.
  Sarthi et al. (2024), ICLR.

Multi-Vector RAG
  Cada documento gera múltiplos vetores: chunk completo,
  resumo, perguntas hipotéticas, entidades extraídas.
  Aumenta recall ao ter múltiplas representações do mesmo conteúdo.

Speculative RAG
  LLM gera resposta especulativa (sem retrieval) → retrieval verifica.
  Reduz latência quando o LLM provavelmente sabe a resposta.
  Risco: hipótese errada polui o retrieval.

Multimodal RAG
  Estende RAG para dados além de texto: imagens, tabelas, gráficos.
  Embeddings visuais (CLIP, GPT-4V) no mesmo espaço vetorial.
  Gemini Embedding 2 suporta texto + imagem + vídeo + áudio.

Long Context RAG
  Coloca toda (ou grande parte) da base no contexto do LLM.
  Funciona para bases pequenas com modelos de 1M+ tokens (Gemini 2.5 Pro).
  Não é RAG tradicional — sem etapa explícita de retrieval.

Two-Stage Retrieval
  Estágio 1: bi-encoder recupera candidatos (recall alto).
  Estágio 2: cross-encoder reordena candidatos (precisão alta).
  Base arquitetural do reranking moderno.

Context Stuffing
  Técnica alternativa ao RAG: incluir todo o contexto relevante
  no prompt sem retrieval. Funciona com LLMs de contexto longo.
  Mais simples que RAG, custo de tokens muito maior.

Noise Robustness
  Capacidade do sistema de ignorar contexto irrelevante no prompt.
  Métrica de robustez: qualidade da resposta com X% de noise injetado.

Counterfactual Robustness
  Capacidade de ignorar contexto que contradiz o conhecimento interno.
  LLM não deve ser "enganado" por documentos incorretos no contexto.

Negative Rejection
  Capacidade de recusar responder quando nenhum contexto relevante
  está disponível, em vez de alucinar.
  "Não encontrei informações suficientes" é melhor que inventar.

Information Integration
  Capacidade de sintetizar informações de múltiplos chunks
  em uma resposta coerente.
```

---

## 17. Parâmetros de geração do LLM

```
Temperature (temperatura)
  Controla aleatoriedade da distribuição de probabilidade dos tokens.
  0.0 → determinístico (mesmo input = mesmo output sempre)
  0.7 → padrão criativo
  1.0 → muito aleatório
  Para RAG factual: 0.0 ou 0.1 (máxima consistência)

Top-P (nucleus sampling)
  Amostra dos tokens cuja probabilidade acumulada = P.
  Top-P = 0.9 → considera apenas os tokens mais prováveis
          que somam 90% de probabilidade.
  Alternativa ao temperature para controlar diversidade.
  Top-P e temperature raramente são usados juntos — escolha um.

Top-K sampling
  Amostra apenas dos K tokens mais prováveis.
  Top-K = 40 → considera apenas os 40 tokens mais prováveis.
  Menos flexível que Top-P em distribuições variáveis.

Greedy decoding
  Seleciona sempre o token com maior probabilidade.
  Equivalente a Temperature = 0.0 ou Top-K = 1.
  Determinístico, mas pode ficar preso em repetições.

Beam search
  Mantém B hipóteses (beams) em paralelo.
  Beam width B = 1 → greedy decoding.
  Beam width B = 5 → 5 hipóteses simultâneas.
  Mais usado em tradução automática que em RAG moderno.

Frequency penalty
  Penaliza tokens que já apareceram na resposta.
  0.0 → sem penalidade
  2.0 → penalidade máxima (evita muita repetição)
  Útil para respostas longas que tendem a repetir.

Presence penalty
  Penaliza qualquer token que apareceu ao menos uma vez.
  Diferente do frequency: é binário (apareceu ou não).
  Força o modelo a usar vocabulário mais variado.

Stop tokens (stop sequences)
  Sequências que interrompem a geração imediatamente.
  Ex: ["\n\n", "Usuário:", "###"]
  Útil para formatos estruturados ou controle de turno.

Max tokens (max_tokens / max_new_tokens)
  Número máximo de tokens que o modelo pode gerar.
  Previne respostas muito longas e custo excessivo.

Logprobs
  Log-probabilidades dos tokens gerados.
  Útil para calcular confiança da resposta.
  Alguns modelos retornam logprobs via API (OpenAI, Anthropic).

Seed
  Semente para reprodutibilidade de resultados.
  Mesmo seed + mesmo input = mesmo output (quando suportado).

Repetition penalty
  Parâmetro similar ao frequency_penalty.
  Usado em modelos HuggingFace e Ollama.
  > 1.0 → penaliza repetição.

KV Cache (Key-Value Cache)
  Cache das ativações de atenção para tokens já processados.
  Acelera geração de tokens subsequentes.
  Prompt caching das APIs usa este mecanismo.

Prompt caching
  APIs (Anthropic, OpenAI, Google) cacheiam o início do prompt.
  Se o mesmo prefixo for reutilizado: desconto de até 90%.
  Muito útil em RAG com system prompt longo e fixo.

Context utilization
  Percentual da janela de contexto preenchida.
  Alto → risco de truncar informação importante.
  Monitorar para ajustar top-K do retrieval.

Token budget
  Planejamento da distribuição de tokens no prompt:
  system_prompt + few-shot + query + chunks + resposta ≤ context_window
  Exemplo com GPT-4o-mini (128K context):
    system_prompt:  300 tokens
    query:           50 tokens
    5 chunks × 512: 2.560 tokens
    resposta:       500 tokens
    Total:          3.410 tokens (2.7% do contexto — muito eficiente)
```

---

## 18. Arquiteturas de modelos de linguagem

```
Transformer
  Arquitetura base de todos os LLMs e modelos de embedding modernos.
  Proposta por Vaswani et al. (2017). "Attention is All You Need".
  Base: mecanismo de self-attention + feed-forward layers.

Self-Attention (atenção própria)
  Mecanismo que permite cada token "olhar" para todos os outros tokens.
  Calcula relevância entre todos os pares de tokens da sequência.
  Complexidade: O(n²) em relação ao comprimento da sequência.

Multi-Head Attention
  Múltiplas "cabeças" de atenção paralelas.
  Cada cabeça aprende padrões de atenção diferentes.
  Saídas concatenadas e projetadas.

BERT (Bidirectional Encoder Representations from Transformers)
  Encoder-only transformer. Vê contexto bidireccional.
  Treinado com Masked Language Modeling (MLM).
  Base de modelos de embedding (Sentence-BERT, BGE, etc.).

MLM (Masked Language Modeling)
  Tarefa de pré-treino: prevê tokens mascarados.
  "O [MASK] tratou o paciente." → "médico"
  Permite treino bidirecional (vê contexto antes e depois).

GPT / Decoder-only
  Transformer só com decoder. Gera texto autoregressivamente.
  Causal LM: cada token só vê tokens anteriores (não futuros).
  Base de todos os LLMs modernos: GPT, LLaMA, Gemini, Claude.

T5 (Text-to-Text Transfer Transformer)
  Encoder-decoder. Trata tudo como problema de seq2seq.
  Usado em rerankers (MonoT5) e classificadores.

Encoder-Decoder
  Arquitectura completa: encoder processa input, decoder gera output.
  Usado em tradução automática, sumarização, T5.

Late Interaction (ColBERT)
  Mantém representação por token (não colapsa em um único vetor).
  MaxSim: para cada token da query, encontra o token de doc mais similar.
  Score = soma dos MaxSim de todos os tokens da query.
  Mais preciso que bi-encoder, menos caro que cross-encoder.

MaxSim
  Operação central do ColBERT.
  Para cada token da query: maximum similarity com qualquer token do doc.
  Score final = soma dos MaxSim sobre todos os tokens da query.

Causal Language Modeling (CLM)
  Tarefa de pré-treino dos modelos decoder.
  Prevê o próximo token dado todos os anteriores.
  Treinamento unidirecional (da esquerda para a direita).

Instruction tuning
  Fine-tuning com pares (instrução, resposta).
  Torna o modelo capaz de seguir instruções em linguagem natural.
  Base dos modelos "chat" modernos.

RLHF (Reinforcement Learning from Human Feedback)
  Técnica de alinhamento: humanos ranqueiam respostas,
  reward model aprende as preferências,
  PPO ajusta o LLM para maximizar o reward.
  GPT-4, Claude e Gemini usam variantes de RLHF.

DPO (Direct Preference Optimization)
  Alternativa ao RLHF sem precisar de reward model separado.
  Treina diretamente nas preferências humanas.
  Mais simples de implementar que RLHF.

LoRA (Low-Rank Adaptation)
  Técnica de fine-tuning eficiente.
  Adiciona matrizes de baixo rank (A×B) em vez de atualizar pesos completos.
  Reduz parâmetros treináveis em 100–10.000x.
  Muito usado para adaptar LLMs a domínios específicos.

GGUF / GGML
  Formatos de arquivo para modelos quantizados.
  GGUF é a evolução do GGML, usado pelo llama.cpp e Ollama.
  Permite rodar modelos grandes em CPU com quantização (Q4, Q8, etc.).
  Q4_K_M = 4 bits por peso, variante K com médias ajustadas.

Quantização de modelo
  Reduzir precisão dos pesos do modelo para economizar memória.
  float32 (32 bits) → float16 → int8 → int4
  Trade-off: menos VRAM, um pouco menos de qualidade.
  Quantização 4-bit (Q4): modelo de 70B requer ~35GB → ~40GB VRAM.

Ollama
  Ferramenta para rodar modelos LLM localmente.
  Suporta GGUF via llama.cpp.
  API REST compatível com OpenAI.
  Modelos: Llama, Mistral, Phi, Qwen, Gemma e outros.
```

---

## 19. Termos de treino de embedding

```
Contrastive loss
  Função de perda que aproxima pares positivos e afasta negativos.
  Base do treino de modelos de embedding.

Triplet loss
  Variante do contrastive: (anchor, positive, negative).
  Minimiza distância(anchor, positive) − distância(anchor, negative).

In-batch negatives
  Usar outros exemplos do mesmo batch como negativos.
  Estratégia eficiente — não precisa minerar negativos explicitamente.

Hard negatives (negativos difíceis)
  Exemplos negativos similares ao positivo mas não relevantes.
  Ex: busca por "metformina dosagem adulto"
      negativo fácil: "receita de bolo"
      negativo difícil: "metformina dosagem infantil"
  Hard negatives melhoram discriminação do modelo.

Negative sampling
  Estratégia de selecionar negativos para treino.
  Random: qualquer documento não relevante.
  Hard: documentos similares mas não relevantes (BM25-mined).
  In-batch: outros exemplos do batch.

Asymmetric retrieval
  Query e documentos têm comprimentos muito diferentes.
  Query: curta (5–20 tokens).
  Documento: longo (100–500 tokens).
  Modelos assimétricos são treinados especificamente para esse cenário.
  OpenAI text-3 e BGE são assimétricos.

Symmetric retrieval
  Query e documentos têm comprimentos similares.
  Ex: buscar tweets similares, encontrar perguntas duplicadas.
  Modelos simétricos (all-MiniLM) são treinados para esse cenário.

Domain adaptation
  Adaptar modelo de embedding pré-treinado para domínio específico.
  Estratégias: fine-tuning com dados do domínio,
               prompt engineering, in-context learning.
  Pode melhorar NDCG@10 em 10–20% em domínios técnicos.

Cross-lingual retrieval
  Busca em um idioma com query em outro.
  Ex: query em PT-BR, documentos em EN.
  Requer modelo multilíngue com espaço vetorial compartilhado.
  BGE-M3 e Cohere Embed v3 suportam isso nativamente.

Semantic similarity
  Grau de similaridade semântica entre dois textos.
  Medida por cosine similarity entre seus embeddings.
  STS (Semantic Textual Similarity) é a tarefa de benchmark.

Zero-shot retrieval
  Retrieval em domínio não visto durante o treino.
  BEIR mede capacidade zero-shot de generalização.

Few-shot retrieval
  Passar exemplos de query-documento relevante no prompt
  para guiar o embedding ou o reranker.
```

---

## 20. Termos de grafos e GraphRAG

```
Knowledge graph (grafo de conhecimento)
  Estrutura de dados que representa entidades e suas relações.
  Nó = entidade (pessoa, lugar, conceito).
  Aresta = relação (trabalha_em, causa, trata).

Entity extraction (extração de entidades)
  Processo de identificar e categorizar entidades nomeadas.
  "A metformina trata diabetes tipo 2"
  → entidades: [metformina, diabetes tipo 2]
  → relação: trata

Relation extraction
  Identificar relações semânticas entre entidades.
  Entrada: "A Pfizer desenvolveu a vacina Comirnaty"
  Saída: (Pfizer) --[desenvolveu]--> (Comirnaty)

Community detection (detecção de comunidades)
  Algoritmos que agrupam nós fortemente conectados.
  Leiden algorithm: detecção eficiente de comunidades.
  Usado pelo GraphRAG para criar "resumos globais".

Leiden algorithm
  Algoritmo de detecção de comunidades em grafos.
  Evolução do Louvain algorithm.
  Usado pelo Microsoft GraphRAG para particionar o grafo.

PageRank
  Algoritmo de ranking de nós em grafos.
  Nós mais referenciados têm PageRank maior.
  Adaptado para RAG: identifica entidades mais importantes.

Local search (GraphRAG)
  Modo de query focado em uma entidade específica.
  Navega o grafo ao redor da entidade.
  Melhor para: "o que é X?" ou "qual o histórico de Y?"

Global search (GraphRAG)
  Modo de query que usa resumos de comunidades.
  Melhor para: "quais são as tendências em X?" ou
               "quais temas emergem neste corpus?"
```

---

## 21. Cache semântico e otimizações

```
Semantic cache (cache semântico)
  Em vez de comparar queries por hash exato,
  compara por similaridade semântica.
  Query similar a uma já cacheada → retorna resultado do cache.
  Threshold de similaridade: tipicamente 0.92–0.97.

Exact match cache
  Cache por hash SHA-256 da query.
  Só faz hit se a query for identica caractere a caractere.
  Mais simples e previsível que semantic cache.

Two-level cache (cache em dois níveis)
  L1: memória do processo (latência < 1ms, menor capacidade).
  L2: Redis (latência ~2ms, maior capacidade, persiste entre restarts).

Prompt caching (cache de prompt)
  APIs (Anthropic, OpenAI, Google) cacheiam prefixos repetidos.
  Anthropic: cache de 5min, desconto de 90% nos tokens cacheados.
  OpenAI: cache automático, desconto de 50%.
  Essencial para system prompts longos e fixos em RAG.

Batch API
  Processar múltiplas requisições em lote com desconto.
  OpenAI Batch: 50% off, até 24h para processar.
  Anthropic Batch: 50% off, até 24h.
  Ideal para: ingestão em lote, avaliação em lote.

Semantic deduplication
  Remover documentos semanticamente duplicados da base.
  Diferente de dedup por hash (conteúdo idêntico).
  Semanticamente duplicado: mesmo conteúdo, palavras diferentes.
  Threshold: cosine similarity > 0.97 → considerar duplicata.

DiskANN
  Algoritmo de ANN baseado em grafo otimizado para disco.
  Permite índices maiores que a RAM disponível.
  Usado pelo pgvectorscale para suportar 50M+ vetores eficientemente.

ANNOY (Approximate Nearest Neighbors Oh Yeah)
  Biblioteca da Spotify para ANN.
  Baseada em árvores aleatórias.
  Simples de usar, bom para bases médias, não atualiza incrementalmente.

ScaNN (Scalable Nearest Neighbors)
  Biblioteca do Google para ANN em larga escala.
  Quantização Anisotropic Vector Quantization (AVQ).
  Melhor trade-off recall × velocidade em benchmarks públicos.

FAISS (Facebook AI Similarity Search)
  Biblioteca da Meta para busca de similaridade.
  Múltiplos índices: Flat, IVF, PQ, HNSW.
  GPU support nativo.
  Usado internamente por Milvus e outros bancos vetoriais.

Agentic chunking
  LLM decide como dividir o documento em chunks.
  Analisa o conteúdo e identifica fronteiras semânticas naturais.
  Muito mais preciso que qualquer heurística.
  Custo: 1 LLM call por N tokens de documento.
```

---

## 22. Termos de avaliação avançados

```
DeepEval
  Framework open-source de avaliação de LLMs e RAG.
  Alternativa ao RAGAS com mais métricas disponíveis.
  Métricas: G-Eval, summarization, hallucination, bias, toxicity.

F1 Score (retrieval)
  Média harmônica entre Precision@K e Recall@K.
  F1 = 2 × (Precision × Recall) / (Precision + Recall)
  Balanceia os dois — útil quando ambos importam igualmente.

RAG Triad (TruLens)
  Framework de avaliação com 3 métricas:
  1. Answer Relevance: resposta é relevante para a query?
  2. Context Relevance: contexto é relevante para a query?
  3. Groundedness: resposta está ancorada no contexto?

G-Eval
  Método de avaliação com LLM como juiz usando CoT.
  Define critérios explícitos e pede ao LLM para avaliar passo a passo.
  Mais transparente que avaliação direta de score.

Self-Ask
  Técnica onde o LLM se faz perguntas intermediárias.
  "Para responder X, preciso saber Y. A resposta de Y é Z. Portanto X."
  Base para multi-hop retrieval estruturado.

Tree of Thought (ToT)
  LLM explora múltiplos caminhos de raciocínio em paralelo.
  Avalia cada caminho e seleciona o mais promissor.
  Muito mais caro que CoT mas melhor em problemas complexos.

In-context learning (ICL)
  Aprendizado a partir de exemplos no prompt, sem atualizar pesos.
  Zero-shot: sem exemplos.
  One-shot: um exemplo.
  Few-shot: poucos exemplos (3–10).
  RAG pode ser visto como uma forma de ICL com recuperação dinâmica.

Noise robustness score
  Métricas específicas do RAGAS para avaliar robustez:
  Noise Robustness: qualidade cai X% com Y% de chunks irrelevantes?
  Negative Rejection: sistema recusa responder quando não tem contexto?
  Information Integration: sintetiza múltiplos chunks corretamente?
  Counterfactual Robustness: ignora contexto que contradiz fatos?
```

---

## 23. Atualização das siglas

```
AVQ   Anisotropic Vector Quantization (ScaNN)
CRAG  Corrective RAG
CLM   Causal Language Modeling
DiskANN Disk-based Approximate Nearest Neighbor
DPO   Direct Preference Optimization
FAISS Facebook AI Similarity Search
GGUF  GPT-Generated Unified Format (llama.cpp)
ICL   In-Context Learning
LoRA  Low-Rank Adaptation
MLM   Masked Language Modeling
PPO   Proximal Policy Optimization (em RLHF)
RLHF  Reinforcement Learning from Human Feedback
ScaNN Scalable Nearest Neighbors (Google)
STS   Semantic Textual Similarity
ToT   Tree of Thought
```
