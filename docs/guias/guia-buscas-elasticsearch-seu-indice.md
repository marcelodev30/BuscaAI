# Guia de Buscas — Elasticsearch (aplicado ao seu índice)

> Todos os exemplos usam **os seus campos reais**: `text`, `vector`, `metadata.filename`, `metadata.headings`, `metadata.doc_id`, `metadata.pages`.
> Cada exemplo vem em duas versões: **Kibana Dev Tools** (copiar e colar) e **Python** (`elasticsearch` 8.x/9.x).
> Baseado na documentação oficial atual (Elasticsearch 9.x, agosto/2026).

---

## Índice

1. [Seu índice, decodificado](#1-seu-índice-decodificado)
2. [Antes de tudo: teste o analisador](#2-antes-de-tudo-teste-o-analisador)
3. [Preparação (Kibana e Python)](#3-preparação)
4. [Buscas léxicas (BM25) em `text`](#4-buscas-léxicas-bm25-em-text)
5. [Filtros por metadata](#5-filtros-por-metadata)
6. [Busca vetorial (kNN) em `vector`](#6-busca-vetorial-knn-em-vector)
7. [Busca híbrida com retrievers (RRF e linear)](#7-busca-híbrida-com-retrievers)
8. [Reranking e retrievers avançados](#8-reranking-e-retrievers-avançados)
9. [Agrupar chunks por documento (`collapse`)](#9-agrupar-chunks-por-documento-collapse)
10. [Highlight](#10-highlight)
11. [Agregações e facetas sobre metadata](#11-agregações-e-facetas)
12. [Paginação](#12-paginação)
13. [Diagnóstico: `_analyze`, `explain`, `profile`, `validate`](#13-diagnóstico)
14. [Classe Python pronta para uso](#14-classe-python-pronta-para-uso)
15. [Análise crítica do seu schema e melhorias](#15-análise-crítica-do-seu-schema)
16. [Mapping melhorado, completo](#16-mapping-melhorado-completo)
17. [Cheat sheet](#17-cheat-sheet)

---

## 1. Seu índice, decodificado

### O que cada peça faz

```python
"analyzer": {"pt_analyzer": {
    "type": "custom", "tokenizer": "standard",
    "filter": ["lowercase", "asciifolding", "pt_stop", "pt_stemmer"]}}
```

Pipeline aplicado ao campo `text`, **tanto na indexação quanto na busca**:

| Etapa | O que faz | Exemplo |
|---|---|---|
| `standard` (tokenizer) | Quebra em palavras, descarta pontuação | `"Não há garantia."` → `["Não", "há", "garantia"]` |
| `lowercase` | Minúsculas | → `["não", "há", "garantia"]` |
| `asciifolding` | Remove acentos | → `["nao", "ha", "garantia"]` |
| `pt_stop` | Remove palavras vazias `_brazilian_` | → `["nao", "ha", "garantia"]` ⚠️ |
| `pt_stemmer` | Reduz ao radical (`brazilian`) | → `["nao", "ha", "garant"]` |

⚠️ Repare no passo 4: **as stopwords não foram removidas.** Isso é um bug real na sua configuração e explico em detalhe na [seção 15](#15-análise-crítica-do-seu-schema). Antes disso, a [seção 2](#2-antes-de-tudo-teste-o-analisador) te mostra como confirmar isso no seu próprio cluster.

### Consequências práticas do stemming para as suas buscas

O `brazilian` stemmer é agressivo. Isso significa:

- ✅ `"garantias"`, `"garantido"` e `"garantir"` casam entre si — ótimo para recall.
- ❌ Termos exatos são destruídos: `"XR-4471"` vira `["xr", "4471"]`, e códigos com sufixos podem colidir.
- ❌ `match_phrase` funciona sobre os radicais, não sobre as palavras originais.
- ❌ **Você não tem um campo exato.** `text` só existe na versão analisada.

### O que o seu schema permite e o que não permite

| Operação | Possível? | Campo |
|---|---|---|
| Busca full-text em português | ✅ | `text` |
| Busca por frase (aproximada, sobre radicais) | ✅ | `text` |
| Busca por termo exato / código | ⚠️ Ruim | não existe campo exato |
| kNN vetorial | ✅ | `vector` |
| Híbrida (BM25 + kNN) | ✅ | `text` + `vector` |
| Filtrar por arquivo | ✅ | `metadata.filename` |
| Filtrar por documento | ✅ | `metadata.doc_id` |
| Filtrar por página | ✅ | `metadata.pages` |
| Agrupar chunks por documento | ✅ | `collapse` em `metadata.doc_id` |
| **Buscar texto dentro dos títulos** | ❌ | `headings` é `keyword`, não `text` |
| Ordenar por data / filtrar por recência | ❌ | não existe campo de data |
| Reconstruir a ordem dos chunks | ❌ | não existe `chunk_index` |
| Agregar sobre `text` | ❌ | `text` não tem `doc_values` |

---

## 2. Antes de tudo: teste o analisador

Rode isso primeiro. É o teste mais informativo que existe e leva 5 segundos.

**Kibana Dev Tools:**

```json
POST /SEU_INDICE/_analyze
{
  "analyzer": "pt_analyzer",
  "text": "Não há garantia para produtos importados após 12 meses"
}
```

**Python:**

```python
r = es.indices.analyze(
    index=INDICE,
    analyzer="pt_analyzer",
    text="Não há garantia para produtos importados após 12 meses",
)
print([t["token"] for t in r["tokens"]])
```

### Como ler o resultado

Se aparecerem tokens como `nao`, `ha`, `para`, `apos` na saída, **as stopwords não estão sendo removidas** — porque o `asciifolding` rodou antes do `pt_stop` e desacentuou as palavras, que então não bateram mais com a lista `_brazilian_` (que contém as formas acentuadas: `não`, `há`, `após`, `é`, `às`...).

Compare com a ordem correta:

```json
POST /_analyze
{
  "tokenizer": "standard",
  "filter": [
    "lowercase",
    {"type": "stop", "stopwords": "_brazilian_"},
    {"type": "stemmer", "language": "brazilian"},
    "asciifolding"
  ],
  "text": "Não há garantia para produtos importados após 12 meses"
}
```

Rode os dois lado a lado. A diferença no número de tokens é o tamanho do problema.

### Outros testes úteis de analisador

```json
// Ver o pipeline etapa por etapa
POST /SEU_INDICE/_analyze
{
  "analyzer": "pt_analyzer",
  "text": "garantias contratuais",
  "explain": true
}

// Ver como um campo específico analisa
POST /SEU_INDICE/_analyze
{
  "field": "text",
  "text": "instalação elétrica"
}

// Conferir se um código sobrevive ao stemming
POST /SEU_INDICE/_analyze
{
  "analyzer": "pt_analyzer",
  "text": "erro XR-4471 no módulo A2"
}
```

---

## 3. Preparação

### Kibana

Abra **Management → Dev Tools**. Cole os blocos que começam com `GET`, `POST` ou `PUT` e aperte ▶.

Descubra o nome do índice e confirme o mapping:

```json
GET _cat/indices?v&s=index

GET /SEU_INDICE/_mapping
GET /SEU_INDICE/_settings
GET /SEU_INDICE/_count
```

Veja um documento de exemplo, para saber com o que está lidando:

```json
GET /SEU_INDICE/_search
{
  "size": 1,
  "_source": {"excludes": ["vector"]}
}
```

### Python

```python
import os
from elasticsearch import Elasticsearch

INDICE = "seu_indice"

es = Elasticsearch(
    os.environ.get("ES_URL", "http://localhost:9200"),
    api_key=os.environ.get("ES_API_KEY"),
    request_timeout=30,
    max_retries=3,
    retry_on_timeout=True,
)

print(es.info()["version"]["number"])
print(es.count(index=INDICE)["count"])
```

> **Sobre `retriever=` no cliente Python:** o parâmetro existe a partir do cliente 8.16. Se a sua versão reclamar, atualize (`pip install -U "elasticsearch>=9,<10"`). Todos os exemplos com `retriever` dependem disso.

### Função auxiliar para imprimir resultados

Use em todos os exemplos Python daqui em diante:

```python
def mostrar(resposta, n=10):
    total = resposta["hits"]["total"]["value"]
    print(f"{total} resultados\n")
    for i, hit in enumerate(resposta["hits"]["hits"][:n], 1):
        src = hit["_source"]
        meta = src.get("metadata", {})
        print(f"{i}. score={hit['_score']:.4f}  "
              f"arquivo={meta.get('filename')}  "
              f"pag={meta.get('pages')}")
        print(f"   {src.get('text', '')[:180]}...")
        if "highlight" in hit:
            for frag in hit["highlight"].get("text", []):
                print(f"   >> {frag}")
        print()
```

---

## 4. Buscas léxicas (BM25) em `text`

### 4.1 `match` — o básico

Analisa a consulta com o `pt_analyzer` e casa por qualquer termo (OR).

**Kibana:**

```json
GET /SEU_INDICE/_search
{
  "size": 5,
  "_source": {"excludes": ["vector"]},
  "query": {
    "match": {"text": "prazo de garantia"}
  }
}
```

**Python:**

```python
r = es.search(
    index=INDICE,
    size=5,
    source={"excludes": ["vector"]},
    query={"match": {"text": "prazo de garantia"}},
)
mostrar(r)
```

> **Sempre exclua `vector` do `_source`.** Um vetor de 1024 dimensões em JSON tem ~15 KB. Com 10 resultados são 150 KB de tráfego inútil por busca. (Em ES 9.x isso já é o padrão — veja a [seção 15.6](#156-o-vector-no-_source).)

### 4.2 Exigindo todos os termos

```json
GET /SEU_INDICE/_search
{
  "query": {
    "match": {
      "text": {
        "query": "prazo garantia importados",
        "operator": "and"
      }
    }
  }
}
```

Ou uma fração mínima — mais flexível que `and`, mais preciso que `or`:

```json
GET /SEU_INDICE/_search
{
  "query": {
    "match": {
      "text": {
        "query": "prazo de garantia para produtos importados",
        "minimum_should_match": "70%"
      }
    }
  }
}
```

```python
r = es.search(index=INDICE, query={
    "match": {"text": {"query": "prazo de garantia para produtos importados",
                       "minimum_should_match": "70%"}}
})
```

### 4.3 `match_phrase` — sequência de termos

Atenção: no seu índice, a frase casa sobre os **radicais**. `"garantia estendida"` também encontra `"garantias estendidas"`.

```json
GET /SEU_INDICE/_search
{
  "query": {
    "match_phrase": {"text": "garantia estendida"}
  }
}
```

Com tolerância a palavras no meio:

```json
GET /SEU_INDICE/_search
{
  "query": {
    "match_phrase": {
      "text": {"query": "garantia produtos", "slop": 3}
    }
  }
}
```

```python
r = es.search(index=INDICE, query={
    "match_phrase": {"text": {"query": "garantia produtos", "slop": 3}}
})
```

### 4.4 `match_phrase_prefix` — busca conforme digita

```json
GET /SEU_INDICE/_search
{
  "query": {
    "match_phrase_prefix": {
      "text": {"query": "instalação elét", "max_expansions": 20}
    }
  }
}
```

### 4.5 Frase com fallback — padrão muito útil

Prioriza quem tem a frase exata, mas não descarta quem tem só os termos soltos:

```json
GET /SEU_INDICE/_search
{
  "query": {
    "bool": {
      "must": [
        {"match": {"text": {"query": "prazo de garantia",
                            "minimum_should_match": "60%"}}}
      ],
      "should": [
        {"match_phrase": {"text": {"query": "prazo de garantia", "boost": 3}}}
      ]
    }
  }
}
```

```python
r = es.search(index=INDICE, query={
    "bool": {
        "must": [{"match": {"text": {"query": "prazo de garantia",
                                     "minimum_should_match": "60%"}}}],
        "should": [{"match_phrase": {"text": {"query": "prazo de garantia",
                                              "boost": 3}}}],
    }
})
```

### 4.6 `simple_query_string` — seguro para caixa de busca do usuário

Aceita operadores (`+`, `-`, `"..."`, `*`) e **não quebra** com sintaxe inválida.

```json
GET /SEU_INDICE/_search
{
  "query": {
    "simple_query_string": {
      "query": "garantia +importado -usado",
      "fields": ["text"],
      "default_operator": "and"
    }
  }
}
```

> Prefira `simple_query_string` a `query_string` em qualquer input que venha do usuário final. O `query_string` lança exceção com parênteses desbalanceados.

### 4.7 Buscando também nos títulos

Como `metadata.headings` é `keyword`, `multi_match` funciona, mas casa o **valor inteiro**, não palavras soltas:

```json
GET /SEU_INDICE/_search
{
  "query": {
    "multi_match": {
      "query": "garantia",
      "fields": ["text", "metadata.headings^2"],
      "type": "best_fields"
    }
  }
}
```

Isso só encontra documentos cujo `headings` seja exatamente `"garantia"`. Para casar `"3.2 Política de garantia"`, você precisa de um sub-campo `text` — está na [seção 15.2](#152-headings-só-como-keyword).

Enquanto isso não existe, dá para contornar com `wildcard` (é lento, use com parcimônia):

```json
GET /SEU_INDICE/_search
{
  "query": {
    "bool": {
      "should": [
        {"match": {"text": "garantia"}},
        {"wildcard": {"metadata.headings": {"value": "*garantia*",
                                            "case_insensitive": true,
                                            "boost": 2}}}
      ]
    }
  }
}
```

### 4.8 `bool` — a estrutura que você mais vai usar

```json
GET /SEU_INDICE/_search
{
  "size": 10,
  "_source": {"excludes": ["vector"]},
  "query": {
    "bool": {
      "must": [
        {"match": {"text": "instalação elétrica"}}
      ],
      "filter": [
        {"term": {"metadata.filename": "manual_v3.pdf"}},
        {"range": {"metadata.pages": {"gte": 10, "lte": 50}}}
      ],
      "should": [
        {"match_phrase": {"text": {"query": "instalação elétrica", "boost": 2}}}
      ],
      "must_not": [
        {"term": {"metadata.doc_id": "rascunho-001"}}
      ]
    }
  }
}
```

**A distinção que importa:**

| Cláusula | Conta no score? | Cacheado? | Use para |
|---|---|---|---|
| `must` | Sim | Não | relevância obrigatória |
| `should` | Sim | Não | relevância opcional (boost) |
| `filter` | **Não** | **Sim** | condição binária sim/não |
| `must_not` | Não | Sim | exclusão |

Tudo que é sim/não (arquivo, página, doc_id) vai em `filter`. É mais rápido e o Elasticsearch guarda o bitset em cache.

```python
r = es.search(
    index=INDICE,
    size=10,
    source={"excludes": ["vector"]},
    query={
        "bool": {
            "must": [{"match": {"text": "instalação elétrica"}}],
            "filter": [
                {"term": {"metadata.filename": "manual_v3.pdf"}},
                {"range": {"metadata.pages": {"gte": 10, "lte": 50}}},
            ],
            "should": [{"match_phrase": {"text": {"query": "instalação elétrica",
                                                  "boost": 2}}}],
            "must_not": [{"term": {"metadata.doc_id": "rascunho-001"}}],
        }
    },
)
mostrar(r)
```

---

## 5. Filtros por metadata

Seus campos de filtro: `filename` (keyword), `headings` (keyword), `doc_id` (keyword), `pages` (integer).

### 5.1 Valor exato

```json
{"term": {"metadata.filename": "manual_v3.pdf"}}
```

> ⚠️ `keyword` é **case-sensitive**. `"Manual_v3.pdf"` não casa com `"manual_v3.pdf"`. Solução definitiva na [seção 15.3](#153-keyword-sem-normalizer).

### 5.2 Vários valores (IN)

```json
{"terms": {"metadata.filename": ["manual_v3.pdf", "anexo_a.pdf", "faq.md"]}}
```

### 5.3 Faixa de páginas

```json
{"range": {"metadata.pages": {"gte": 10, "lte": 50}}}
```

### 5.4 Campo presente / ausente

```json
{"exists": {"field": "metadata.headings"}}
```

Ausente:

```json
{"bool": {"must_not": [{"exists": {"field": "metadata.headings"}}]}}
```

### 5.5 Prefixo (ex.: todos os PDFs de um projeto)

```json
{"prefix": {"metadata.filename": "projeto_2026_"}}
```

### 5.6 Por IDs do Elasticsearch

```json
{"ids": {"values": ["chunk-001", "chunk-002"]}}
```

### 5.7 Filtro composto reutilizável (Python)

```python
def montar_filtro(
    arquivos: list[str] | None = None,
    doc_ids: list[str] | None = None,
    pagina_min: int | None = None,
    pagina_max: int | None = None,
    excluir_docs: list[str] | None = None,
) -> dict | None:
    must, must_not = [], []

    if arquivos:
        must.append({"terms": {"metadata.filename": arquivos}})
    if doc_ids:
        must.append({"terms": {"metadata.doc_id": doc_ids}})
    if pagina_min is not None or pagina_max is not None:
        faixa = {}
        if pagina_min is not None:
            faixa["gte"] = pagina_min
        if pagina_max is not None:
            faixa["lte"] = pagina_max
        must.append({"range": {"metadata.pages": faixa}})
    if excluir_docs:
        must_not.append({"terms": {"metadata.doc_id": excluir_docs}})

    if not must and not must_not:
        return None
    filtro = {}
    if must:
        filtro["must"] = must
    if must_not:
        filtro["must_not"] = must_not
    return {"bool": filtro}
```

### 5.8 Só filtro, sem relevância

Quando você quer *listar*, não *rankear*. Use `constant_score` para o Elasticsearch nem calcular score:

```json
GET /SEU_INDICE/_search
{
  "size": 100,
  "_source": {"excludes": ["vector"]},
  "query": {
    "constant_score": {
      "filter": {"term": {"metadata.doc_id": "manual-2026"}}
    }
  },
  "sort": [{"metadata.pages": "asc"}]
}
```

Esse é o padrão para "me devolva todos os chunks do documento X, em ordem".

---

## 6. Busca vetorial (kNN) em `vector`

Seu campo: `dense_vector`, `similarity: cosine`, `int8_hnsw`, `m: 16`, `ef_construction: 200`.

### 6.1 kNN básico

**Kibana** (substitua pelo vetor real — precisa ter exatamente `DIMS` posições):

```json
GET /SEU_INDICE/_search
{
  "size": 5,
  "_source": {"excludes": ["vector"]},
  "knn": {
    "field": "vector",
    "query_vector": [0.021, -0.043, 0.11],
    "k": 5,
    "num_candidates": 100
  }
}
```

**Python** (gerando o embedding de verdade):

```python
from sentence_transformers import SentenceTransformer

modelo = SentenceTransformer("intfloat/multilingual-e5-large")

def embed_consulta(texto: str) -> list[float]:
    # Modelos E5 exigem o prefixo "query: " — sem ele a qualidade cai muito
    return modelo.encode(f"query: {texto}", normalize_embeddings=True).tolist()

vetor = embed_consulta("qual o prazo de garantia?")

r = es.search(
    index=INDICE,
    size=5,
    source={"excludes": ["vector"]},
    knn={
        "field": "vector",
        "query_vector": vetor,
        "k": 5,
        "num_candidates": 100,
    },
)
mostrar(r)
```

> **Use exatamente o mesmo modelo que gerou os embeddings indexados.** Modelo diferente = vetores em espaços diferentes = resultados aleatórios, sem nenhuma mensagem de erro. Se você usou prefixos (`passage:` na indexação), use `query:` na busca.

### 6.2 `k` e `num_candidates` — o que ajustar

| Parâmetro | O que é | Efeito |
|---|---|---|
| `k` | Quantos resultados devolver | O tamanho da resposta |
| `num_candidates` | Quantos nós o HNSW visita por shard | ↑ = mais preciso, mais lento |

`num_candidates` precisa ser ≥ `k`. Regra prática: **`num_candidates` = 10× a 20× `k`**, com piso de 100. Se o recall estiver ruim, suba isso antes de mexer em qualquer outra coisa.

```json
"knn": {
  "field": "vector",
  "query_vector": [...],
  "k": 10,
  "num_candidates": 200
}
```

### 6.3 kNN com filtro

O filtro é aplicado **durante** a travessia do grafo, não depois. Você recebe `k` resultados que satisfazem o filtro.

```json
GET /SEU_INDICE/_search
{
  "size": 5,
  "_source": {"excludes": ["vector"]},
  "knn": {
    "field": "vector",
    "query_vector": [...],
    "k": 5,
    "num_candidates": 100,
    "filter": {
      "bool": {
        "must": [
          {"terms": {"metadata.filename": ["manual_v3.pdf", "anexo_a.pdf"]}}
        ]
      }
    }
  }
}
```

```python
r = es.search(
    index=INDICE,
    size=5,
    source={"excludes": ["vector"]},
    knn={
        "field": "vector",
        "query_vector": vetor,
        "k": 5,
        "num_candidates": 100,
        "filter": {"terms": {"metadata.filename": ["manual_v3.pdf"]}},
    },
)
```

> Quando o filtro é muito restritivo (sobram poucos documentos), **aumente `num_candidates`**. Com filtro apertado o HNSW precisa caminhar mais para achar `k` candidatos válidos.

### 6.4 Oversampling e rescore — recuperando precisão da quantização

Seu campo usa `int8_hnsw`, que comprime cada dimensão para 1 byte. Isso economiza 75% de memória com uma pequena perda de precisão. O `rescore_vector` recupera essa precisão: busca mais candidatos usando os vetores comprimidos e depois reordena o topo com os vetores originais (que continuam no disco).

```json
GET /SEU_INDICE/_search
{
  "size": 10,
  "_source": {"excludes": ["vector"]},
  "knn": {
    "field": "vector",
    "query_vector": [...],
    "k": 10,
    "num_candidates": 100,
    "rescore_vector": {"oversample": 2.0}
  }
}
```

```python
r = es.search(
    index=INDICE,
    size=10,
    source={"excludes": ["vector"]},
    knn={
        "field": "vector", "query_vector": vetor,
        "k": 10, "num_candidates": 100,
        "rescore_vector": {"oversample": 2.0},
    },
)
```

Vale muito a pena testar. O custo em latência é pequeno e o ganho de recall costuma ser perceptível. Valores entre 1.5 e 3.0 são o intervalo útil.

### 6.5 Múltiplos vetores de consulta

Útil quando você quer buscar com a pergunta original **e** com uma versão reescrita:

```json
GET /SEU_INDICE/_search
{
  "knn": [
    {"field": "vector", "query_vector": [...], "k": 10,
     "num_candidates": 100, "boost": 1.0},
    {"field": "vector", "query_vector": [...], "k": 10,
     "num_candidates": 100, "boost": 0.5}
  ]
}
```

### 6.6 kNN exato (`script_score`) — para medir recall

Força varredura completa, sem HNSW. Lento, mas dá a resposta *perfeita* — serve de referência para você medir quanto o índice aproximado está errando.

```json
GET /SEU_INDICE/_search
{
  "size": 10,
  "_source": {"excludes": ["vector"]},
  "query": {
    "script_score": {
      "query": {
        "bool": {"filter": [{"term": {"metadata.filename": "manual_v3.pdf"}}]}
      },
      "script": {
        "source": "cosineSimilarity(params.qv, 'vector') + 1.0",
        "params": {"qv": [...]}
      }
    }
  }
}
```

> Use apenas em subconjuntos pequenos (sempre com filtro) ou em avaliação offline. Em toda a base isso derruba o cluster.

**Medindo o recall do seu índice:**

```python
def medir_recall(consultas: list[str], k: int = 10) -> float:
    acertos = total = 0
    for consulta in consultas:
        v = embed_consulta(consulta)

        aprox = es.search(index=INDICE, size=k, source=False,
                          knn={"field": "vector", "query_vector": v,
                               "k": k, "num_candidates": 100})
        exato = es.search(index=INDICE, size=k, source=False, query={
            "script_score": {
                "query": {"match_all": {}},
                "script": {"source": "cosineSimilarity(params.qv,'vector')+1.0",
                           "params": {"qv": v}},
            }
        })

        ids_aprox = {h["_id"] for h in aprox["hits"]["hits"]}
        ids_exato = {h["_id"] for h in exato["hits"]["hits"]}
        acertos += len(ids_aprox & ids_exato)
        total += len(ids_exato)

    return acertos / total if total else 0.0

print(f"Recall@10: {medir_recall(['garantia', 'instalação', 'preço']):.1%}")
```

Se o recall vier abaixo de ~0.9, suba `num_candidates` ou ative `rescore_vector`.

---

## 7. Busca híbrida com retrievers

Esta é a parte mais importante do guia. Seu índice tem `text` e `vector`, e cada um acerta onde o outro erra:

- **BM25** acerta termos exatos, códigos, nomes próprios. Erra sinônimos e paráfrases.
- **kNN** acerta sentido e paráfrase. Erra código de produto e sigla.

A fusão dos dois é quase sempre melhor que qualquer um sozinho.

### 7.1 RRF — Reciprocal Rank Fusion

O RRF combina as listas pela **posição**, não pelo score. Isso é o que faz funcionar sem calibração: não importa que BM25 dê score 14.7 e kNN dê 0.83, o que conta é quem ficou em 1º, 2º, 3º.

**Kibana:**

```json
GET /SEU_INDICE/_search
{
  "size": 10,
  "_source": {"excludes": ["vector"]},
  "retriever": {
    "rrf": {
      "retrievers": [
        {
          "standard": {
            "query": {
              "match": {"text": "prazo de garantia para importados"}
            }
          }
        },
        {
          "knn": {
            "field": "vector",
            "query_vector": [...],
            "k": 50,
            "num_candidates": 200
          }
        }
      ],
      "rank_window_size": 50,
      "rank_constant": 60
    }
  }
}
```

**Python:**

```python
consulta = "prazo de garantia para importados"
vetor = embed_consulta(consulta)

r = es.search(
    index=INDICE,
    size=10,
    source={"excludes": ["vector"]},
    retriever={
        "rrf": {
            "retrievers": [
                {"standard": {"query": {"match": {"text": consulta}}}},
                {"knn": {"field": "vector", "query_vector": vetor,
                         "k": 50, "num_candidates": 200}},
            ],
            "rank_window_size": 50,
            "rank_constant": 60,
        }
    },
)
mostrar(r)
```

**Parâmetros do RRF:**

| Parâmetro | Padrão | O que faz |
|---|---|---|
| `rank_window_size` | 10 | Quantos documentos cada sub-retriever contribui. Deve ser ≥ `size`. Comece com 50–100. |
| `rank_constant` | 60 | Suaviza o peso das posições. Menor = topo domina mais. Raramente precisa mexer. |

> Se `k` do kNN for maior que `rank_window_size`, os resultados são truncados. Mantenha `k` ≥ `rank_window_size` para não desperdiçar busca.

### 7.2 RRF com pesos

Quando você quer dar mais importância a uma das pernas:

```json
GET /SEU_INDICE/_search
{
  "size": 10,
  "retriever": {
    "rrf": {
      "retrievers": [
        {
          "retriever": {
            "standard": {"query": {"match": {"text": "garantia"}}}
          },
          "weight": 1.0
        },
        {
          "retriever": {
            "knn": {"field": "vector", "query_vector": [...],
                    "k": 50, "num_candidates": 200}
          },
          "weight": 2.0
        }
      ],
      "rank_window_size": 50
    }
  }
}
```

Repare na diferença de sintaxe: com peso, cada item vira `{"retriever": {...}, "weight": N}`. Sem peso, é o retriever direto. Você pode misturar os dois formatos na mesma query.

### 7.3 Híbrida com filtro

O filtro precisa entrar **em cada perna** — o RRF não tem filtro global.

```json
GET /SEU_INDICE/_search
{
  "size": 10,
  "_source": {"excludes": ["vector"]},
  "retriever": {
    "rrf": {
      "retrievers": [
        {
          "standard": {
            "query": {
              "bool": {
                "must": [{"match": {"text": "garantia"}}],
                "filter": [{"term": {"metadata.filename": "manual_v3.pdf"}}]
              }
            }
          }
        },
        {
          "knn": {
            "field": "vector",
            "query_vector": [...],
            "k": 50,
            "num_candidates": 200,
            "filter": {"term": {"metadata.filename": "manual_v3.pdf"}}
          }
        }
      ],
      "rank_window_size": 50
    }
  }
}
```

```python
def buscar_hibrida(consulta: str, filtro: dict | None = None, tamanho: int = 10):
    vetor = embed_consulta(consulta)

    lexica = {"bool": {"must": [{"match": {"text": consulta}}]}}
    knn = {"field": "vector", "query_vector": vetor,
           "k": 50, "num_candidates": 200}

    if filtro:
        lexica["bool"]["filter"] = [filtro]
        knn["filter"] = filtro

    return es.search(
        index=INDICE,
        size=tamanho,
        source={"excludes": ["vector"]},
        retriever={
            "rrf": {
                "retrievers": [
                    {"standard": {"query": lexica}},
                    {"knn": knn},
                ],
                "rank_window_size": 50,
                "rank_constant": 60,
            }
        },
    )

r = buscar_hibrida(
    "prazo de garantia",
    filtro={"terms": {"metadata.filename": ["manual_v3.pdf"]}},
)
mostrar(r)
```

### 7.4 Retriever `linear` — combinando scores em vez de posições

Alternativa ao RRF. Combina os scores brutos, normalizados. Dá mais controle, mas exige calibração.

```json
GET /SEU_INDICE/_search
{
  "size": 10,
  "retriever": {
    "linear": {
      "retrievers": [
        {
          "retriever": {"standard": {"query": {"match": {"text": "garantia"}}}},
          "weight": 1.0,
          "normalizer": "minmax"
        },
        {
          "retriever": {"knn": {"field": "vector", "query_vector": [...],
                                "k": 50, "num_candidates": 200}},
          "weight": 1.5,
          "normalizer": "minmax"
        }
      ],
      "rank_window_size": 50
    }
  }
}
```

**RRF ou linear?**

| | RRF | Linear |
|---|---|---|
| Precisa calibrar | Não | Sim |
| Sensível à escala dos scores | Não | Sim |
| Controle fino do peso | Limitado | Total |
| Recomendação | **Comece aqui** | Quando o RRF não basta |

> No `linear`, use `normalizer: "minmax"` ou `"l2_norm"`. Com `"none"`, os scores não são normalizados e o resultado vai pender fortemente para a perna léxica, que tem escala maior.

### 7.5 Três pernas: semântica + frase exata + termos

Padrão de alta qualidade quando você quer cobrir todos os casos:

```json
GET /SEU_INDICE/_search
{
  "size": 10,
  "_source": {"excludes": ["vector"]},
  "retriever": {
    "rrf": {
      "retrievers": [
        {"standard": {"query": {"match": {"text": "garantia estendida importados"}}}},
        {"standard": {"query": {"match_phrase": {"text": "garantia estendida"}}}},
        {"knn": {"field": "vector", "query_vector": [...],
                 "k": 50, "num_candidates": 200}}
      ],
      "rank_window_size": 60
    }
  }
}
```

---

## 8. Reranking e retrievers avançados

Os retrievers disponíveis hoje: `standard`, `knn`, `rrf`, `linear`, `text_similarity_reranker`, `rescorer`, `pinned`, `rule`, `diversify`.

### 8.1 `text_similarity_reranker` — o maior ganho de qualidade

Busca amplo, reordena o topo com um cross-encoder. Requer um endpoint de inference configurado no cluster.

Criando o endpoint:

```json
PUT _inference/rerank/meu-reranker
{
  "service": "cohere",
  "service_settings": {
    "api_key": "SUA_CHAVE",
    "model_id": "rerank-multilingual-v3.0"
  }
}
```

Usando em cima da híbrida:

```json
GET /SEU_INDICE/_search
{
  "size": 5,
  "_source": {"excludes": ["vector"]},
  "retriever": {
    "text_similarity_reranker": {
      "retriever": {
        "rrf": {
          "retrievers": [
            {"standard": {"query": {"match": {"text": "prazo de garantia"}}}},
            {"knn": {"field": "vector", "query_vector": [...],
                     "k": 50, "num_candidates": 200}}
          ],
          "rank_window_size": 50
        }
      },
      "field": "text",
      "inference_id": "meu-reranker",
      "inference_text": "qual o prazo de garantia para produtos importados?",
      "rank_window_size": 50
    }
  }
}
```

```python
r = es.search(
    index=INDICE,
    size=5,
    source={"excludes": ["vector"]},
    retriever={
        "text_similarity_reranker": {
            "retriever": {
                "rrf": {
                    "retrievers": [
                        {"standard": {"query": {"match": {"text": consulta}}}},
                        {"knn": {"field": "vector", "query_vector": vetor,
                                 "k": 50, "num_candidates": 200}},
                    ],
                    "rank_window_size": 50,
                }
            },
            "field": "text",
            "inference_id": "meu-reranker",
            "inference_text": consulta,
            "rank_window_size": 50,
        }
    },
)
```

Repare na composição: o `text_similarity_reranker` recebe um `rrf` como filho, que por sua vez recebe `standard` e `knn`. Essa árvore é a força do modelo de retrievers.

**Alternativa sem endpoint no cluster** — rerankear do lado do Python:

```python
from sentence_transformers import CrossEncoder

cross = CrossEncoder("BAAI/bge-reranker-v2-m3")

def buscar_com_rerank(consulta: str, top: int = 5, candidatos: int = 40):
    r = buscar_hibrida(consulta, tamanho=candidatos)
    hits = r["hits"]["hits"]
    if not hits:
        return []

    pares = [(consulta, h["_source"]["text"]) for h in hits]
    notas = cross.predict(pares)

    ordenados = sorted(zip(hits, notas), key=lambda x: x[1], reverse=True)
    return [
        {**h["_source"], "_score_rerank": float(nota), "_id": h["_id"]}
        for h, nota in ordenados[:top]
    ]

for doc in buscar_com_rerank("prazo de garantia para importados"):
    print(f"{doc['_score_rerank']:.3f}  {doc['text'][:120]}")
```

**Se você só puder fazer uma melhoria na sua busca, faça esta.** O ganho costuma ser maior que trocar o modelo de embedding ou ajustar chunking.

### 8.2 `diversify` — evitando 5 chunks quase idênticos

Problema clássico em RAG: os 5 primeiros resultados são o mesmo parágrafo em variações.

```json
GET /SEU_INDICE/_search
{
  "size": 5,
  "retriever": {
    "diversify": {
      "retriever": {
        "knn": {"field": "vector", "query_vector": [...],
                "k": 50, "num_candidates": 200}
      },
      "field": "metadata.doc_id",
      "max_per_group": 2
    }
  }
}
```

> A disponibilidade e os parâmetros exatos do `diversify` variam por versão. Confirme com `GET /_xpack` ou consulte a doc da sua versão. A alternativa universal é `collapse` (seção 9).

### 8.3 `pinned` — fixando resultados no topo

Para quando existe uma resposta canônica que deve sempre aparecer primeiro:

```json
GET /SEU_INDICE/_search
{
  "size": 10,
  "retriever": {
    "pinned": {
      "ids": ["chunk-garantia-oficial"],
      "retriever": {
        "standard": {"query": {"match": {"text": "garantia"}}}
      }
    }
  }
}
```

### 8.4 `rescorer` — reordenar o topo com uma query cara

```json
GET /SEU_INDICE/_search
{
  "size": 10,
  "retriever": {
    "rescorer": {
      "retriever": {
        "standard": {"query": {"match": {"text": "garantia produtos"}}}
      },
      "rescore": {
        "window_size": 50,
        "query": {
          "rescore_query": {
            "match_phrase": {"text": {"query": "garantia produtos", "slop": 2}}
          },
          "query_weight": 0.7,
          "rescore_query_weight": 1.3
        }
      }
    }
  }
}
```

Barato e eficaz: busca ampla com `match`, depois promove quem tem a frase quase exata.

### 8.5 Restrições ao usar `retriever`

Quando você usa `retriever`, estes elementos **não são permitidos no nível superior**:

- `query`
- `knn`
- `search_after`
- `terminate_after`
- `sort`
- `rescore` (use o retriever `rescorer`)

`from`, `size`, `aggs`, `highlight` e `collapse` continuam funcionando normalmente.

---

## 9. Agrupar chunks por documento (`collapse`)

Sem isso, uma busca pode devolver 10 chunks do mesmo PDF e nenhum dos outros documentos. Em RAG isso é péssimo — você enche o contexto com uma fonte só.

```json
GET /SEU_INDICE/_search
{
  "size": 5,
  "_source": {"excludes": ["vector"]},
  "query": {"match": {"text": "garantia"}},
  "collapse": {
    "field": "metadata.doc_id",
    "inner_hits": {
      "name": "melhores_chunks",
      "size": 3,
      "_source": {"excludes": ["vector"]}
    }
  }
}
```

Isso devolve **5 documentos distintos**, cada um com seus 3 melhores chunks.

```python
r = es.search(
    index=INDICE,
    size=5,
    source={"excludes": ["vector"]},
    query={"match": {"text": "garantia"}},
    collapse={
        "field": "metadata.doc_id",
        "inner_hits": {
            "name": "melhores_chunks",
            "size": 3,
            "_source": {"excludes": ["vector"]},
        },
    },
)

for hit in r["hits"]["hits"]:
    doc_id = hit["fields"]["metadata.doc_id"][0]
    print(f"\n=== {doc_id} (score {hit['_score']:.3f})")
    for inner in hit["inner_hits"]["melhores_chunks"]["hits"]["hits"]:
        print(f"   p.{inner['_source']['metadata'].get('pages')}: "
              f"{inner['_source']['text'][:120]}")
```

Funciona junto com retrievers:

```json
GET /SEU_INDICE/_search
{
  "size": 5,
  "retriever": {
    "rrf": {
      "retrievers": [
        {"standard": {"query": {"match": {"text": "garantia"}}}},
        {"knn": {"field": "vector", "query_vector": [...],
                 "k": 50, "num_candidates": 200}}
      ],
      "rank_window_size": 50
    }
  },
  "collapse": {"field": "metadata.doc_id"}
}
```

### Expandindo o contexto: buscando os chunks vizinhos

Depois de achar o chunk certo, você geralmente quer os vizinhos para dar contexto ao LLM. Com o seu schema atual dá para aproximar usando `pages`:

```python
def buscar_vizinhos(doc_id: str, pagina: int, janela: int = 1) -> list[dict]:
    r = es.search(
        index=INDICE,
        size=20,
        source={"excludes": ["vector"]},
        query={
            "bool": {
                "filter": [
                    {"term": {"metadata.doc_id": doc_id}},
                    {"range": {"metadata.pages": {
                        "gte": pagina - janela, "lte": pagina + janela}}},
                ]
            }
        },
        sort=[{"metadata.pages": "asc"}],
    )
    return [h["_source"] for h in r["hits"]["hits"]]
```

> Isso é uma aproximação. Com um campo `chunk_index` (seção 15.4) ficaria exato.

---

## 10. Highlight

Mostra ao usuário *por que* aquele resultado apareceu.

```json
GET /SEU_INDICE/_search
{
  "size": 5,
  "_source": {"excludes": ["vector"]},
  "query": {"match": {"text": "prazo de garantia"}},
  "highlight": {
    "fields": {
      "text": {
        "fragment_size": 200,
        "number_of_fragments": 3,
        "pre_tags": ["<mark>"],
        "post_tags": ["</mark>"]
      }
    }
  }
}
```

```python
r = es.search(
    index=INDICE,
    size=5,
    source={"excludes": ["vector"]},
    query={"match": {"text": "prazo de garantia"}},
    highlight={
        "fields": {"text": {"fragment_size": 200, "number_of_fragments": 3}},
        "pre_tags": ["<mark>"],
        "post_tags": ["</mark>"],
    },
)

for hit in r["hits"]["hits"]:
    for frag in hit.get("highlight", {}).get("text", []):
        print(frag)
```

Chunk inteiro destacado, sem fragmentar:

```json
"highlight": {
  "fields": {
    "text": {"number_of_fragments": 0}
  }
}
```

> O highlight destaca as palavras que casaram **após o stemming**. Buscar `"garantia"` destaca também `"garantias"` e `"garantido"`. Isso é esperado.
>
> Em híbrida com RRF, o highlight só funciona nas pernas léxicas — kNN não tem termos para destacar.

---

## 11. Agregações e facetas

### 11.1 Quais arquivos têm o assunto

```json
GET /SEU_INDICE/_search
{
  "size": 0,
  "query": {"match": {"text": "garantia"}},
  "aggs": {
    "por_arquivo": {
      "terms": {"field": "metadata.filename", "size": 20}
    }
  }
}
```

```python
r = es.search(
    index=INDICE,
    size=0,
    query={"match": {"text": "garantia"}},
    aggs={"por_arquivo": {"terms": {"field": "metadata.filename", "size": 20}}},
)
for b in r["aggregations"]["por_arquivo"]["buckets"]:
    print(f"{b['key']}: {b['doc_count']} chunks")
```

### 11.2 Facetas completas para uma interface de busca

```json
GET /SEU_INDICE/_search
{
  "size": 10,
  "_source": {"excludes": ["vector"]},
  "query": {"match": {"text": "instalação"}},
  "aggs": {
    "arquivos": {"terms": {"field": "metadata.filename", "size": 20}},
    "secoes":   {"terms": {"field": "metadata.headings", "size": 30}},
    "documentos": {"terms": {"field": "metadata.doc_id", "size": 20}},
    "faixa_paginas": {
      "range": {
        "field": "metadata.pages",
        "ranges": [
          {"key": "1-20",   "to": 21},
          {"key": "21-50",  "from": 21, "to": 51},
          {"key": "51+",    "from": 51}
        ]
      }
    },
    "total_documentos": {"cardinality": {"field": "metadata.doc_id"}}
  }
}
```

### 11.3 Estatísticas da base (sem busca)

```json
GET /SEU_INDICE/_search
{
  "size": 0,
  "aggs": {
    "documentos_distintos": {"cardinality": {"field": "metadata.doc_id"}},
    "arquivos_distintos":   {"cardinality": {"field": "metadata.filename"}},
    "paginas": {"stats": {"field": "metadata.pages"}},
    "chunks_por_documento": {
      "terms": {"field": "metadata.doc_id", "size": 10,
                "order": {"_count": "desc"}}
    }
  }
}
```

Muito útil para auditar a ingestão: se um documento tem 900 chunks e os outros têm 12, provavelmente algo deu errado no chunking dele.

### 11.4 Encontrar documentos sem seção

```json
GET /SEU_INDICE/_search
{
  "size": 0,
  "query": {
    "bool": {"must_not": [{"exists": {"field": "metadata.headings"}}]}
  },
  "aggs": {
    "arquivos_sem_secao": {"terms": {"field": "metadata.filename", "size": 50}}
  }
}
```

> Não dá para agregar sobre `text` — campos `text` não têm `doc_values`. Se precisar de nuvem de termos, use a agregação `significant_text` (que é cara) ou adicione um sub-campo `keyword`.

---

## 12. Paginação

### `from` + `size` — até 10.000

```json
GET /SEU_INDICE/_search
{
  "from": 20,
  "size": 10,
  "_source": {"excludes": ["vector"]},
  "query": {"match": {"text": "garantia"}}
}
```

### `search_after` — paginação profunda

```json
GET /SEU_INDICE/_search
{
  "size": 50,
  "_source": {"excludes": ["vector"]},
  "query": {"match_all": {}},
  "sort": [{"metadata.doc_id": "asc"}, {"_shard_doc": "asc"}],
  "search_after": ["manual-2026", 1234]
}
```

### Varrer tudo (Python)

```python
from elasticsearch import helpers

for doc in helpers.scan(
    es,
    index=INDICE,
    query={
        "query": {"term": {"metadata.doc_id": "manual-2026"}},
        "_source": {"excludes": ["vector"]},
    },
    size=500,
):
    print(doc["_source"]["metadata"]["pages"], doc["_source"]["text"][:80])
```

> `search_after` não é permitido no nível superior junto com `retriever`.

---

## 13. Diagnóstico

### 13.1 A query está sintaticamente correta?

```json
GET /SEU_INDICE/_validate/query?explain=true
{
  "query": {"match": {"text": "garantia"}}
}
```

### 13.2 Por que este documento tem esse score?

```json
GET /SEU_INDICE/_explain/ID_DO_DOCUMENTO
{
  "query": {"match": {"text": "prazo de garantia"}}
}
```

```python
r = es.explain(index=INDICE, id="chunk-001",
               query={"match": {"text": "prazo de garantia"}})
print(r["explanation"])
```

### 13.3 Onde o tempo está sendo gasto?

```json
GET /SEU_INDICE/_search
{
  "profile": true,
  "query": {"match": {"text": "garantia"}}
}
```

A saída é longa. Procure por `time_in_nanos` nas fases `query` e `collector`.

### 13.4 Quanto disco cada campo ocupa

```json
POST /SEU_INDICE/_disk_usage?run_expensive_tasks=true
```

Isso mostra exatamente quanto do índice é `vector` versus `text`. Normalmente a resposta é surpreendente.

### 13.5 Checklist quando a busca não acha o que existe

```json
// 1. O documento existe na base?
GET /SEU_INDICE/_search
{
  "query": {"match_phrase": {"text": "trecho literal que você sabe que existe"}}
}

// 2. E sem análise nenhuma, procurando o termo cru?
GET /SEU_INDICE/_search
{
  "query": {"wildcard": {"metadata.filename": "*manual*"}}
}

// 3. Como o analisador tratou a sua consulta?
POST /SEU_INDICE/_analyze
{"analyzer": "pt_analyzer", "text": "sua consulta aqui"}

// 4. E o texto do documento?
POST /SEU_INDICE/_analyze
{"analyzer": "pt_analyzer", "text": "o texto do documento aqui"}
```

**Compare as saídas de 3 e 4.** Se não houver token em comum, o `match` nunca vai casar — e o problema é de análise, não de query.

### 13.6 Tabela de sintomas

| Sintoma | Causa provável | Verificação |
|---|---|---|
| Busca não acha texto que existe | Análise diferente entre consulta e documento | `_analyze` nos dois (13.5) |
| Stopwords aparecem nos tokens | `asciifolding` antes de `pt_stop` | Seção 15.1 |
| Código/sigla não é encontrado | Stemming destruiu o termo | Falta campo exato (15.2) |
| `term` em `filename` não casa | Case-sensitive | Seção 15.3 |
| kNN devolve resultados ruins | Modelo de embedding diferente do indexado | Confira o modelo e os prefixos |
| kNN perde documentos óbvios | `num_candidates` baixo | Suba para 200–500 |
| Resultados repetitivos | Vários chunks do mesmo doc | `collapse` (seção 9) |
| Resposta enorme e lenta | `vector` vindo no `_source` | `_source.excludes` |
| Híbrida pior que kNN sozinho | `rank_window_size` pequeno demais | Suba para 50–100 |

---

## 14. Classe Python pronta para uso

Junta tudo em algo que você pode colar no seu projeto:

```python
import os
from dataclasses import dataclass, field
from typing import Any, Literal

from elasticsearch import Elasticsearch
from sentence_transformers import SentenceTransformer


@dataclass
class Resultado:
    id: str
    score: float
    texto: str
    filename: str | None = None
    doc_id: str | None = None
    pages: Any = None
    headings: Any = None
    destaques: list[str] = field(default_factory=list)


class BuscadorRAG:
    def __init__(
        self,
        indice: str,
        es_url: str | None = None,
        api_key: str | None = None,
        modelo_embedding: str = "intfloat/multilingual-e5-large",
        prefixo_consulta: str = "query: ",
    ):
        self.indice = indice
        self.prefixo = prefixo_consulta
        self.es = Elasticsearch(
            es_url or os.environ.get("ES_URL", "http://localhost:9200"),
            api_key=api_key or os.environ.get("ES_API_KEY"),
            request_timeout=30,
            max_retries=3,
            retry_on_timeout=True,
        )
        self.modelo = SentenceTransformer(modelo_embedding)

    # ---------- helpers ----------

    def _embed(self, texto: str) -> list[float]:
        return self.modelo.encode(
            f"{self.prefixo}{texto}", normalize_embeddings=True
        ).tolist()

    @staticmethod
    def _para_resultados(resposta: dict) -> list[Resultado]:
        saida = []
        for hit in resposta["hits"]["hits"]:
            src = hit["_source"]
            meta = src.get("metadata", {})
            saida.append(Resultado(
                id=hit["_id"],
                score=hit["_score"] or 0.0,
                texto=src.get("text", ""),
                filename=meta.get("filename"),
                doc_id=meta.get("doc_id"),
                pages=meta.get("pages"),
                headings=meta.get("headings"),
                destaques=hit.get("highlight", {}).get("text", []),
            ))
        return saida

    @staticmethod
    def _filtro(
        arquivos: list[str] | None = None,
        doc_ids: list[str] | None = None,
        paginas: tuple[int | None, int | None] | None = None,
    ) -> dict | None:
        clausulas = []
        if arquivos:
            clausulas.append({"terms": {"metadata.filename": arquivos}})
        if doc_ids:
            clausulas.append({"terms": {"metadata.doc_id": doc_ids}})
        if paginas:
            minimo, maximo = paginas
            faixa = {}
            if minimo is not None:
                faixa["gte"] = minimo
            if maximo is not None:
                faixa["lte"] = maximo
            if faixa:
                clausulas.append({"range": {"metadata.pages": faixa}})

        if not clausulas:
            return None
        if len(clausulas) == 1:
            return clausulas[0]
        return {"bool": {"must": clausulas}}

    # ---------- buscas ----------

    def lexica(self, consulta: str, k: int = 10, **filtros) -> list[Resultado]:
        f = self._filtro(**filtros)
        query: dict = {
            "bool": {
                "must": [{"match": {"text": {"query": consulta,
                                             "minimum_should_match": "60%"}}}],
                "should": [{"match_phrase": {"text": {"query": consulta,
                                                      "boost": 3}}}],
            }
        }
        if f:
            query["bool"]["filter"] = [f]

        r = self.es.search(
            index=self.indice, size=k,
            source={"excludes": ["vector"]},
            query=query,
            highlight={"fields": {"text": {"fragment_size": 200,
                                           "number_of_fragments": 2}}},
        )
        return self._para_resultados(r)

    def vetorial(self, consulta: str, k: int = 10,
                 num_candidates: int = 200, oversample: float | None = 2.0,
                 **filtros) -> list[Resultado]:
        f = self._filtro(**filtros)
        knn: dict = {
            "field": "vector",
            "query_vector": self._embed(consulta),
            "k": k,
            "num_candidates": num_candidates,
        }
        if f:
            knn["filter"] = f
        if oversample:
            knn["rescore_vector"] = {"oversample": oversample}

        r = self.es.search(
            index=self.indice, size=k,
            source={"excludes": ["vector"]},
            knn=knn,
        )
        return self._para_resultados(r)

    def hibrida(self, consulta: str, k: int = 10,
                janela: int = 50, peso_lexico: float = 1.0,
                peso_vetorial: float = 1.0,
                agrupar_por_documento: bool = False,
                **filtros) -> list[Resultado]:
        f = self._filtro(**filtros)

        lexica: dict = {"bool": {"must": [{"match": {"text": consulta}}]}}
        knn: dict = {
            "field": "vector",
            "query_vector": self._embed(consulta),
            "k": janela,
            "num_candidates": janela * 4,
        }
        if f:
            lexica["bool"]["filter"] = [f]
            knn["filter"] = f

        corpo: dict = {
            "retriever": {
                "rrf": {
                    "retrievers": [
                        {"retriever": {"standard": {"query": lexica}},
                         "weight": peso_lexico},
                        {"retriever": {"knn": knn}, "weight": peso_vetorial},
                    ],
                    "rank_window_size": janela,
                    "rank_constant": 60,
                }
            },
            "size": k,
            "_source": {"excludes": ["vector"]},
            "highlight": {"fields": {"text": {"fragment_size": 200,
                                              "number_of_fragments": 2}}},
        }
        if agrupar_por_documento:
            corpo["collapse"] = {
                "field": "metadata.doc_id",
                "inner_hits": {"name": "chunks", "size": 3,
                               "_source": {"excludes": ["vector"]}},
            }

        r = self.es.search(index=self.indice, **corpo)
        return self._para_resultados(r)

    # ---------- utilidades para RAG ----------

    def contexto_para_llm(self, consulta: str, k: int = 5,
                          modo: Literal["lexica", "vetorial", "hibrida"] = "hibrida",
                          **filtros) -> str:
        metodo = getattr(self, modo)
        resultados = metodo(consulta, k=k, **filtros)
        return "\n\n---\n\n".join(
            f"[Fonte: {r.filename} | Página: {r.pages} | Seção: {r.headings}]\n{r.texto}"
            for r in resultados
        )

    def chunks_do_documento(self, doc_id: str) -> list[Resultado]:
        r = self.es.search(
            index=self.indice, size=500,
            source={"excludes": ["vector"]},
            query={"constant_score": {
                "filter": {"term": {"metadata.doc_id": doc_id}}}},
            sort=[{"metadata.pages": "asc"}],
        )
        return self._para_resultados(r)

    def estatisticas(self) -> dict:
        r = self.es.search(
            index=self.indice, size=0,
            aggs={
                "documentos": {"cardinality": {"field": "metadata.doc_id"}},
                "arquivos": {"cardinality": {"field": "metadata.filename"}},
                "paginas": {"stats": {"field": "metadata.pages"}},
                "maiores": {"terms": {"field": "metadata.doc_id", "size": 5}},
            },
        )
        a = r["aggregations"]
        return {
            "total_chunks": self.es.count(index=self.indice)["count"],
            "documentos": a["documentos"]["value"],
            "arquivos": a["arquivos"]["value"],
            "paginas": a["paginas"],
            "maiores_documentos": {b["key"]: b["doc_count"]
                                   for b in a["maiores"]["buckets"]},
        }

    def testar_analise(self, texto: str) -> list[str]:
        r = self.es.indices.analyze(index=self.indice,
                                    analyzer="pt_analyzer", text=texto)
        return [t["token"] for t in r["tokens"]]


# ---------- uso ----------

if __name__ == "__main__":
    b = BuscadorRAG(indice="seu_indice")

    print(b.estatisticas())
    print(b.testar_analise("Não há garantia para importados após 12 meses"))

    for r in b.hibrida("prazo de garantia para importados", k=5):
        print(f"{r.score:.4f}  {r.filename} p.{r.pages}")
        print(f"   {r.texto[:150]}")

    print(b.contexto_para_llm("qual o prazo de garantia?", k=3))
```

---

## 15. Análise crítica do seu schema

O schema está bem acima da média — `dynamic: strict`, quantização configurada, analisador em português. Os pontos abaixo são refinamentos, ordenados por impacto.

### 15.1 🔴 Ordem dos filtros no analisador (crítico)

```python
"filter": ["lowercase", "asciifolding", "pt_stop", "pt_stemmer"]
                         ^^^^^^^^^^^^^^  ^^^^^^^
                         desacentua       procura formas ACENTUADAS
```

A lista `_brazilian_` do Lucene contém as formas acentuadas: `não`, `há`, `é`, `às`, `após`, `também`, `só`. Quando o `asciifolding` roda antes, essas palavras chegam ao `pt_stop` já desacentuadas (`nao`, `ha`, `e`, `as`, `apos`) e **não são reconhecidas como stopwords**.

**Consequência:** o índice está cheio de tokens vazios. Isso incha o índice e degrada o BM25 — palavras sem valor discriminativo entram no cálculo de score.

**Confirme antes de mudar** (seção 2). Se a saída contiver `nao`, `ha`, `apos`, o problema está lá.

**Correção:**

```python
"analyzer": {"pt_analyzer": {
    "type": "custom",
    "tokenizer": "standard",
    "filter": ["lowercase", "pt_stop", "pt_stemmer", "asciifolding"],
}}
```

O `asciifolding` vai para o fim: as stopwords são removidas com acento e o que sobra é desacentuado depois, mantendo a tolerância a acento nas buscas.

> **Isso exige reindexação.** Mudança de analisador não afeta documentos já indexados. Veja a seção 15.8 para o procedimento sem downtime.

### 15.2 🔴 Sem campo para termo exato

Seu `text` só existe na forma com stemming agressivo. Isso significa que:

- `"XR-4471"` vira `["xr", "4471"]`
- `"garantia"` e `"garantido"` são o mesmo token
- Não há como fazer busca literal

Para uma base de documentos técnicos, isso derruba a precisão em códigos, siglas e nomes próprios.

**Correção — multi-campo:**

```python
"text": {
    "type": "text",
    "analyzer": "pt_analyzer",
    "fields": {
        "exact": {
            "type": "text",
            "analyzer": "pt_exact",     # lowercase + asciifolding, SEM stemming
        },
        "raw": {
            "type": "keyword",
            "ignore_above": 256,        # só para chunks curtos; útil para dedup
        },
    },
},
```

Com o analisador auxiliar:

```python
"pt_exact": {
    "type": "custom",
    "tokenizer": "standard",
    "filter": ["lowercase", "asciifolding"],
}
```

Aí a busca fica muito melhor:

```json
{
  "multi_match": {
    "query": "garantia XR-4471",
    "fields": ["text^1", "text.exact^3"],
    "type": "most_fields"
  }
}
```

O campo com stemming dá recall, o campo exato dá precisão. Quem casa nos dois sobe.

### 15.2b `headings` só como keyword

`metadata.headings` guarda títulos de seção — texto semanticamente rico que você não consegue buscar hoje.

```python
"headings": {
    "type": "keyword",
    "fields": {
        "text": {"type": "text", "analyzer": "pt_analyzer"}
    }
},
```

Você mantém `metadata.headings` para filtro e agregação (facetas por seção) e ganha `metadata.headings.text` para busca:

```json
{
  "multi_match": {
    "query": "política de garantia",
    "fields": ["text", "metadata.headings.text^2"]
  }
}
```

Títulos de seção são um sinal forte de relevância. Dar boost neles costuma melhorar bastante os resultados.

### 15.3 🟡 Keyword sem `normalizer`

```json
{"term": {"metadata.filename": "Manual_v3.PDF"}}   // não casa com "manual_v3.pdf"
```

**Correção:**

```python
# em settings.analysis
"normalizer": {
    "lowercase_norm": {
        "type": "custom",
        "filter": ["lowercase", "asciifolding"],
    }
}

# em mappings
"filename": {"type": "keyword", "normalizer": "lowercase_norm"},
```

Agora o filtro é case-insensitive e tolerante a acento, sem você precisar normalizar na aplicação.

### 15.4 🟡 Campos que faltam para RAG

Seu metadata não permite algumas operações básicas:

| Campo ausente | O que você não consegue fazer |
|---|---|
| `chunk_index` | Reconstruir a ordem; buscar chunk anterior/seguinte |
| `indexed_at` | Filtrar por recência; detectar versões velhas |
| `source_path` / `url` | Linkar a fonte original na interface |
| `char_start` / `char_end` | Localizar o trecho no documento original |
| `total_chunks` | Saber se o documento foi indexado por completo |
| `embedding_model` | Saber quais chunks precisam ser reindexados ao trocar de modelo |

Esse último é subestimado. No dia que você trocar de modelo de embedding, sem esse campo você não sabe o que está desatualizado e precisa reindexar tudo às cegas.

```python
"metadata": {
    "properties": {
        "filename":        {"type": "keyword", "normalizer": "lowercase_norm"},
        "headings":        {"type": "keyword",
                            "fields": {"text": {"type": "text",
                                                "analyzer": "pt_analyzer"}}},
        "doc_id":          {"type": "keyword"},
        "pages":           {"type": "integer"},
        "chunk_index":     {"type": "integer"},
        "total_chunks":    {"type": "integer"},
        "char_start":      {"type": "integer"},
        "char_end":        {"type": "integer"},
        "source_path":     {"type": "keyword", "index": False},
        "url":             {"type": "keyword", "index": False},
        "indexed_at":      {"type": "date"},
        "embedding_model": {"type": "keyword"},
        "lang":            {"type": "keyword"},
    }
},
```

> **Boa notícia:** adicionar campos novos ao mapping **não exige reindexação**. É um `PUT /_mapping` e pronto. Só os documentos novos terão os campos preenchidos, mas o índice continua funcionando.

```json
PUT /SEU_INDICE/_mapping
{
  "properties": {
    "metadata": {
      "properties": {
        "chunk_index":     {"type": "integer"},
        "indexed_at":      {"type": "date"},
        "embedding_model": {"type": "keyword"}
      }
    }
  }
}
```

### 15.5 🟡 `int8_hnsw` pode não ser a melhor escolha

Segundo a documentação atual, o **padrão do Elasticsearch para vetores `float` com 384 dimensões ou mais é `bbq_hnsw`**, não `int8_hnsw`.

| Quantização | Redução de memória | Perda de precisão |
|---|---|---|
| `int8_hnsw` (o seu) | 4× | Baixa |
| `int4_hnsw` | 8× | Média |
| `bbq_hnsw` | **32×** | Maior, mas recuperável com oversampling |

Se `DIMS >= 384` (provável — os modelos multilíngues comuns têm 384, 768 ou 1024), migrar para `bbq_hnsw` reduz o uso de memória em **8× a mais** do que você tem hoje, e a perda de precisão é mitigada com `rescore_vector`.

**E dá para migrar sem recriar o índice.** A documentação define este caminho de atualização:

```
flat → int8_flat → int4_flat → bbq_flat → hnsw → int8_hnsw → int4_hnsw → bbq_hnsw
```

Saltos para frente são permitidos. De `int8_hnsw` você pode ir direto para `bbq_hnsw`:

```json
PUT /SEU_INDICE/_mapping
{
  "properties": {
    "vector": {
      "type": "dense_vector",
      "dims": DIMS,
      "index": true,
      "similarity": "cosine",
      "index_options": {
        "type": "bbq_hnsw",
        "m": 16,
        "ef_construction": 200,
        "rescore_vector": {"oversample": 3.0}
      }
    }
  }
}
```

**Duas ressalvas importantes:**

1. Vetores **já indexados mantêm o tipo antigo**. Só os novos usam `bbq_hnsw`. Para converter tudo, faça `_forcemerge` ou reindexe.
2. Ao atualizar tipos HNSW, o `m` deve **permanecer igual ou aumentar**. Nunca diminuir.
3. `bbq` exige mais de 64 dimensões (o seu certamente atende).

**Antes de migrar, meça.** Use a função `medir_recall` da seção 6.6 antes e depois. Se o recall cair demais, suba o `oversample` ou volte para `int4_hnsw`.

Sobre `ef_construction: 200`: está acima do padrão (100). Isso deixa a indexação mais lenta em troca de um grafo melhor. Para um índice que é escrito uma vez e lido muito, é uma boa escolha — mantenha.

### 15.6 🟢 O `vector` no `_source`

Desde as versões recentes, o Elasticsearch **não inclui `dense_vector` no `_source` por padrão**. O comportamento é controlado por `index.mapping.exclude_source_vectors`, que vem habilitado para índices novos e só pode ser definido na criação.

**Confirme qual é o seu caso:**

```json
GET /SEU_INDICE/_settings?flat_settings=true&include_defaults=true&filter_path=**.exclude_source_vectors
```

E na prática:

```json
GET /SEU_INDICE/_search
{"size": 1}
```

Se o `vector` aparecer no resultado, você está pagando por isso em disco e em tráfego. Nesse caso:

- **Curto prazo:** sempre use `"_source": {"excludes": ["vector"]}` nas buscas. Todos os exemplos deste guia já fazem isso.
- **Longo prazo:** ao recriar o índice, deixe o padrão ativo (não defina `exclude_source_vectors: false`).

Para conferir o impacto real:

```json
POST /SEU_INDICE/_disk_usage?run_expensive_tasks=true
```

Em índices de RAG, o `_source` com vetores costuma ser a maior fatia do disco.

### 15.7 🟢 Settings de infraestrutura

```python
"index": {"number_of_shards": 1, "number_of_replicas": 0, "refresh_interval": "1s"}
```

| Setting | Situação | Recomendação |
|---|---|---|
| `number_of_shards: 1` | ✅ Correto para até ~50GB | Mantenha. Só divida se passar disso. |
| `number_of_replicas: 0` | ⚠️ Sem redundância | `1` em produção. Se o nó cair, você perde tudo. |
| `refresh_interval: "1s"` | ⚠️ Desnecessário | `"30s"` ou `"60s"` para índice de RAG |

O `refresh_interval` de 1s faz sentido para dados que chegam continuamente e precisam estar visíveis na hora. Um índice de documentos é escrito em lotes — 30s reduz a criação de segmentos e o custo de merge sem prejuízo nenhum.

Durante a carga inicial, o ideal é:

```json
PUT /SEU_INDICE/_settings
{"index": {"refresh_interval": "-1", "number_of_replicas": 0}}

// ... ingestão ...

PUT /SEU_INDICE/_settings
{"index": {"refresh_interval": "30s", "number_of_replicas": 1}}

POST /SEU_INDICE/_forcemerge?max_num_segments=1
```

### 15.8 🟢 Sem alias — e você vai precisar de um

Você tem pelo menos duas mudanças pela frente que exigem reindexação (analisador e possivelmente quantização). Sem alias, isso significa downtime.

```json
// 1. aponte o alias para o índice atual
POST /_aliases
{
  "actions": [
    {"add": {"index": "SEU_INDICE", "alias": "documentos"}}
  ]
}
```

A partir daí, **sua aplicação sempre consulta `documentos`**, nunca o nome real. Aí a migração vira:

```json
// 2. crie o índice novo com o mapping corrigido
PUT /documentos_v2
{ ...settings e mappings novos... }

// 3. reindexe (mais rápido se desligar o refresh antes)
POST /_reindex?wait_for_completion=false
{
  "source": {"index": "SEU_INDICE", "size": 1000},
  "dest":   {"index": "documentos_v2"}
}

// acompanhe
GET /_tasks/ID_DA_TASK

// 4. troca atômica — a aplicação não percebe nada
POST /_aliases
{
  "actions": [
    {"remove": {"index": "SEU_INDICE",   "alias": "documentos"}},
    {"add":    {"index": "documentos_v2", "alias": "documentos"}}
  ]
}

// 5. depois de validar, apague o antigo
DELETE /SEU_INDICE
```

> ⚠️ O `_reindex` copia os documentos, mas **não recalcula os embeddings**. Se você mudar o modelo de embedding, precisa reprocessar a partir dos textos originais, não do índice.
>
> Já a mudança do **analisador** funciona com `_reindex` normal — o texto é reanalisado ao ser gravado no índice novo.

### 15.9 Resumo priorizado

| # | Melhoria | Impacto | Exige reindex? |
|---|---|---|---|
| 1 | Corrigir ordem `asciifolding` / `pt_stop` | 🔴 Alto | Sim |
| 2 | Adicionar `text.exact` (sem stemming) | 🔴 Alto | Sim |
| 3 | Criar alias | 🔴 Alto (viabiliza o resto) | Não |
| 4 | `headings` como multi-campo | 🟡 Médio | Sim |
| 5 | Avaliar `bbq_hnsw` | 🟡 Médio (memória) | Não (mas ideal) |
| 6 | Adicionar `chunk_index`, `indexed_at`, `embedding_model` | 🟡 Médio | Não |
| 7 | `normalizer` nos keywords | 🟡 Médio | Sim |
| 8 | `number_of_replicas: 1` | 🟡 Médio | Não |
| 9 | `refresh_interval: "30s"` | 🟢 Baixo | Não |

**Sugestão de sequência:** faça o item 3 primeiro (alias, sem risco). Depois agrupe 1, 2, 4 e 7 em uma única reindexação — são todos mudanças de mapping. Os itens 5, 6, 8 e 9 podem ser aplicados no índice atual a qualquer momento.

---

## 16. Mapping melhorado, completo

Versão pronta para colar, com todas as correções e comentários explicando cada decisão:

```python
from typing import Any

DIMS = 1024  # ajuste para o seu modelo

SETTINGS: dict[str, Any] = {
    "index": {
        "number_of_shards": 1,
        "number_of_replicas": 1,        # ← era 0: sem réplica, um nó caído = dados perdidos
        "refresh_interval": "30s",      # ← era 1s: índice de RAG não precisa de 1s
    },
    "analysis": {
        "filter": {
            "pt_stop":    {"type": "stop", "stopwords": "_brazilian_"},
            "pt_stemmer": {"type": "stemmer", "language": "brazilian"},
        },
        "normalizer": {
            # ← NOVO: deixa filtros por keyword insensíveis a caixa e acento
            "lowercase_norm": {
                "type": "custom",
                "filter": ["lowercase", "asciifolding"],
            }
        },
        "analyzer": {
            # ← CORRIGIDO: asciifolding no FIM, depois do stop e do stemmer
            "pt_analyzer": {
                "type": "custom",
                "tokenizer": "standard",
                "filter": ["lowercase", "pt_stop", "pt_stemmer", "asciifolding"],
            },
            # ← NOVO: sem stemming, preserva termos exatos, códigos e siglas
            "pt_exact": {
                "type": "custom",
                "tokenizer": "standard",
                "filter": ["lowercase", "asciifolding"],
            },
        },
    },
}

MAPPINGS: dict[str, Any] = {
    "dynamic": "strict",
    "properties": {
        "text": {
            "type": "text",
            "analyzer": "pt_analyzer",
            "fields": {
                # busca precisa: códigos, siglas, nomes próprios
                "exact": {"type": "text", "analyzer": "pt_exact"},
            },
        },
        "vector": {
            "type": "dense_vector",
            "dims": DIMS,
            "index": True,
            "similarity": "cosine",
            "index_options": {
                # bbq_hnsw se DIMS >= 384; int8_hnsw abaixo disso
                "type": "bbq_hnsw",
                "m": 16,
                "ef_construction": 200,
                "rescore_vector": {"oversample": 3.0},
            },
        },
        "metadata": {
            "properties": {
                "filename": {
                    "type": "keyword",
                    "normalizer": "lowercase_norm",
                },
                "headings": {
                    "type": "keyword",
                    "normalizer": "lowercase_norm",
                    "fields": {
                        # permite buscar texto dentro dos títulos de seção
                        "text": {"type": "text", "analyzer": "pt_analyzer"},
                    },
                },
                "doc_id":       {"type": "keyword"},
                "pages":        {"type": "integer"},
                "chunk_index":  {"type": "integer"},   # ordem dentro do documento
                "total_chunks": {"type": "integer"},   # detecta ingestão incompleta
                "char_start":   {"type": "integer"},
                "char_end":     {"type": "integer"},
                "source_path":  {"type": "keyword", "index": False},  # só armazena
                "url":          {"type": "keyword", "index": False},
                "indexed_at":   {"type": "date"},
                "embedding_model": {"type": "keyword"},  # saber o que reindexar
                "lang":         {"type": "keyword"},
            }
        },
    },
}
```

### Criando com alias desde o começo

```python
INDICE_FISICO = "documentos_v2"
ALIAS = "documentos"

es.indices.create(index=INDICE_FISICO, settings=SETTINGS, mappings=MAPPINGS)
es.indices.put_alias(index=INDICE_FISICO, name=ALIAS)

# a partir daqui, a aplicação só usa ALIAS
```

### A busca que aproveita o mapping novo

```python
def buscar_completa(consulta: str, k: int = 10, filtro: dict | None = None):
    vetor = embed_consulta(consulta)

    lexica = {
        "bool": {
            "must": [{
                "multi_match": {
                    "query": consulta,
                    "fields": [
                        "text^1",                  # com stemming → recall
                        "text.exact^3",            # sem stemming → precisão
                        "metadata.headings.text^2" # título de seção → sinal forte
                    ],
                    "type": "most_fields",
                }
            }],
            "should": [
                {"match_phrase": {"text.exact": {"query": consulta, "boost": 4}}}
            ],
        }
    }
    knn = {"field": "vector", "query_vector": vetor,
           "k": 50, "num_candidates": 200,
           "rescore_vector": {"oversample": 2.0}}

    if filtro:
        lexica["bool"]["filter"] = [filtro]
        knn["filter"] = filtro

    return es.search(
        index=ALIAS,
        size=k,
        source={"excludes": ["vector"]},
        retriever={
            "rrf": {
                "retrievers": [
                    {"standard": {"query": lexica}},
                    {"knn": knn},
                ],
                "rank_window_size": 50,
            }
        },
        collapse={"field": "metadata.doc_id",
                  "inner_hits": {"name": "chunks", "size": 2,
                                 "_source": {"excludes": ["vector"]}}},
        highlight={"fields": {"text": {"fragment_size": 200,
                                       "number_of_fragments": 2}}},
    )
```

Essa única query faz: busca léxica com stemming, busca exata sem stemming, boost em títulos de seção, bônus para frase exata, busca vetorial com oversampling, fusão RRF, agrupamento por documento e destaque dos trechos.

---

## 17. Cheat sheet

### Queries léxicas em `text`

```json
{"match":              {"text": "consulta"}}
{"match":              {"text": {"query": "c", "operator": "and"}}}
{"match":              {"text": {"query": "c", "minimum_should_match": "70%"}}}
{"match_phrase":       {"text": "frase exata"}}
{"match_phrase":       {"text": {"query": "frase", "slop": 2}}}
{"match_phrase_prefix":{"text": {"query": "insta", "max_expansions": 20}}}
{"multi_match":        {"query": "c", "fields": ["text", "text.exact^3"]}}
{"simple_query_string":{"query": "+a -b", "fields": ["text"]}}
{"match_all":          {}}
```

### Filtros em `metadata`

```json
{"term":   {"metadata.filename": "manual.pdf"}}
{"terms":  {"metadata.filename": ["a.pdf", "b.pdf"]}}
{"term":   {"metadata.doc_id": "doc-123"}}
{"range":  {"metadata.pages": {"gte": 10, "lte": 50}}}
{"prefix": {"metadata.filename": "projeto_"}}
{"exists": {"field": "metadata.headings"}}
{"ids":    {"values": ["chunk-1", "chunk-2"]}}
```

### kNN em `vector`

```json
"knn": {
  "field": "vector",
  "query_vector": [...],
  "k": 10,
  "num_candidates": 200,
  "filter": {"term": {"metadata.doc_id": "x"}},
  "rescore_vector": {"oversample": 2.0}
}
```

### Híbrida

```json
"retriever": {
  "rrf": {
    "retrievers": [
      {"standard": {"query": {"match": {"text": "c"}}}},
      {"knn": {"field": "vector", "query_vector": [...],
               "k": 50, "num_candidates": 200}}
    ],
    "rank_window_size": 50,
    "rank_constant": 60
  }
}
```

### Comandos de inspeção (Kibana)

```json
GET _cat/indices?v
GET /IDX/_mapping
GET /IDX/_settings
GET /IDX/_count
GET /IDX/_stats
POST /IDX/_analyze          {"analyzer": "pt_analyzer", "text": "..."}
GET  /IDX/_explain/ID       {"query": {...}}
GET  /IDX/_validate/query?explain=true
POST /IDX/_disk_usage?run_expensive_tasks=true
GET  /_tasks?actions=*reindex&detailed
```

### Python — assinaturas

```python
es.search(index=..., query=..., knn=..., retriever=...,
          size=10, from_=0, source={"excludes": ["vector"]},
          highlight=..., aggs=..., collapse=..., sort=...)

es.indices.analyze(index=..., analyzer="pt_analyzer", text="...")
es.explain(index=..., id=..., query=...)
es.count(index=..., query=...)
es.indices.put_mapping(index=..., properties={...})
es.indices.put_settings(index=..., settings={...})
es.indices.update_aliases(actions=[...])
es.reindex(source={...}, dest={...}, wait_for_completion=False)

helpers.scan(es, index=..., query={...}, size=500)
```

### Valores de partida

| Parâmetro | Comece com | Suba se |
|---|---|---|
| `k` (kNN) | 10 | — |
| `num_candidates` | 200 | recall baixo, filtro restritivo |
| `rescore_vector.oversample` | 2.0 | quantização prejudicando resultados |
| `rank_window_size` (RRF) | 50 | híbrida pior que as pernas isoladas |
| `rank_constant` (RRF) | 60 | raramente precisa mexer |
| `minimum_should_match` | "70%" | consultas longas trazendo lixo |

---

## Links da documentação oficial

- Retrievers (visão geral): https://www.elastic.co/docs/solutions/search/retrievers-overview
- Referência de retrievers: https://www.elastic.co/docs/reference/elasticsearch/rest-apis/retrievers
- RRF retriever: https://www.elastic.co/docs/reference/elasticsearch/rest-apis/retrievers/rrf-retriever
- Reciprocal Rank Fusion: https://www.elastic.co/docs/reference/elasticsearch/rest-apis/reciprocal-rank-fusion
- `dense_vector`: https://www.elastic.co/docs/reference/elasticsearch/mapping-reference/dense-vector
- Better Binary Quantization: https://www.elastic.co/docs/reference/elasticsearch/mapping-reference/bbq
- Query DSL: https://www.elastic.co/docs/reference/query-languages/querydsl
- Componentes de análise de texto: https://www.elastic.co/docs/reference/text-analysis
- Collapse: https://www.elastic.co/docs/reference/elasticsearch/rest-apis/collapse-search-results
- Highlighting: https://www.elastic.co/docs/reference/elasticsearch/rest-apis/highlighting
