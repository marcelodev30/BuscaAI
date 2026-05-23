# Estratégias de RAG — Pré-Retrieval, Retrieval e Pós-Retrieval

Guia completo de todas as estratégias disponíveis em cada etapa do pipeline RAG.
Para cada estratégia: o que é, como funciona, latência, custo, ganho de qualidade,
pontos positivos e negativos, e casos de uso indicados.

---

## Sumário

- [Pré-Retrieval](#pré-retrieval)
  - [Query Rewriting](#1-query-rewriting)
  - [Query Expansion](#2-query-expansion)
  - [HyDE](#3-hyde--hypothetical-document-embedding)
  - [Step-Back Prompting](#4-step-back-prompting)
  - [Query Decomposition](#5-query-decomposition)
  - [Query Routing](#6-query-routing)
- [Retrieval](#retrieval)
  - [BM25 / Busca Lexical](#1-bm25--busca-lexical)
  - [Busca Densa](#2-busca-densa)
  - [Busca Híbrida + RRF](#3-busca-híbrida--rrf-recomendado)
  - [SPLADE / Busca Esparsa Neural](#4-splade--busca-esparsa-neural)
  - [MMR](#5-mmr--maximal-marginal-relevance)
  - [Multi-Index Retrieval](#6-multi-index-retrieval)
- [Pós-Retrieval](#pós-retrieval)
  - [Reranking — Cross-Encoder](#1-reranking--cross-encoder)
  - [Reranking — LLM](#2-reranking--llm)
  - [Context Compression](#3-context-compression)
  - [Prompt Packing](#4-prompt-packing)
  - [Knowledge Strips](#5-knowledge-strips-crag)
  - [Filtro por Score Mínimo](#6-filtro-por-score-mínimo)
  - [Citation Grounding](#7-citation-grounding)
- [Tabela comparativa geral](#tabela-comparativa-geral)
- [Combinações recomendadas](#combinações-recomendadas)

---

## Pré-Retrieval

Transformações aplicadas à query **antes** de ir ao banco vetorial.
O objetivo é aumentar a probabilidade de encontrar os chunks certos.

---

### 1. Query Rewriting

**O que é:**
Um LLM reescreve a query original tornando-a mais clara, expandida ou objetiva.
Corrige ambiguidade, jargões, queries incompletas e linguagem coloquial.

**Como funciona:**
```
query original:  "e o prazo?"
      ↓
LLM com histórico da conversa
      ↓
query reescrita: "qual o prazo de rescisão do contrato de prestação de serviços?"
      ↓
retrieval com query melhorada
```

Prompt típico:
```
Dado o histórico de conversa abaixo, reescreva a última pergunta do usuário
de forma autônoma e completa, sem depender do contexto anterior.

Histórico: {historico}
Pergunta: {query}

Reescrita:
```

| Métrica | Valor |
|---|---|
| Latência adicionada | +300–800ms |
| Custo por query | ~$0.001 (modelo barato como Groq) |
| Ganho de qualidade | +15–25% no Recall@5 |

**Pontos positivos:**
- Resolve queries curtas, ambíguas e dependentes de contexto
- Melhora recall significativamente em conversas com histórico
- Essencial para o modo chat (reformulação de queries de acompanhamento)

**Pontos negativos:**
- Custo extra de LLM por query
- Pode distorcer a intenção original se o prompt não for bem calibrado
- Adiciona latência perceptível

**Casos de uso indicados:**
- Chatbots com usuários leigos
- Conversas com histórico (modo chat)
- Domínio técnico com terminologia específica
- Perguntas de acompanhamento ("e quanto a X?", "e no caso Y?")

---

### 2. Query Expansion

**O que é:**
Gera N variações semânticas da query original (sinônimos, paráfrases, perguntas
alternativas) e executa retrieval para cada uma, fundindo os resultados com RRF.
É a base do paradigma RAG Fusion.

**Como funciona:**
```
query: "prazo de rescisão contratual"
      ↓
LLM gera variações:
  → "tempo para cancelar contrato"
  → "período de aviso prévio"
  → "rescisão sem justa causa prazo"
      ↓
retrieval independente para cada variação
      ↓
RRF funde os 4 rankings
      ↓
resultado mais robusto
```

Prompt típico:
```
Gere {n} variações semânticas da query abaixo para uso em busca de documentos.
Cada variação deve capturar o mesmo significado com vocabulário diferente.
Retorne apenas as variações, uma por linha.

Query: {query}
```

| Métrica | Valor |
|---|---|
| Latência adicionada | +500ms–1.5s |
| Custo por query | 3–5× o custo de um retrieval simples |
| Ganho de qualidade | +10–20% no Recall@5 |

**Pontos positivos:**
- Ótimo para domínios com vocabulário variado (jurídico, médico)
- Aumenta recall consideravelmente
- Cobre diferentes formas de expressar a mesma necessidade

**Pontos negativos:**
- Multiplica o custo de retrieval (N buscas em vez de 1)
- Piora em queries técnicas com termos exatos (IDs, códigos, SKUs)
- Latência mais alta, impacta UX em tempo real

**Casos de uso indicados:**
- Domínio jurídico (terminologia muito variada)
- Bases com documentos de múltiplas fontes e estilos
- Usuários leigos com vocabulário diferente dos documentos
- Perguntas exploratórias e abertas

---

### 3. HyDE — Hypothetical Document Embedding

**O que é:**
O LLM gera uma resposta hipotética para a query. O embedding desta resposta
hipotética (muito mais rico semanticamente que o embedding da query curta)
é usado para buscar documentos reais.

**Como funciona:**
```
query curta: "efeitos metformina"
      ↓
LLM gera resposta hipotética:
  "A metformina pode causar náusea, diarreia e dor abdominal,
   especialmente no início do tratamento. Raramente, pode causar
   acidose lática. O mecanismo envolve inibição da gliconeogênese..."
      ↓
embedding da resposta hipotética (muito mais denso e rico)
      ↓
busca vetorial com embedding de alta qualidade
      ↓
chunks muito mais relevantes que com o embedding da query curta
```

| Métrica | Valor |
|---|---|
| Latência adicionada | +500ms–1s |
| Custo por query | +1 chamada de LLM (~$0.002–0.01) |
| Ganho de qualidade | +15–30% em bases com texto denso |

**Pontos positivos:**
- Excelente para queries curtas e vagas
- Faz a ponte entre vocabulário do usuário e vocabulário dos documentos
- Funciona bem em domínios especializados com linguagem técnica

**Pontos negativos:**
- Piora em queries que precisam de termos exatos (IDs, nomes próprios, códigos)
- Uma hipótese errada polui o retrieval com ruído
- Custo adicional de LLM por query

**Casos de uso indicados:**
- Perguntas abertas e exploratórias
- Bases com texto denso e técnico (artigos, manuais, papers)
- Saúde e pesquisa científica
- Usuários que não sabem o vocabulário exato do domínio

---

### 4. Step-Back Prompting

**O que é:**
Transforma uma query muito específica em uma pergunta mais geral ("step back"),
recupera contexto conceitual de fundo, e usa esse contexto para enriquecer
a resposta à pergunta específica original.

**Como funciona:**
```
query específica:
  "qual a dose de metformina para idosos com insuficiência renal leve?"
      ↓
LLM gera pergunta step-back:
  "quais são os princípios gerais de dosagem de metformina?"
      ↓
retrieval para AMBAS as queries em paralelo:
  → chunks da query original (detalhes específicos)
  → chunks da step-back (contexto geral)
      ↓
LLM responde com ambos os contextos disponíveis
```

| Métrica | Valor |
|---|---|
| Latência adicionada | +400–800ms |
| Custo por query | +2× retrieval + 1 LLM call |
| Ganho de qualidade | +10–20% em queries muito específicas |

**Pontos positivos:**
- Ótimo para perguntas com muitos detalhes específicos
- Recupera contexto de fundo que o usuário pressupõe mas não pergunta
- Melhora a qualidade de respostas sobre casos edge

**Pontos negativos:**
- Overhead de retrieval duplicado
- A abstração gerada pode não ser a correta
- Benefício limitado para queries já bem formuladas

**Casos de uso indicados:**
- Saúde (perguntas clínicas com muitas variáveis)
- Jurídico (casos específicos que dependem de princípios gerais)
- Bases com hierarquia de conceitos (geral → específico)
- Perguntas com múltiplas condições e exceções

---

### 5. Query Decomposition

**O que é:**
Queries com múltiplas perguntas embutidas são divididas em sub-queries
independentes. Cada sub-query é respondida separadamente, e as respostas
parciais são combinadas pelo LLM em uma resposta final coerente.

**Como funciona:**
```
query complexa:
  "compare o desempenho do produto A em Q1 e Q2 e explique as causas da diferença"
      ↓
LLM decompõe em sub-queries:
  1. "qual foi o desempenho do produto A no Q1?"
  2. "qual foi o desempenho do produto A no Q2?"
  3. "quais fatores influenciaram o desempenho do produto A?"
      ↓
retrieval independente para cada sub-query
      ↓
LLM sintetiza as 3 respostas parciais em resposta final
```

Estratégias de decomposição:
- **Sequencial:** sub-query 2 usa o resultado da sub-query 1
- **Paralela:** todas as sub-queries executam simultaneamente
- **Iterativa (Self-Ask):** LLM decide a próxima sub-query baseado na resposta anterior

| Métrica | Valor |
|---|---|
| Latência adicionada | +1–3s |
| Custo por query | N × retrieval + LLMs de síntese |
| Ganho de qualidade | +30–50% em queries multi-hop |

**Pontos positivos:**
- Melhor resultado isolado em queries analíticas e comparativas
- Respostas muito mais completas e estruturadas
- Permite paralelização das sub-queries para reduzir latência

**Pontos negativos:**
- Custo muito alto para queries simples — não usar como padrão
- Requer orquestração complexa (LangGraph ideal)
- Latência alta mesmo com paralelização

**Casos de uso indicados:**
- Análise financeira (comparações, tendências, causas)
- Relatórios executivos com múltiplas dimensões
- Queries multi-hop (resposta A depende da resposta B)
- Perguntas que envolvem comparação entre entidades

---

### 6. Query Routing

**O que é:**
Classifica a query e a direciona para o pipeline mais adequado: RAG completo,
resposta direta do LLM (sem retrieval), busca na web, consulta SQL, ou
pipeline especializado por domínio.

**Como funciona:**
```
query
  ↓
[classificador — heurística ou LLM]
  ↓
  ├── query factual sobre documentos   → RAG padrão
  ├── query simples de conhecimento    → LLM direto (sem retrieval)
  ├── query sobre dados estruturados   → SQL + resposta
  ├── query sobre eventos recentes     → busca web
  └── query de domínio específico      → pipeline especializado
```

Três implementações possíveis:
```
1. Heurística pura (~$0, <5ms):
   if len(query) < 20 and not any(keyword in query for keyword in KEYWORDS_RAG):
       return "llm_direto"

2. Classificador LLM barato (~$0.001, ~200ms):
   "Classifique: factual/simples/estruturado/recente. Query: {query}"

3. Embedding + classificador treinado (~$0, ~20ms):
   modelo scikit-learn treinado com exemplos de cada categoria
```

| Métrica | Valor |
|---|---|
| Latência adicionada | <5ms (heurística) a 300ms (LLM) |
| Custo por query | $0 a $0.001 |
| Ganho (redução de custo) | 60–80% do custo total |

**Pontos positivos:**
- Reduz custo total drasticamente ao evitar RAG para queries simples
- Melhora latência para queries que o LLM responde diretamente
- Permite especialização do pipeline por domínio

**Pontos negativos:**
- Erros de classificação direcionam para o pipeline errado
- Regras de roteamento precisam de manutenção contínua
- Cobertura de edge cases é difícil

**Casos de uso indicados:**
- Bases com queries de natureza muito variada
- Múltiplas fontes de dados (SQL + vetorial + web)
- Otimização de custo em produção
- Chatbots multi-domínio

---

## Retrieval

Estratégias de busca e recuperação dos chunks mais relevantes da base.

---

### 1. BM25 / Busca Lexical

**O que é:**
Busca por presença e frequência de termos no texto. Usa BM25 (Best Match 25),
evolução do TF-IDF com saturação de frequência de termos e normalização
pelo tamanho do documento.

**Como funciona:**
```
Índice invertido:
  "metformina" → [doc_3: pos 45, doc_12: pos 8, doc_47: pos 122]
  "diabetes"   → [doc_3: pos 50, doc_5: pos 3, doc_12: pos 15]

Score BM25 para o documento d, query q:
  score(d, q) = Σ IDF(t) × [ TF(t,d) × (k1+1) / (TF(t,d) + k1 × (1 - b + b × |d|/avgdl)) ]

  onde:
    TF(t,d)  = frequência do termo t no documento d
    IDF(t)   = log((N - df(t) + 0.5) / (df(t) + 0.5))
    k1       = parâmetro de saturação (tipicamente 1.2–2.0)
    b        = normalização de tamanho (tipicamente 0.75)
    |d|      = tamanho do documento
    avgdl    = tamanho médio dos documentos
```

| Métrica | Valor |
|---|---|
| Latência | 5–30ms |
| Custo | $0 (índice próprio) |
| Qualidade | baseline — pior que híbrida, melhor que nada |

**Pontos positivos:**
- Rápido, determinístico, sem custo de API
- Excelente para termos exatos: IDs, SKUs, nomes próprios, códigos
- Funciona bem para domínios com terminologia muito específica
- Sem dependência de modelos externos

**Pontos negativos:**
- Não entende significado semântico
- Falha completamente em sinônimos e paráfrases
- Sensível a typos (sem tolerância a erros)
- Não captura queries conceituais ("riscos de investimento" ≠ "perigos financeiros")

**Casos de uso indicados:**
- Pré-filtragem léxica antes da busca vetorial
- Bases com logs, código-fonte, IDs e referências técnicas
- Complemento da busca densa na estratégia híbrida
- Cenários offline sem acesso a modelos de embedding

---

### 2. Busca Densa

**O que é:**
Transforma query e documentos em vetores densos (embeddings) e busca
os k vetores mais próximos por similaridade de cosseno, usando
o algoritmo HNSW para busca aproximada eficiente.

**Como funciona:**
```
Ingestão:
  chunk de texto → modelo de embedding → vetor de 1536 dimensões
  vetor armazenado no banco vetorial (Qdrant, Pinecone, etc.)
  índice HNSW construído sobre os vetores

Query:
  query → modelo de embedding → vetor de 1536 dimensões
       ↓
  HNSW navega grafo de vizinhos (não busca exaustiva)
       ↓
  top-k vetores mais similares por cosseno
       ↓
  chunks correspondentes retornados
```

HNSW (Hierarchical Navigable Small World):
- Grafo em camadas: camadas superiores têm poucos nós (atalhos), inferiores têm todos
- Busca começa no topo (macro) e desce até o detalhe
- Trade-off: `hnsw_m` (qualidade × RAM), `hnsw_ef` (precisão × latência)

| Métrica | Valor |
|---|---|
| Latência | 20–80ms |
| Custo | $0.02–0.13 por 1M tokens (embedding) |
| Qualidade | +20–30% sobre BM25 em queries semânticas |

**Pontos positivos:**
- Entende semântica: sinônimos, paráfrases, contexto
- Funciona em múltiplos idiomas com modelos multilíngues
- Generaliza bem para queries não vistas antes

**Pontos negativos:**
- Perde termos exatos quando o embedding suaviza a diferença
- Custo de embedding por query (API ou hardware para modelo local)
- Qualidade depende fortemente do modelo de embedding escolhido
- RAM significativa para o índice HNSW (~9GB para 1M vetores 1536d)

**Casos de uso indicados:**
- FAQ e suporte ao cliente
- Perguntas em linguagem natural
- Bases multilíngues
- Domínios onde sinônimos são comuns

---

### 3. Busca Híbrida + RRF ⭐ recomendado

**O que é:**
Executa BM25 e busca densa em paralelo e funde os dois rankings com
Reciprocal Rank Fusion (RRF). Captura termos exatos e significado semântico
simultaneamente. Padrão recomendado pela literatura e pelo BuscaAI.

**Como funciona:**
```
query
  ├──→ BM25 → [doc_3: 0.89, doc_7: 0.72, doc_15: 0.61, ...]   rank_lexical
  └──→ Densa → [doc_7: 0.94, doc_3: 0.88, doc_22: 0.71, ...]  rank_semântico
                                    ↓
             RRF score = Σ 1 / (k + rank_i)   onde k = 60 (padrão)

             doc_3:  1/(60+1) + 1/(60+2) = 0.0164 + 0.0161 = 0.0325
             doc_7:  1/(60+2) + 1/(60+1) = 0.0161 + 0.0164 = 0.0325
             doc_22: 0      + 1/(60+3)   = 0      + 0.0159 = 0.0159
                                    ↓
             top-k do ranking fundido → reranker (se ativo) → LLM
```

Por que RRF é superior a média de scores?
- Não precisa normalizar scores de sistemas diferentes
- Robusto a outliers (um sistema com score altíssimo não domina)
- Simples e sem hiperparâmetros críticos

| Métrica | Valor |
|---|---|
| Latência | 30–120ms |
| Custo | BM25 ($0) + embedding ($0.02–0.13/1M) |
| Qualidade | +25–40% sobre BM25 ou densa isolados |

**Pontos positivos:**
- Melhor resultado comprovado em benchmarks de retrieval (Sharma 2025)
- Cobre os gaps de cada método — termos exatos E semântica
- RRF é robusto sem parâmetros difíceis de tunar
- Padrão de mercado para produção

**Pontos negativos:**
- Custo e latência são a soma dos dois métodos
- Mais complexo de implementar e de debugar quando algo falha
- Requer manutenção de dois índices (invertido + vetorial)

**Casos de uso indicados:**
- Produção geral (padrão recomendado)
- Bases corporativas com documentos variados
- Domínios onde termos exatos e semântica são ambos importantes
- Jurídico, saúde, suporte técnico, e-commerce

---

### 4. SPLADE / Busca Esparsa Neural

**O que é:**
Modelo neural que gera representações esparsas com expansão semântica.
Combina a eficiência do índice invertido com o entendimento contextual
de transformers. Evolução do BM25 que "entende" os termos.

**Como funciona:**
```
texto: "metformina para diabetes tipo 2"
      ↓
BERT encoder → MLM head → vetor no espaço do vocabulário (30.522 dim)
      ↓
vetor esparso (maioria = 0, poucos valores > 0):
  metformina: 2.1
  diabetes:   1.8
  glicemia:   1.2   ← expansão semântica
  insulina:   0.9   ← expansão semântica
  tipo:       0.7
  tratamento: 0.6   ← expansão semântica
  [outros 30.516 termos]: 0.0
      ↓
índice invertido normal (mesma estrutura do BM25)
      ↓
busca eficiente + cobertura semântica
```

| Métrica | Valor |
|---|---|
| Latência | 20–60ms (com GPU) |
| Custo | ~$0 (modelo local via FastEmbed, ~500MB) |
| Qualidade | +15–25% sobre BM25 puro |

**Pontos positivos:**
- Melhor que BM25 puro com custo de inferência similar
- Interpretável — você vê quais termos o modelo expande
- Sem custo de API (modelo local)
- Excelente como componente esparso da busca híbrida

**Pontos negativos:**
- Requer modelo local (~500MB de RAM)
- Inferência mais lenta que BM25 puro (precisa de GPU para produção)
- Menos maduro que embeddings densos em língua portuguesa

**Casos de uso indicados:**
- Substituto do BM25 na busca híbrida quando há GPU disponível
- Bases com terminologia rica onde expansão semântica ajuda
- Domínios médicos e científicos com sinônimos técnicos

---

### 5. MMR — Maximal Marginal Relevance

**O que é:**
Penaliza chunks muito similares entre si no resultado. Em vez de retornar
5 chunks quase idênticos sobre o mesmo parágrafo, força diversidade temática
no conjunto de chunks enviados ao LLM.

**Como funciona:**
```
candidatos após retrieval: [chunk_1, chunk_2, chunk_3, chunk_4, chunk_5]

MMR score = λ × sim(query, doc) − (1−λ) × max_sim(doc, já_selecionados)
  λ = 0.5 (equilíbrio relevância × diversidade)
  λ = 0.7 (prioriza relevância)
  λ = 0.3 (prioriza diversidade)

Iteração 1: seleciona chunk mais similar à query → chunk_3 (score 0.91)
Iteração 2: chunk_1 (score 0.88, mas similar ao chunk_3) → penalizado
            chunk_5 (score 0.82, mas diferente) → selecionado
Iteração 3: continua até top_k selecionados
```

| Métrica | Valor |
|---|---|
| Latência adicionada | +5–20ms |
| Custo | ~$0 (cálculo de similaridade entre vetores) |
| Ganho | +5–15% em Faithfulness quando há redundância |

**Pontos positivos:**
- Evita redundância no contexto enviado ao LLM
- Melhora cobertura de subtemas relacionados à query
- Especialmente útil em bases com documentos redundantes

**Pontos negativos:**
- Pode sacrificar o chunk mais relevante em favor de diversidade
- λ precisa de ajuste manual para cada caso de uso
- Benefício limitado em bases com pouca redundância

**Casos de uso indicados:**
- Documentos com muito conteúdo repetido (versões de contratos, FAQs extensos)
- Bases onde a mesma informação aparece em múltiplos documentos
- Sumarização de múltiplos documentos

---

### 6. Multi-Index Retrieval

**O que é:**
Mantém índices separados por domínio, fonte, tipo de dado ou tenant.
A query é roteada para o(s) índice(s) mais relevantes, e os resultados
são fundidos via RRF.

**Como funciona:**
```
Base jurídica:
  índice_contratos    → chunks de contratos da empresa
  índice_legislacao   → leis e regulamentos
  índice_jurisprud    → jurisprudências e decisões

Query: "rescisão contratual — precedentes do STJ"
  ↓
router: relevante para índice_contratos + índice_jurisprud
  ↓
retrieval paralelo em dois índices
  ↓
RRF funde os rankings dos dois índices
  ↓
top-k combinado
```

| Métrica | Valor |
|---|---|
| Latência | N × latência de busca simples (paralelo = similar à busca única) |
| Custo | N × custo de embedding |
| Ganho | +20–35% em cobertura e precisão |

**Pontos positivos:**
- Permite especialização por domínio (embeddings, prompts, chunking diferentes)
- Isolamento de dados sensíveis (multi-tenant nativo)
- Resultados mais precisos por índice mais focado

**Pontos negativos:**
- Custo de manutenção de múltiplos índices
- Fusão entre domínios muito diferentes é desafiadora
- Infraestrutura mais complexa

**Casos de uso indicados:**
- Multi-tenant (cada cliente tem seu próprio índice)
- Bases com fontes heterogêneas (contratos + leis + emails)
- Domínios que requerem configurações diferentes de chunking/embedding

---

## Pós-Retrieval

Processamento dos chunks recuperados **antes** de enviar ao LLM.
O objetivo é maximizar a qualidade e fidelidade da resposta final.

---

### 1. Reranking — Cross-Encoder

**O que é:**
Modelo que recebe (query + chunk) **juntos** e calcula a relevância com
atenção cruzada entre os dois textos — muito mais preciso que comparar
embeddings separados. Reordena os top-k candidatos do retrieval.

**Como funciona:**
```
Busca retorna 50 candidatos
      ↓
Para cada candidato:
  cross_encoder([query; chunk]) → score de relevância (0–1)

  input:  "[CLS] qual é o prazo de rescisão? [SEP] O contrato
           pode ser rescindido com aviso prévio de 30 dias... [SEP]"
  output: 0.94 (muito relevante)
      ↓
Re-ordena os 50 por score
      ↓
Retorna os top 5 para o LLM

Modelos disponíveis:
  cross-encoder/ms-marco-MiniLM-L-6-v2   → 22MB, ~100ms/30 docs em CPU
  cross-encoder/ms-marco-MiniLM-L-12-v2  → 33MB, ~200ms/30 docs em CPU
  BAAI/bge-reranker-large                → 1.5GB, precisa GPU
  Qwen3-Reranker-8B                      → 8GB, GPU obrigatória
```

| Métrica | Valor |
|---|---|
| Latência | 80–300ms (CPU, 30 candidatos) |
| Custo | $0 (local) a $2/1k buscas (Cohere) |
| Ganho de qualidade | +20–35% — maior ganho isolado do pipeline |

**Pontos positivos:**
- Maior ganho isolado de qualidade de todo o pipeline pós-retrieval
- Modelo local disponível e gratuito (ms-marco-MiniLM)
- Corrige erros do retrieval inicial — recupera chunks sub-ranqueados
- Muito eficaz em distinguir chunks com conteúdo parecido

**Pontos negativos:**
- Latência proporcional ao número de candidatos (N × inferência)
- Não escala para centenas de candidatos sem GPU
- GPU necessária para modelos maiores e mais precisos

**Casos de uso indicados:**
- Saúde e jurídico (missão crítica, qualidade > latência)
- Bases com muitos chunks similares sobre o mesmo tema
- Sempre que top-k > 10 candidatos chegam ao pós-retrieval

---

### 2. Reranking — LLM

**O que é:**
Um LLM (geralmente menor e mais barato) recebe a query e os chunks
e produz um ranking de relevância. Mais flexível que o cross-encoder
para domínios muito específicos.

**Como funciona:**
```
Prompt para reranking:
  "Você recebeu a query: '{query}'
   Abaixo estão {n} chunks de documentos. Ordene-os de 1 (mais relevante)
   a {n} (menos relevante) para responder a query.
   Retorne apenas os números, ex: 3, 1, 5, 2, 4

   Chunk 1: {chunk_1}
   Chunk 2: {chunk_2}
   ...
   Chunk {n}: {chunk_n}"

Resposta: "2, 5, 1, 3, 4"
      ↓
BuscaAI reordena os chunks conforme o ranking
      ↓
top final_k vão ao LLM de geração
```

| Métrica | Valor |
|---|---|
| Latência | 500ms–2s |
| Custo | $0.05–0.50 por query (depende do LLM e número de chunks) |
| Ganho de qualidade | +25–40% |

**Pontos positivos:**
- Máxima precisão — LLM entende nuances que cross-encoder perde
- Adaptável com prompt específico para o domínio
- Sem necessidade de modelo especializado treinado

**Pontos negativos:**
- Custo alto em volume elevado
- Latência alta — impacta UX negativamente
- LLM pode "inventar" relevâncias com poucos exemplos

**Casos de uso indicados:**
- Volume baixo onde qualidade é crítica
- Domínios muito especializados sem modelo de reranking disponível
- Prototipagem antes de treinar um cross-encoder específico

---

### 3. Context Compression

**O que é:**
Cada chunk é filtrado para manter apenas as sentenças diretamente relevantes
para a query. Reduz o contexto enviado ao LLM, diminuindo custo de tokens,
ruído e o problema de "lost in the middle".

**Como funciona:**
```
chunk original (500 tokens):
  "A metformina foi aprovada pela FDA em 1958. É amplamente usada
   para diabetes tipo 2. Estudos mostram redução de HbA1c de 1.5%.
   O mecanismo principal é a inibição da gliconeogênese hepática.
   Efeitos colaterais incluem náusea, diarreia e dor abdominal.
   Raramente, pode causar acidose lática. A absorção é lenta e
   o pico plasmático ocorre em 2-3 horas após a ingestão..."

query: "quais são os efeitos colaterais da metformina?"
      ↓
LLM extrai frases relevantes:
  "Efeitos colaterais incluem náusea, diarreia e dor abdominal.
   Raramente, pode causar acidose lática."
      ↓
chunk comprimido (35 tokens em vez de 500)
```

Implementações possíveis:
- LLM pequeno (Groq, Cohere R7B) — maior qualidade
- Cross-encoder por sentença — sem custo de API
- Filtro por score de similaridade sentença × query — mais simples

| Métrica | Valor |
|---|---|
| Latência adicionada | +200–600ms |
| Custo | +LLM de compressão, mas economiza tokens do LLM final |
| Ganho de qualidade | +10–20% em Faithfulness |

**Pontos positivos:**
- Reduz custo de tokens do LLM final em 60–80%
- Diminui "lost in the middle" (LLM perde info no meio do contexto longo)
- Permite encaixar mais chunks no limite de contexto

**Pontos negativos:**
- Risco de remover contexto necessário para a resposta
- Adiciona latência e custo da compressão
- Custo-benefício nem sempre positivo para chunks já curtos

**Casos de uso indicados:**
- Chunks longos (>300 tokens) com muito conteúdo fora do escopo
- LLM com janela de contexto limitada
- Casos onde custo de tokens do LLM final é significativo

---

### 4. Prompt Packing

**O que é:**
Organiza e ordena os chunks no prompt do LLM para maximizar a qualidade
da resposta dentro do limite de tokens. A posição no contexto importa —
LLMs lembram melhor o início e o fim ("lost in the middle").

**Como funciona:**
```
chunks ordenados por score após reranker:
  chunk_A (score 0.94)
  chunk_B (score 0.88)
  chunk_C (score 0.76)
  chunk_D (score 0.71)
  chunk_E (score 0.65)

Sem packing (ordem linear):
  [chunk_A] [chunk_B] [chunk_C] [chunk_D] [chunk_E]
  ↑ LLM lembra bem    ↑ LLM perde aqui    ↑ LLM lembra bem

Com packing (lost-in-the-middle mitigation):
  [chunk_A] [chunk_C] [chunk_E] [chunk_D] [chunk_B]
  ↑ mais relevante no início e fim, menos relevante no meio
```

Template de prompt:
```
Contexto:
---
{chunk_mais_relevante}
---
{outros_chunks}
---
{segundo_mais_relevante}
---

Pergunta: {query}
Resposta baseada apenas no contexto acima:
```

| Métrica | Valor |
|---|---|
| Latência adicionada | <5ms |
| Custo | $0 |
| Ganho de qualidade | +5–15% |

**Pontos positivos:**
- Zero custo e latência mínima
- Mitiga o problema de "lost in the middle" comprovado na literatura
- Fácil de implementar junto com qualquer outra estratégia

**Pontos negativos:**
- Ganho incremental pequeno quando aplicado isoladamente
- Depende do comportamento específico do LLM (varia entre modelos)
- Difícil de avaliar isoladamente de outras melhorias

**Casos de uso indicados:**
- Sempre aplicável — custo zero, nunca piora
- Especialmente útil com muitos chunks por query (>5)
- LLMs com contexto menor que o necessário

---

### 5. Knowledge Strips (CRAG)

**O que é:**
Decompõe chunks em afirmações atômicas (facts). Cada afirmação é avaliada
individualmente para relevância. Reconstrói o contexto apenas com as
afirmações relevantes. Componente central do CRAG.

**Como funciona:**
```
chunk: "A metformina foi aprovada em 1958. É usada para diabetes tipo 2.
        Causa náusea. Inibe a gliconeogênese. Foi desenvolvida por Jean Sterne."

query: "quais os efeitos colaterais da metformina?"
      ↓
LLM decompõe em afirmações atômicas (strips):
  strip_1: "aprovada em 1958"            → irrelevante (score 0.1) ✗
  strip_2: "usada para diabetes tipo 2"  → parcialmente (score 0.4) ✗
  strip_3: "causa náusea"                → relevante (score 0.95)   ✓
  strip_4: "inibe a gliconeogênese"      → irrelevante (score 0.2)  ✗
  strip_5: "desenvolvida por Jean Sterne"→ irrelevante (score 0.05) ✗
      ↓
contexto reconstruído: "A metformina causa náusea."
      ↓
LLM gera resposta com contexto ultra-limpo
```

| Métrica | Valor |
|---|---|
| Latência adicionada | +500ms–2s por chunk |
| Custo | Alto — 1 LLM call por chunk |
| Ganho de qualidade | +20–35% em Precision e Faithfulness |

**Pontos positivos:**
- Máxima precisão no contexto final — elimina todo ruído
- Reduz alucinações causadas por contexto irrelevante
- Rastreabilidade total (cada afirmação tem origem documentada)

**Pontos negativos:**
- Custo e latência muito altos — inviável em volume alto
- Risco de perder contexto implícito necessário
- Parte do framework CRAG, não fácil de usar standalone

**Casos de uso indicados:**
- Saúde (contexto incorreto pode causar danos reais)
- Jurídico (precisão de afirmações é crítica)
- Chunks muito longos e densos com muito conteúdo off-topic
- Quando alucinação é inaceitável

---

### 6. Filtro por Score Mínimo

**O que é:**
Define um score mínimo de relevância. Chunks abaixo do threshold são
descartados, mesmo que sejam os top-k retornados. Se nenhum chunk
passar, o sistema responde que não tem informação suficiente.

**Como funciona:**
```
top-k após retrieval/reranker:
  chunk_1: score 0.87 ✓ (passa)
  chunk_2: score 0.72 ✓ (passa)
  chunk_3: score 0.48 ✗ (abaixo do threshold = 0.50)
  chunk_4: score 0.31 ✗
  chunk_5: score 0.22 ✗

→ apenas chunk_1 e chunk_2 vão ao LLM

Se nenhum chunk passar:
  → resposta: "Não encontrei informações suficientes na base de
               conhecimento para responder esta pergunta."
  → sem alucinação
```

Calibração do threshold:
```python
# threshold muito alto: rejeita chunks úteis, mais "não sei" do que necessário
# threshold muito baixo: permite chunks irrelevantes, mais alucinação

# Valores práticos por tipo de retrieval:
THRESHOLD_COSINE_SIMILARITY = 0.60   # busca densa (escala 0–1)
THRESHOLD_BM25_SCORE        = 5.0    # BM25 (escala variável por base)
THRESHOLD_RERANKER          = 0.50   # cross-encoder (escala 0–1)
```

| Métrica | Valor |
|---|---|
| Latência adicionada | <1ms |
| Custo | $0 |
| Ganho | Redução significativa de alucinações |

**Pontos positivos:**
- Reduz alucinações drasticamente
- Zero custo e latência irrelevante
- Fácil de implementar e de ajustar

**Pontos negativos:**
- Threshold precisa de calibração por base e por tipo de retrieval
- Threshold errado (muito alto) rejeita chunks genuinamente úteis
- Métricas de score variam entre estratégias de retrieval

**Casos de uso indicados:**
- Sempre recomendado — nenhum sistema deveria ir sem isso
- Especialmente crítico quando há queries out-of-scope frequentes
- Chatbots com usuários que testam os limites do sistema

---

### 7. Citation Grounding

**O que é:**
O LLM é instruído a vincular cada afirmação da resposta à fonte original
(documento, página, chunk). A resposta final inclui referências verificáveis,
aumentando confiança e auditabilidade.

**Como funciona:**
```
Prompt para o LLM:
  "Responda a pergunta abaixo baseado APENAS nos documentos fornecidos.
   Para cada afirmação, indique a fonte entre colchetes [doc_id, pág. X].
   Se não encontrar no contexto, diga explicitamente que não sabe.

   Documentos:
   [1] contrato_xyz.pdf, pág. 3: 'O prazo de rescisão é de 30 dias...'
   [2] lei_8666.pdf, art. 79: 'A rescisão do contrato poderá ser...'

   Pergunta: qual é o prazo de rescisão?

   Resposta:"
      ↓
LLM responde:
  "O prazo de rescisão é de 30 dias [1]. A lei também prevê
   rescisão imediata em casos de descumprimento grave [2]."

Pós-processamento verifica se [1] e [2] existem nos chunks fornecidos.
```

| Métrica | Valor |
|---|---|
| Latência adicionada | +50–200ms (tokens extras de output) |
| Custo | +tokens de output com as citações |
| Ganho | +confiança e auditabilidade |

**Pontos positivos:**
- Auditabilidade total — cada afirmação pode ser verificada
- Reduz alucinações (LLM fica "preso" às fontes)
- Indispensável em domínios regulados

**Pontos negativos:**
- LLM pode inventar citações que não existem nos chunks
- Aumenta custo de tokens de output
- Requer pós-processamento para validar as citações

**Casos de uso indicados:**
- Jurídico (toda afirmação precisa de base legal)
- Saúde (diagnósticos e condutas precisam de fonte)
- Compliance e auditoria
- Pesquisa científica
- Qualquer caso onde o usuário precisa verificar a fonte

---

## Tabela comparativa geral

### Pré-Retrieval

| Estratégia | Latência | Custo/query | Ganho qualidade | Complexidade |
|---|---|---|---|---|
| Query Rewriting | +300–800ms | ~$0.001 | +15–25% | Baixa |
| Query Expansion | +500ms–1.5s | +3–5× retrieval | +10–20% | Média |
| HyDE | +500ms–1s | ~$0.005 | +15–30% | Baixa |
| Step-Back | +400–800ms | +2× retrieval | +10–20% | Baixa |
| Query Decomposition | +1–3s | N× retrieval | +30–50% | Alta |
| Query Routing | <5ms–300ms | $0–$0.001 | −60% custo | Média |

### Retrieval

| Estratégia | Latência | Custo/query | Qualidade | Complexidade |
|---|---|---|---|---|
| BM25 | 5–30ms | $0 | baseline | Baixa |
| Busca Densa | 20–80ms | $0.02/1M embed | +20–30% | Média |
| Híbrida + RRF ⭐ | 30–120ms | BM25 + embed | +25–40% | Média |
| SPLADE | 20–60ms | $0 (local) | +15–25% | Média |
| MMR | +5–20ms | $0 | +5–15% diversidade | Baixa |
| Multi-Index | N× busca | N× embed | +20–35% | Alta |

### Pós-Retrieval

| Estratégia | Latência | Custo/query | Ganho qualidade | Complexidade |
|---|---|---|---|---|
| Cross-Encoder ⭐ | 80–300ms | $0 (local) | +20–35% | Baixa |
| LLM Reranker | 500ms–2s | $0.05–0.50 | +25–40% | Baixa |
| Context Compression | +200–600ms | +LLM | +10–20% | Média |
| Prompt Packing | <5ms | $0 | +5–15% | Baixa |
| Knowledge Strips | +500ms–2s | alto | +20–35% | Alta |
| Score Mínimo ⭐ | <1ms | $0 | −alucinação | Baixa |
| Citation Grounding | +50–200ms | +tokens | +confiança | Baixa |

---

## Combinações recomendadas

### Pipeline mínimo (POC / desenvolvimento)
```
[BM25] → [Busca Densa] → [RRF] → [Score Mínimo] → [LLM]
Latência: ~100ms | Custo: embedding apenas | Qualidade: boa
```

### Pipeline balanceado (produção padrão)
```
[Query Rewriting] → [BM25 + Densa + RRF] → [Cross-Encoder] → [Prompt Packing] → [Score Mínimo] → [LLM]
Latência: ~600ms | Custo: embedding + reranker local | Qualidade: muito boa
```

### Pipeline máxima qualidade (saúde / jurídico)
```
[Query Rewriting] → [HyDE] → [Híbrida + RRF] → [LLM Reranker] → [Context Compression] → [Score Mínimo] → [Citation Grounding] → [LLM]
Latência: ~2–3s | Custo: alto | Qualidade: máxima
```

### Pipeline econômico (custo mínimo)
```
[Query Routing] → [BM25] → [Score Mínimo] → [LLM barato (Groq)]
Latência: ~100ms | Custo: mínimo | Qualidade: aceitável para queries simples
```

### Configuração no BuscaAI (rag_settings.py)

```python
# Pipeline balanceado — recomendado para produção
PRE_FILTERING = {"enabled": True, "strategy": "bm25", "language": "pt"}

RETRIEVAL = {
    "strategy":       "hybrid",
    "top_k":          50,
    "reranker":       True,
    "reranker_model": "cross-encoder",
    "final_top_k":    5,
}

CHAT = {
    "reformulacao": {"enabled": True, "provider": "groq"},
}

LLM_FEATURES = {
    "query_expansion": {"enabled": False},
    "hyde":            {"enabled": False},
}

CACHE = {"enabled": True, "ttl": 3600}
```
