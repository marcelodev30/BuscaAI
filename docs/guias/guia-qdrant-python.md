# Guia Completo: Qdrant com Python

> Baseado no `qdrant-client` **1.18.0** (maio/2026). Requer Python 3.10+.
>
> ⚠️ **Aviso importante sobre versão:** na 1.16 os métodos `search()`, `recommend()`, `discover()`, `search_batch()`, `upload_records()` foram **removidos** (não só depreciados — removidos mesmo). Tudo hoje passa por `query_points()`. Se você achar tutorial usando `client.search(...)`, é código que **não roda mais**.

---

## 1. O que é Qdrant

Banco de dados vetorial escrito em Rust. A ideia central: em vez de buscar por palavras, você busca por **proximidade em um espaço vetorial**. Textos, imagens ou áudios viram vetores (embeddings), e "parecido" vira "perto".

### Modelo mental

| Conceito | O que é | Analogia |
|---|---|---|
| **Collection** | Conjunto de pontos com a mesma config de vetor | Tabela |
| **Point** | Unidade: `id` + `vector` + `payload` | Linha |
| **Vector** | Lista de floats (o embedding) | — |
| **Payload** | JSON com os metadados | Colunas |
| **HNSW** | Estrutura de índice para busca aproximada | Índice B-tree |
| **Distance** | Métrica de similaridade | — |

Um ponto na prática:

```python
{
    "id": 42,
    "vector": [0.12, -0.45, 0.88, ...],       # 384 dimensões, por exemplo
    "payload": {"titulo": "Como trocar a bateria", "categoria": "hardware", "ano": 2026}
}
```

### IDs: só inteiro ou UUID

Essa é a pegadinha nº 1 de quem começa. O Qdrant **não aceita string arbitrária** como ID.

```python
# ✅ válido
id=42
id="550e8400-e29b-41d4-a716-446655440000"
id=uuid.uuid4()          # aceito direto desde a 1.16

# ❌ inválido — dá erro
id="produto-abc-123"
```

Solução padrão: gere um UUID determinístico a partir da sua chave e guarde a chave original no payload.

```python
import uuid

def id_para_qdrant(chave: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, chave))

id_para_qdrant("produto-abc-123")  # sempre o mesmo UUID
```

### Métricas de distância

| Métrica | Quando usar |
|---|---|
| `COSINE` | Padrão para embeddings de texto. Ignora magnitude. |
| `DOT` | Quando os vetores já estão normalizados, ou em modelos de recomendação. |
| `EUCLID` | Distância L2. Comum em visão computacional. |
| `MANHATTAN` | L1. Casos específicos. |

Use a métrica que o **modelo de embedding recomenda**. Usar `EUCLID` com um modelo treinado para cosseno degrada a qualidade sem dar erro nenhum — falha silenciosa.

---

## 2. Qdrant ou Elasticsearch?

| | Qdrant | Elasticsearch |
|---|---|---|
| Foco | Busca vetorial | Busca textual (com vetorial adicionada depois) |
| Full-text/BM25 | Básico (índice de texto + BM25 esparso) | Excelente, com analyzers, stemming, etc. |
| Agregações analíticas | Limitadas (facets simples) | Muito ricas |
| Filtro + vetor | Excelente (filtro aplicado *durante* o HNSW) | Bom |
| Consumo de memória | Menor, com quantização agressiva | Maior |
| Complexidade operacional | Baixa | Alta |
| Modo local sem servidor | Sim (`:memory:` / arquivo) | Não |

**Na prática:** se o projeto é RAG, recomendação ou busca semântica, Qdrant. Se envolve log analytics, dashboards, agregações complexas e busca por texto rico, Elasticsearch. Muitos times usam os dois.

---

## 3. Subindo o Qdrant

### Docker

```bash
docker run -d --name qdrant \
  -p 6333:6333 -p 6334:6334 \
  -v $(pwd)/qdrant_storage:/qdrant/storage \
  qdrant/qdrant
```

- `6333` → API REST + painel web
- `6334` → gRPC (mais rápido)

Painel web: **http://localhost:6333/dashboard**

### docker-compose.yml

```yaml
services:
  qdrant:
    image: qdrant/qdrant:latest
    ports:
      - "6333:6333"
      - "6334:6334"
    volumes:
      - qdrant_data:/qdrant/storage
    environment:
      QDRANT__SERVICE__API_KEY: ${QDRANT_API_KEY:-chave-de-dev}
      QDRANT__LOG_LEVEL: INFO
    healthcheck:
      test: ["CMD-SHELL", "bash -c ':> /dev/tcp/127.0.0.1/6333' || exit 1"]
      interval: 10s
      retries: 5

volumes:
  qdrant_data:
```

### Sem servidor nenhum (modo local)

O grande diferencial do cliente Python: ele **roda o Qdrant embutido**.

```python
from qdrant_client import QdrantClient

client = QdrantClient(":memory:")              # tudo em RAM, some ao fechar
client = QdrantClient(path="./qdrant_local")   # persiste em disco
```

Mesma API do servidor. Ideal para testes, notebooks, CI e protótipos. Quando escalar, troca a linha de conexão e nada mais muda.

> Limitação: o modo local é single-process e não suporta tudo (algumas otimizações e quantização não se aplicam). Não use em produção.

---

## 4. Instalação

```bash
pip install qdrant-client

# com geração de embeddings local (ONNX, roda em CPU)
pip install "qdrant-client[fastembed]"

# versão GPU do fastembed
pip install "qdrant-client[fastembed-gpu]"
```

---

## 5. Conectando

```python
from qdrant_client import QdrantClient, models

# local, sem auth
client = QdrantClient(url="http://localhost:6333")

# com API key
client = QdrantClient(url="http://localhost:6333", api_key="minha-chave")

# Qdrant Cloud
client = QdrantClient(
    url="https://xyz-abc.us-east.aws.cloud.qdrant.io:6333",
    api_key="sua-api-key",
)

# gRPC — recomendado para carga pesada
client = QdrantClient(host="localhost", grpc_port=6334, prefer_grpc=True)

# timeout e headers
client = QdrantClient(
    url="http://localhost:6333",
    api_key="...",
    timeout=60,
    prefer_grpc=True,
    headers={"X-Origem": "meu-app"},
)
```

Verificando:

```python
print(client.info())            # versão do servidor
print(client.get_collections())
```

### Padrão de projeto: cliente único

```python
# qdrant_conn.py
import os
from functools import lru_cache
from qdrant_client import QdrantClient

@lru_cache(maxsize=1)
def get_client() -> QdrantClient:
    return QdrantClient(
        url=os.environ.get("QDRANT_URL", "http://localhost:6333"),
        api_key=os.environ.get("QDRANT_API_KEY"),
        timeout=60,
        prefer_grpc=True,
    )
```

---

## 6. Collections

### Criar

```python
from qdrant_client import models

COL = "documentos"

if not client.collection_exists(COL):
    client.create_collection(
        collection_name=COL,
        vectors_config=models.VectorParams(
            size=384,                          # dimensão do seu modelo
            distance=models.Distance.COSINE,
        ),
    )
```

`size` precisa bater **exatamente** com a dimensão do embedding. Alguns valores comuns:

| Modelo | Dimensão |
|---|---|
| `all-MiniLM-L6-v2` | 384 |
| `paraphrase-multilingual-MiniLM-L12-v2` | 384 |
| `BAAI/bge-m3` | 1024 |
| `text-embedding-3-small` (OpenAI) | 1536 |
| `text-embedding-3-large` (OpenAI) | 3072 |

### Vetores nomeados (múltiplos vetores por ponto)

```python
client.create_collection(
    collection_name="multimodal",
    vectors_config={
        "texto":  models.VectorParams(size=384, distance=models.Distance.COSINE),
        "imagem": models.VectorParams(size=512, distance=models.Distance.COSINE),
    },
)
```

Depois você escolhe qual usar na busca com `using="texto"`.

### Vetores esparsos (para BM25 / busca híbrida)

```python
client.create_collection(
    collection_name="hibrido",
    vectors_config={
        "denso": models.VectorParams(size=384, distance=models.Distance.COSINE),
    },
    sparse_vectors_config={
        "bm25": models.SparseVectorParams(modifier=models.Modifier.IDF),
    },
)
```

O `modifier=IDF` faz o Qdrant aplicar a ponderação IDF do BM25 no lado do servidor.

### Configuração completa (produção)

```python
client.create_collection(
    collection_name=COL,
    vectors_config=models.VectorParams(
        size=1024,
        distance=models.Distance.COSINE,
        on_disk=True,                     # vetores originais em disco, economiza RAM
    ),
    hnsw_config=models.HnswConfigDiff(
        m=16,                             # conexões por nó (↑ = melhor recall, mais RAM)
        ef_construct=100,                 # esforço na construção do índice
        on_disk=False,                    # índice HNSW na RAM = buscas rápidas
    ),
    optimizers_config=models.OptimizersConfigDiff(
        default_segment_number=2,
        indexing_threshold=20_000,        # só indexa segmentos acima disso
    ),
    quantization_config=models.ScalarQuantization(
        scalar=models.ScalarQuantizationConfig(
            type=models.ScalarType.INT8,
            quantile=0.99,
            always_ram=True,              # vetores quantizados sempre na RAM
        )
    ),
    shard_number=2,
    replication_factor=1,
    write_consistency_factor=1,
)
```

### Inspecionar e gerenciar

```python
info = client.get_collection(COL)
print(info.points_count, info.status, info.config.params.vectors)

client.get_collections()
client.collection_exists(COL)
client.delete_collection(COL)

# alterar config depois (sem recriar)
client.update_collection(
    collection_name=COL,
    optimizers_config=models.OptimizersConfigDiff(indexing_threshold=50_000),
)
```

### Adicionar/remover vetor nomeado depois de criada (1.18+)

```python
client.update_collection(
    collection_name=COL,
    vectors_config={"imagem": models.VectorParams(size=512, distance=models.Distance.COSINE)},
)
```

---

## 7. Pontos: inserir, ler, atualizar, apagar

### Upsert

```python
client.upsert(
    collection_name=COL,
    points=[
        models.PointStruct(
            id=1,
            vector=[0.05] * 384,
            payload={"titulo": "Trocar bateria", "categoria": "hardware", "ano": 2026},
        ),
        models.PointStruct(
            id=2,
            vector=[0.11] * 384,
            payload={"titulo": "Configurar Wi-Fi", "categoria": "rede", "ano": 2025},
        ),
    ],
    wait=True,   # espera confirmar antes de retornar
)
```

Com vetores nomeados:

```python
models.PointStruct(
    id=1,
    vector={"texto": [...], "imagem": [...]},
    payload={"titulo": "..."},
)
```

Com vetor esparso:

```python
models.PointStruct(
    id=1,
    vector={
        "denso": [0.1] * 384,
        "bm25": models.SparseVector(indices=[7, 42, 91], values=[0.8, 0.5, 0.3]),
    },
    payload={"titulo": "..."},
)
```

### Formato `Batch` (mais compacto)

```python
client.upsert(
    collection_name=COL,
    points=models.Batch(
        ids=[10, 11, 12],
        vectors=[[0.1]*384, [0.2]*384, [0.3]*384],
        payloads=[{"cat": "a"}, {"cat": "b"}, {"cat": "c"}],
    ),
)
```

### Ler por ID

```python
pontos = client.retrieve(
    collection_name=COL,
    ids=[1, 2],
    with_payload=True,
    with_vectors=False,
)

for p in pontos:
    print(p.id, p.payload)
```

### Contar

```python
client.count(collection_name=COL, exact=True).count

client.count(
    collection_name=COL,
    count_filter=models.Filter(
        must=[models.FieldCondition(key="categoria", match=models.MatchValue(value="hardware"))]
    ),
    exact=True,
).count
```

### Atualizar payload (sem reenviar o vetor)

```python
# mescla com o payload existente
client.set_payload(
    collection_name=COL,
    payload={"revisado": True, "revisor": "ana"},
    points=[1, 2, 3],
)

# substitui o payload inteiro
client.overwrite_payload(collection_name=COL, payload={"titulo": "Novo"}, points=[1])

# remove chaves específicas
client.delete_payload(collection_name=COL, keys=["revisor"], points=[1])

# limpa tudo
client.clear_payload(
    collection_name=COL,
    points_selector=models.PointIdsList(points=[1]),
)
```

Atualizar payload por filtro (em massa):

```python
client.set_payload(
    collection_name=COL,
    payload={"arquivado": True},
    points=models.Filter(
        must=[models.FieldCondition(key="ano", range=models.Range(lt=2020))]
    ),
)
```

### Atualizar só o vetor

```python
client.update_vectors(
    collection_name=COL,
    points=[models.PointVectors(id=1, vector=[0.99] * 384)],
)

client.delete_vectors(collection_name=COL, points=[1], vectors=["imagem"])
```

### Apagar

```python
# por ID
client.delete(
    collection_name=COL,
    points_selector=models.PointIdsList(points=[1, 2, 3]),
)

# por filtro
client.delete(
    collection_name=COL,
    points_selector=models.FilterSelector(
        filter=models.Filter(
            must=[models.FieldCondition(key="categoria", match=models.MatchValue(value="obsoleto"))]
        )
    ),
)
```

### Várias operações numa tacada

```python
client.batch_update_points(
    collection_name=COL,
    update_operations=[
        models.UpsertOperation(upsert=models.PointsList(points=[
            models.PointStruct(id=100, vector=[0.1]*384, payload={"x": 1})
        ])),
        models.SetPayloadOperation(set_payload=models.SetPayload(
            payload={"revisado": True}, points=[100]
        )),
        models.DeleteOperation(delete=models.PointIdsList(points=[99])),
    ],
)
```

---

## 8. Ingestão em massa

### `upload_points` — o jeito certo

```python
def gerar_pontos(documentos):
    for i, doc in enumerate(documentos):
        yield models.PointStruct(
            id=i,
            vector=doc["embedding"],
            payload={"titulo": doc["titulo"], "categoria": doc["categoria"]},
        )

client.upload_points(
    collection_name=COL,
    points=gerar_pontos(documentos),
    batch_size=256,
    parallel=4,          # processos paralelos
    max_retries=3,
    wait=True,
)
```

Aceita gerador — não carrega tudo na memória.

### `upload_collection` — direto de arrays NumPy

```python
import numpy as np

vetores = np.random.rand(100_000, 384).astype(np.float32)
payloads = [{"idx": i, "grupo": i % 10} for i in range(100_000)]

client.upload_collection(
    collection_name=COL,
    vectors=vetores,
    payload=payloads,
    ids=list(range(100_000)),
    batch_size=512,
    parallel=4,
)
```

### Ingestão eficiente de verdade

Para cargas grandes, desligue a indexação durante a inserção e ligue depois:

```python
# 1. desliga indexação HNSW
client.update_collection(
    collection_name=COL,
    optimizer_config=models.OptimizersConfigDiff(indexing_threshold=0),
)

# 2. sobe tudo
client.upload_points(collection_name=COL, points=gerar_pontos(docs),
                     batch_size=512, parallel=4)

# 3. religa — o Qdrant constrói o índice de uma vez, muito mais rápido
client.update_collection(
    collection_name=COL,
    optimizer_config=models.OptimizersConfigDiff(indexing_threshold=20_000),
)
```

### Pipeline realista: chunks → embeddings → Qdrant

```python
import uuid
from sentence_transformers import SentenceTransformer
from qdrant_client import models

modelo = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")

def chunk(texto, tamanho=500, overlap=50):
    for i in range(0, len(texto), tamanho - overlap):
        yield texto[i:i + tamanho]

def gerar_pontos(documentos, lote=64):
    buffer_txt, buffer_meta = [], []

    def esvaziar():
        vetores = modelo.encode(buffer_txt, batch_size=32, normalize_embeddings=True)
        for vec, meta in zip(vetores, buffer_meta):
            yield models.PointStruct(
                id=str(uuid.uuid4()),
                vector=vec.tolist(),
                payload=meta,
            )
        buffer_txt.clear()
        buffer_meta.clear()

    for doc in documentos:
        for j, pedaco in enumerate(chunk(doc["texto"])):
            buffer_txt.append(pedaco)
            buffer_meta.append({
                "doc_id": doc["id"],
                "chunk_idx": j,
                "texto": pedaco,
                "fonte": doc["fonte"],
            })
            if len(buffer_txt) >= lote:
                yield from esvaziar()

    if buffer_txt:
        yield from esvaziar()

client.upload_points(collection_name=COL, points=gerar_pontos(documentos),
                     batch_size=256, parallel=2)
```

> **Sempre guarde o texto original no payload.** Sem isso, você recupera IDs e não tem o que mandar pro LLM.

---

## 9. Busca com `query_points`

Método único para tudo: vizinho mais próximo, recomendação, discovery, fusão híbrida.

### Busca básica

```python
resultado = client.query_points(
    collection_name=COL,
    query=[0.05] * 384,        # vetor da consulta
    limit=10,
    with_payload=True,
    with_vectors=False,
)

for p in resultado.points:
    print(f"{p.score:.4f}  {p.id}  {p.payload['titulo']}")
```

### Com corte de score

```python
client.query_points(
    collection_name=COL,
    query=vetor,
    limit=10,
    score_threshold=0.7,   # descarta resultados fracos
)
```

> Cuidado: o valor útil de `score_threshold` depende da métrica e do modelo. Para cosseno normalizado, 0.7 costuma ser razoável; para `DOT` sem normalizar, esse número não significa nada. Calibre com dados reais.

### Escolhendo o vetor nomeado

```python
client.query_points(collection_name="multimodal", query=vec_texto, using="texto", limit=5)
```

### Buscar "parecido com este ponto" (só passar o ID)

```python
client.query_points(collection_name=COL, query=42, limit=10)
```

O Qdrant busca o vetor do ponto 42 internamente. Não precisa de `retrieve` antes.

### Controlando o que volta

```python
client.query_points(
    collection_name=COL,
    query=vetor,
    limit=5,
    with_payload=["titulo", "fonte"],           # só esses campos
    with_payload=models.PayloadSelectorExclude(exclude=["embedding_bruto"]),
    with_vectors=True,
)
```

### Vários queries de uma vez

```python
resultados = client.query_batch_points(
    collection_name=COL,
    requests=[
        models.QueryRequest(query=vec1, limit=5, with_payload=True),
        models.QueryRequest(query=vec2, limit=5, with_payload=True),
    ],
)
```

### Parâmetros de busca (recall vs velocidade)

```python
client.query_points(
    collection_name=COL,
    query=vetor,
    limit=10,
    search_params=models.SearchParams(
        hnsw_ef=256,      # ↑ = mais preciso, mais lento (padrão ~128)
        exact=False,      # True = busca exaustiva, ignora HNSW (só para avaliar recall)
        quantization=models.QuantizationSearchParams(
            ignore=False,
            rescore=True,        # reavalia com vetores originais
            oversampling=2.0,    # busca 2x candidatos antes do rescore
        ),
    ),
)
```

---

## 10. Filtros — a parte mais forte do Qdrant

O Qdrant aplica o filtro **durante** a travessia do HNSW (com o algoritmo ACORN), não depois. Isso significa que filtrar não quebra o recall como acontece em vários outros bancos vetoriais.

### Estrutura

```python
from qdrant_client import models

filtro = models.Filter(
    must=[...],       # E lógico
    should=[...],     # OU lógico
    must_not=[...],   # NÃO
)

client.query_points(collection_name=COL, query=vetor, query_filter=filtro, limit=10)
```

### Condições por valor

```python
# igual a
models.FieldCondition(key="categoria", match=models.MatchValue(value="hardware"))

# um entre vários (IN)
models.FieldCondition(key="categoria", match=models.MatchAny(any=["hardware", "rede"]))

# nenhum entre vários (NOT IN)
models.FieldCondition(key="categoria", match=models.MatchExcept(**{"except": ["obsoleto"]}))

# contém a frase (precisa de índice de texto no campo)
models.FieldCondition(key="titulo", match=models.MatchText(text="bateria"))

# contém qualquer uma das palavras (1.16+)
models.FieldCondition(key="titulo", match=models.MatchTextAny(text="bateria carregador"))

# booleano
models.FieldCondition(key="publicado", match=models.MatchValue(value=True))
```

### Faixas

```python
models.FieldCondition(key="ano", range=models.Range(gte=2020, lte=2026))
models.FieldCondition(key="preco", range=models.Range(gt=100, lt=500))

from datetime import datetime, timezone
models.FieldCondition(
    key="criado_em",
    range=models.DatetimeRange(
        gte=datetime(2026, 1, 1, tzinfo=timezone.utc),
        lte=datetime(2026, 8, 31, tzinfo=timezone.utc),
    ),
)
```

### Geo

```python
models.FieldCondition(
    key="local",
    geo_radius=models.GeoRadius(
        center=models.GeoPoint(lat=-7.1934, lon=-36.0128),   # Cubati, PB
        radius=50_000,   # metros
    ),
)

models.FieldCondition(
    key="local",
    geo_bounding_box=models.GeoBoundingBox(
        top_left=models.GeoPoint(lat=-6.0, lon=-37.0),
        bottom_right=models.GeoPoint(lat=-8.0, lon=-35.0),
    ),
)
```

### Presença, nulo, ID, contagem

```python
models.IsEmptyCondition(is_empty=models.PayloadField(key="resumo"))
models.IsNullCondition(is_null=models.PayloadField(key="resumo"))
models.HasIdCondition(has_id=[1, 2, 3])

# array com N ou mais elementos
models.FieldCondition(key="tags", values_count=models.ValuesCount(gte=2))
```

### Objetos aninhados

Sem `Nested`, o Qdrant "achata" os arrays e mistura os valores de objetos diferentes:

```python
# payload: {"itens": [{"nome": "A", "qtd": 1}, {"nome": "B", "qtd": 9}]}

# ❌ isso casa, porque acha "A" em um item e qtd>5 em OUTRO
models.Filter(must=[
    models.FieldCondition(key="itens[].nome", match=models.MatchValue(value="A")),
    models.FieldCondition(key="itens[].qtd", range=models.Range(gt=5)),
])

# ✅ isso exige que seja o MESMO item
models.NestedCondition(nested=models.Nested(
    key="itens",
    filter=models.Filter(must=[
        models.FieldCondition(key="nome", match=models.MatchValue(value="A")),
        models.FieldCondition(key="qtd", range=models.Range(gt=5)),
    ]),
))
```

### `min_should` — pelo menos N das condições

```python
models.Filter(
    min_should=models.MinShould(
        conditions=[
            models.FieldCondition(key="tags", match=models.MatchValue(value="python")),
            models.FieldCondition(key="tags", match=models.MatchValue(value="rag")),
            models.FieldCondition(key="tags", match=models.MatchValue(value="vetorial")),
        ],
        min_count=2,
    )
)
```

### Filtro composto realista

```python
filtro = models.Filter(
    must=[
        models.FieldCondition(key="idioma", match=models.MatchValue(value="pt")),
        models.FieldCondition(key="ano", range=models.Range(gte=2024)),
    ],
    should=[
        models.FieldCondition(key="tags", match=models.MatchValue(value="destaque")),
    ],
    must_not=[
        models.FieldCondition(key="status", match=models.MatchAny(any=["rascunho", "removido"])),
        models.IsEmptyCondition(is_empty=models.PayloadField(key="texto")),
    ],
)

client.query_points(collection_name=COL, query=vetor, query_filter=filtro, limit=10)
```

---

## 11. Índices de payload — obrigatório para filtrar bem

Sem índice, o filtro faz varredura completa. Com índice, é instantâneo. **Sempre indexe os campos que você filtra.**

```python
client.create_payload_index(
    collection_name=COL,
    field_name="categoria",
    field_schema=models.PayloadSchemaType.KEYWORD,
)

client.create_payload_index(COL, "ano", field_schema=models.PayloadSchemaType.INTEGER)
client.create_payload_index(COL, "preco", field_schema=models.PayloadSchemaType.FLOAT)
client.create_payload_index(COL, "publicado", field_schema=models.PayloadSchemaType.BOOL)
client.create_payload_index(COL, "local", field_schema=models.PayloadSchemaType.GEO)
client.create_payload_index(COL, "criado_em", field_schema=models.PayloadSchemaType.DATETIME)
client.create_payload_index(COL, "uuid_externo", field_schema=models.PayloadSchemaType.UUID)
```

### Índice de texto (para `MatchText`)

```python
client.create_payload_index(
    collection_name=COL,
    field_name="titulo",
    field_schema=models.TextIndexParams(
        type=models.TextIndexType.TEXT,
        tokenizer=models.TokenizerType.MULTILINGUAL,   # bom para português
        min_token_len=2,
        max_token_len=20,
        lowercase=True,
    ),
)
```

Tokenizers: `WORD`, `WHITESPACE`, `PREFIX` (autocomplete), `MULTILINGUAL`.

### Índice de tenant (multi-tenancy)

```python
client.create_payload_index(
    collection_name=COL,
    field_name="tenant_id",
    field_schema=models.KeywordIndexParams(
        type=models.KeywordIndexType.KEYWORD,
        is_tenant=True,     # agrupa os dados por tenant no disco
    ),
)
```

Isso faz o Qdrant organizar fisicamente os pontos por tenant. Buscas filtradas por `tenant_id` ficam muito mais rápidas. **É o padrão recomendado para SaaS** — muito melhor que criar uma collection por cliente.

### Ver e remover

```python
print(client.get_collection(COL).payload_schema)
client.delete_payload_index(collection_name=COL, field_name="categoria")
```

---

## 12. Busca híbrida (denso + esparso)

O ponto fraco da busca puramente vetorial: ela erra em termos exatos (códigos de produto, nomes próprios, siglas). A híbrida resolve juntando BM25 com embeddings.

### Setup

```python
client.create_collection(
    collection_name="hibrido",
    vectors_config={"denso": models.VectorParams(size=384, distance=models.Distance.COSINE)},
    sparse_vectors_config={"bm25": models.SparseVectorParams(modifier=models.Modifier.IDF)},
)
```

### Inserindo (BM25 nativo, sem fastembed — 1.16+)

```python
client.upsert(
    collection_name="hibrido",
    points=[
        models.PointStruct(
            id=1,
            vector={
                "denso": models.Document(text=texto, model="sentence-transformers/all-MiniLM-L6-v2"),
                "bm25":  models.Document(text=texto, model="Qdrant/bm25"),
            },
            payload={"texto": texto},
        )
    ],
)
```

O `models.Document` faz o cliente gerar o embedding automaticamente (ou o servidor, se você usa Qdrant Cloud com inference).

### Buscando com fusão RRF

```python
consulta = "como trocar a bateria do notebook"

resultado = client.query_points(
    collection_name="hibrido",
    prefetch=[
        models.Prefetch(
            query=models.Document(text=consulta, model="sentence-transformers/all-MiniLM-L6-v2"),
            using="denso",
            limit=50,
        ),
        models.Prefetch(
            query=models.Document(text=consulta, model="Qdrant/bm25"),
            using="bm25",
            limit=50,
        ),
    ],
    query=models.FusionQuery(fusion=models.Fusion.RRF),
    limit=10,
    with_payload=True,
)
```

**RRF (Reciprocal Rank Fusion)** combina pelas posições, não pelos scores — funciona bem sem calibração. **DBSF** (`models.Fusion.DBSF`) normaliza os scores antes de somar; às vezes é melhor, mas é mais sensível.

### RRF com pesos (1.17+)

```python
query=models.FusionQuery(
    fusion=models.Fusion.RRF,
    params=models.RrfParams(k=60, weights=[0.7, 0.3]),   # denso pesa mais
)
```

### Multi-estágio: busca ampla + rerank com ColBERT

Padrão de alta qualidade para RAG: recupera muito com vetor barato, reordena o topo com um modelo caro.

```python
client.create_collection(
    collection_name="rerank",
    vectors_config={
        "denso": models.VectorParams(size=384, distance=models.Distance.COSINE),
        "colbert": models.VectorParams(
            size=128,
            distance=models.Distance.COSINE,
            multivector_config=models.MultiVectorConfig(
                comparator=models.MultiVectorComparator.MAX_SIM
            ),
            hnsw_config=models.HnswConfigDiff(m=0),   # sem índice: só usado no rerank
        ),
    },
)

resultado = client.query_points(
    collection_name="rerank",
    prefetch=models.Prefetch(query=vetor_denso, using="denso", limit=200),
    query=vetores_colbert,     # lista de vetores (multivector)
    using="colbert",
    limit=10,
)
```

`m=0` no HNSW desliga a indexação daquele vetor — ele fica só para reordenar os candidatos, o que economiza bastante memória.

### Prefetch aninhado

```python
client.query_points(
    collection_name="rerank",
    prefetch=models.Prefetch(
        prefetch=models.Prefetch(query=vec_barato, using="denso", limit=1000),
        query=vec_medio, using="medio", limit=100,
    ),
    query=vec_colbert, using="colbert", limit=10,
)
```

---

## 13. Recomendação, discovery e contexto

### Recomendação (positivos e negativos)

```python
resultado = client.query_points(
    collection_name=COL,
    query=models.RecommendQuery(
        recommend=models.RecommendInput(
            positive=[1, 5, 9],                                # IDs ou vetores
            negative=[42],
            strategy=models.RecommendStrategy.AVERAGE_VECTOR,  # ou BEST_SCORE
        )
    ),
    limit=10,
    query_filter=models.Filter(
        must_not=[models.HasIdCondition(has_id=[1, 5, 9])]     # não devolva os próprios
    ),
)
```

- `AVERAGE_VECTOR`: média dos positivos menos os negativos. Bom para "mais do mesmo".
- `BEST_SCORE`: pontua por proximidade ao *melhor* positivo. Bom quando os gostos são variados.

### Discovery — navegar com âncoras

```python
client.query_points(
    collection_name=COL,
    query=models.DiscoverQuery(
        discover=models.DiscoverInput(
            target=vetor_alvo,
            context=[
                models.ContextPair(positive=10, negative=20),
                models.ContextPair(positive=11, negative=21),
            ],
        )
    ),
    limit=10,
)
```

Cada par define uma "direção" no espaço. Útil para busca guiada por feedback ("mais assim, menos assado").

### Context — só exploração, sem alvo

```python
client.query_points(
    collection_name=COL,
    query=models.ContextQuery(
        context=[models.ContextPair(positive=10, negative=20)]
    ),
    limit=20,
)
```

Retorna a região do espaço definida pelos pares, sem ordenar por proximidade a um ponto específico.

---

## 14. MMR — diversidade nos resultados

Problema clássico de RAG: as 5 primeiras respostas são o mesmo parágrafo escrito de cinco jeitos. MMR resolve.

```python
resultado = client.query_points(
    collection_name=COL,
    query=models.NearestQuery(
        nearest=vetor_consulta,
        mmr=models.Mmr(
            diversity=0.5,          # 0.0 = só relevância | 1.0 = só diversidade
            candidates_limit=100,   # pré-seleciona 100, devolve os `limit` mais variados
        ),
    ),
    limit=5,
    with_payload=True,
)
```

Comece com `diversity=0.3` e suba se os resultados estiverem repetitivos.

---

## 15. Agrupamento

Evita que um documento longo domine os resultados com vários chunks.

```python
resultado = client.query_points_groups(
    collection_name=COL,
    query=vetor,
    group_by="doc_id",      # campo do payload
    limit=5,                # nº de grupos (documentos)
    group_size=3,           # chunks por documento
    with_payload=True,
)

for grupo in resultado.groups:
    print("Documento:", grupo.id)
    for p in grupo.hits:
        print("   ", p.score, p.payload["texto"][:60])
```

---

## 16. Scroll — varrer a collection

Não é busca, é paginação. Para exportar, migrar ou processar tudo.

```python
proximo = None
while True:
    pontos, proximo = client.scroll(
        collection_name=COL,
        scroll_filter=models.Filter(
            must=[models.FieldCondition(key="categoria", match=models.MatchValue(value="hardware"))]
        ),
        limit=500,
        offset=proximo,
        with_payload=True,
        with_vectors=False,
    )

    for p in pontos:
        print(p.id, p.payload["titulo"])

    if proximo is None:
        break
```

Com ordenação por campo indexado:

```python
client.scroll(
    collection_name=COL,
    limit=100,
    order_by=models.OrderBy(key="criado_em", direction=models.Direction.DESC),
)
```

---

## 17. Quantização e economia de memória

O maior custo do Qdrant em produção é RAM. Quantização é a alavanca principal.

| Tipo | Compressão | Perda de precisão | Quando usar |
|---|---|---|---|
| **Scalar (int8)** | 4x | Baixa (~1%) | Padrão. Quase sempre vale a pena. |
| **Binary** | 32x | Alta sem rescore | Vetores grandes (1536+), com rescore ativado |
| **Product** | até 64x | Média-alta, e indexa devagar | Quando RAM é o gargalo absoluto |

### Scalar

```python
quantization_config=models.ScalarQuantization(
    scalar=models.ScalarQuantizationConfig(
        type=models.ScalarType.INT8,
        quantile=0.99,      # ignora 1% de outliers ao calcular a escala
        always_ram=True,
    )
)
```

### Binary (para OpenAI, Cohere, bge-m3)

```python
quantization_config=models.BinaryQuantization(
    binary=models.BinaryQuantizationConfig(always_ram=True)
)
```

Sempre combine binary com rescore na busca:

```python
search_params=models.SearchParams(
    quantization=models.QuantizationSearchParams(rescore=True, oversampling=3.0)
)
```

Sem rescore, binary quantization com 1536 dimensões degrada bastante o recall.

### Estratégia de memória recomendada

```python
client.create_collection(
    collection_name=COL,
    vectors_config=models.VectorParams(
        size=1536,
        distance=models.Distance.COSINE,
        on_disk=True,               # originais no disco
    ),
    hnsw_config=models.HnswConfigDiff(on_disk=False),   # grafo na RAM
    quantization_config=models.BinaryQuantization(
        binary=models.BinaryQuantizationConfig(always_ram=True)  # quantizados na RAM
    ),
)
```

Lógica: o grafo HNSW e os vetores comprimidos ficam na RAM (rápido); os vetores originais ficam no disco e só são lidos no rescore final.

### Payload em disco

```python
client.create_collection(
    collection_name=COL,
    vectors_config=...,
    on_disk_payload=True,   # payloads grandes não ocupam RAM
)
```

---

## 18. FastEmbed — embeddings sem escrever código de modelo

```bash
pip install "qdrant-client[fastembed]"
```

Com `models.Document`, o cliente gera o embedding sozinho:

```python
from qdrant_client import QdrantClient, models

client = QdrantClient(":memory:")

client.create_collection(
    collection_name="faq",
    vectors_config=models.VectorParams(size=384, distance=models.Distance.COSINE),
)

MODELO = "sentence-transformers/all-MiniLM-L6-v2"

client.upsert(
    collection_name="faq",
    points=[
        models.PointStruct(
            id=i,
            vector=models.Document(text=t, model=MODELO),
            payload={"texto": t},
        )
        for i, t in enumerate([
            "Como redefinir minha senha",
            "Onde vejo minha fatura",
            "Como cancelar a assinatura",
        ])
    ],
)

r = client.query_points(
    collection_name="faq",
    query=models.Document(text="esqueci a senha", model=MODELO),
    limit=3,
)

for p in r.points:
    print(f"{p.score:.3f}  {p.payload['texto']}")
```

Listando modelos disponíveis:

```python
client.list_text_models()      # densos
client.list_sparse_models()    # esparsos (BM25, SPLADE)
client.list_image_models()
client.list_late_interaction_text_models()   # ColBERT
```

> `client.add()` e `client.query()` (a API antiga do fastembed) foram **depreciados na 1.16**. Use `upsert` + `query_points` com `models.Document`.

---

## 19. Cliente assíncrono

```python
import asyncio
from qdrant_client import AsyncQdrantClient, models

async def main():
    client = AsyncQdrantClient(url="http://localhost:6333")
    try:
        await client.upsert(
            collection_name=COL,
            points=[models.PointStruct(id=1, vector=[0.1]*384, payload={"x": 1})],
        )

        r = await client.query_points(collection_name=COL, query=[0.1]*384, limit=5)
        for p in r.points:
            print(p.id, p.score)

        # buscas em paralelo
        resultados = await asyncio.gather(
            client.query_points(collection_name=COL, query=v1, limit=5),
            client.query_points(collection_name=COL, query=v2, limit=5),
            client.query_points(collection_name=COL, query=v3, limit=5),
        )
    finally:
        await client.close()

asyncio.run(main())
```

Todos os métodos existem em versão async com o mesmo nome.

---

## 20. Snapshots, aliases e operação

### Snapshots

```python
snap = client.create_snapshot(collection_name=COL)
print(snap.name)

client.list_snapshots(collection_name=COL)

client.recover_snapshot(
    collection_name=COL,
    location=f"file:///qdrant/snapshots/{COL}/{snap.name}",
)

client.delete_snapshot(collection_name=COL, snapshot_name=snap.name)

# snapshot do cluster inteiro
client.create_full_snapshot()
```

### Aliases — migração sem downtime

```python
# aponta o alias para a versão atual
client.update_collection_aliases(change_aliases_operations=[
    models.CreateAliasOperation(
        create_alias=models.CreateAlias(collection_name="docs_v1", alias_name="docs")
    )
])

# ... cria docs_v2 com novo modelo de embedding, reindexa tudo ...

# troca atômica
client.update_collection_aliases(change_aliases_operations=[
    models.DeleteAliasOperation(delete_alias=models.DeleteAlias(alias_name="docs")),
    models.CreateAliasOperation(
        create_alias=models.CreateAlias(collection_name="docs_v2", alias_name="docs")
    ),
])

client.delete_collection("docs_v1")
```

**Sua aplicação sempre consulta `docs`, nunca `docs_v1`.** Trocar de modelo de embedding exige recriar tudo — com alias, isso vira uma operação de milissegundos.

---

## 21. Tratamento de erros

```python
from qdrant_client.http.exceptions import UnexpectedResponse, ResponseHandlingException
from grpc import RpcError

try:
    r = client.query_points(collection_name=COL, query=vetor, limit=10)
except UnexpectedResponse as e:
    print(f"Erro HTTP {e.status_code}: {e.content}")
except ResponseHandlingException as e:
    print("Falha de conexão/timeout:", e)
except ValueError as e:
    print("Parâmetros inválidos:", e)
```

Erros mais comuns e o que significam:

| Mensagem | Causa |
|---|---|
| `Vector dimension error: expected dim: 384, got 768` | Modelo de embedding diferente do `size` da collection |
| `Not found: Collection ... doesn't exist` | Faltou criar, ou nome errado |
| `Format error in JSON body: value is not a valid point ID` | ID que não é inteiro nem UUID |
| `Wrong input: Not existing vector name` | `using=` com nome que não existe |
| `Index required but not found` | Filtrando `MatchText` em campo sem índice de texto |

### Retry com backoff

```python
import time
from qdrant_client.http.exceptions import ResponseHandlingException

def com_retry(fn, tentativas=5, base=0.5):
    for i in range(tentativas):
        try:
            return fn()
        except ResponseHandlingException:
            if i == tentativas - 1:
                raise
            time.sleep(base * (2 ** i))

r = com_retry(lambda: client.query_points(collection_name=COL, query=vetor, limit=10))
```

### Health check

```python
def qdrant_ok(client) -> bool:
    try:
        client.get_collections()
        return True
    except Exception:
        return False
```

---

## 22. Integrações

### FastAPI + RAG

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Query
from qdrant_client import AsyncQdrantClient, models
from sentence_transformers import SentenceTransformer

client: AsyncQdrantClient | None = None
modelo = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")

@asynccontextmanager
async def lifespan(app: FastAPI):
    global client
    client = AsyncQdrantClient(url="http://localhost:6333")
    yield
    await client.close()

app = FastAPI(lifespan=lifespan)

@app.get("/buscar")
async def buscar(
    q: str,
    categoria: str | None = None,
    ano_min: int | None = None,
    limite: int = Query(10, le=50),
):
    condicoes = []
    if categoria:
        condicoes.append(
            models.FieldCondition(key="categoria", match=models.MatchValue(value=categoria))
        )
    if ano_min:
        condicoes.append(
            models.FieldCondition(key="ano", range=models.Range(gte=ano_min))
        )

    vetor = modelo.encode(q, normalize_embeddings=True).tolist()

    r = await client.query_points(
        collection_name="documentos",
        query=vetor,
        query_filter=models.Filter(must=condicoes) if condicoes else None,
        limit=limite,
        with_payload=True,
    )

    return {
        "resultados": [
            {"id": str(p.id), "score": p.score, **p.payload} for p in r.points
        ]
    }
```

Recuperação para alimentar um LLM:

```python
async def recuperar_contexto(pergunta: str, k: int = 5) -> str:
    vetor = modelo.encode(pergunta, normalize_embeddings=True).tolist()

    r = await client.query_points(
        collection_name="documentos",
        query=models.NearestQuery(
            nearest=vetor,
            mmr=models.Mmr(diversity=0.3, candidates_limit=50),
        ),
        limit=k,
        score_threshold=0.5,
        with_payload=["texto", "fonte"],
    )

    return "\n\n---\n\n".join(
        f"[Fonte: {p.payload['fonte']}]\n{p.payload['texto']}" for p in r.points
    )
```

### LangChain

```bash
pip install langchain-qdrant
```

```python
from langchain_qdrant import QdrantVectorStore, RetrievalMode
from langchain_huggingface import HuggingFaceEmbeddings

emb = HuggingFaceEmbeddings(model_name="paraphrase-multilingual-MiniLM-L12-v2")

vs = QdrantVectorStore.from_existing_collection(
    embedding=emb,
    collection_name="documentos",
    url="http://localhost:6333",
    retrieval_mode=RetrievalMode.DENSE,   # ou HYBRID
)

retriever = vs.as_retriever(search_type="mmr", search_kwargs={"k": 5, "lambda_mult": 0.7})
docs = retriever.invoke("como trocar a bateria")
```

### LlamaIndex

```bash
pip install llama-index-vector-stores-qdrant
```

```python
from llama_index.core import VectorStoreIndex, StorageContext
from llama_index.vector_stores.qdrant import QdrantVectorStore
from qdrant_client import QdrantClient

client = QdrantClient(url="http://localhost:6333")
vs = QdrantVectorStore(client=client, collection_name="documentos")
index = VectorStoreIndex.from_vector_store(vs)

resposta = index.as_query_engine(similarity_top_k=5).query("como trocar a bateria?")
```

---

## 23. Boas práticas e armadilhas

### Modelagem

- **Sempre guarde o texto original no payload.** Recuperar só IDs é inútil em RAG.
- Use **alias** desde o dia 1. Trocar de modelo de embedding exige reindexar tudo.
- Guarde a **versão do modelo** no payload. Ajuda muito quando vier a migração.
- Uma collection por caso de uso, **não** uma por cliente. Para multi-tenancy, use payload index com `is_tenant=True`.

### Performance

- **Indexe todo campo que você filtra.** É a otimização de maior impacto.
- Chunks de 300–800 tokens com 10–20% de overlap costumam ser o ponto ótimo em RAG.
- `prefer_grpc=True` para ingestão pesada — a diferença é real.
- Suba `hnsw_ef` se o recall estiver ruim; suba `m` se puder gastar mais RAM.
- Desligue `indexing_threshold` durante carga inicial e religue depois.
- Normalize os vetores quando usar `COSINE` — economiza cálculo.

### Memória

- Quantização scalar int8 é quase sempre lucro líquido: 4x menos RAM, perda desprezível.
- `on_disk=True` nos vetores + `always_ram=True` nos quantizados é o combo padrão.
- `on_disk_payload=True` se os payloads forem grandes (textos longos).

### Armadilhas mais comuns

| Sintoma | Causa |
|---|---|
| `expected dim: X, got Y` | Modelo diferente do configurado na collection |
| Erro de ID inválido | ID string que não é UUID |
| Filtro lento | Falta índice de payload no campo |
| `MatchText` não retorna nada | Falta índice de texto no campo |
| Resultados repetitivos em RAG | Use MMR ou agrupamento por `doc_id` |
| Score alto mas resultado irrelevante | Métrica errada, ou o embedding não cobre o domínio |
| Busca não acha termos exatos (SKU, sigla) | Vetorial sozinha falha nisso — use híbrida com BM25 |
| Recall cai depois de quantizar | Ative `rescore=True` e aumente `oversampling` |
| `client.search()` não existe | Removido na 1.16 — use `query_points()` |

---

## 24. Cheat sheet

```python
from qdrant_client import QdrantClient, AsyncQdrantClient, models

# CONEXÃO
QdrantClient(":memory:")
QdrantClient(path="./dados")
QdrantClient(url="http://localhost:6333", api_key="...")
QdrantClient(host="localhost", grpc_port=6334, prefer_grpc=True)

# COLLECTION
client.create_collection(COL, vectors_config=models.VectorParams(size=384, distance=models.Distance.COSINE))
client.collection_exists(COL)
client.get_collection(COL)
client.get_collections()
client.update_collection(COL, optimizers_config=...)
client.delete_collection(COL)

# ÍNDICE DE PAYLOAD
client.create_payload_index(COL, "campo", field_schema=models.PayloadSchemaType.KEYWORD)
client.delete_payload_index(COL, "campo")

# PONTOS
client.upsert(COL, points=[models.PointStruct(id=1, vector=[...], payload={})])
client.upload_points(COL, points=gerador, batch_size=256, parallel=4)
client.upload_collection(COL, vectors=array, payload=lista, ids=ids)
client.retrieve(COL, ids=[1, 2], with_payload=True)
client.count(COL, exact=True)
client.set_payload(COL, payload={}, points=[1])
client.overwrite_payload(COL, payload={}, points=[1])
client.delete_payload(COL, keys=["x"], points=[1])
client.update_vectors(COL, points=[models.PointVectors(id=1, vector=[...])])
client.delete(COL, points_selector=models.PointIdsList(points=[1]))

# BUSCA (tudo por query_points)
client.query_points(COL, query=vetor, limit=10, query_filter=f, with_payload=True)
client.query_points(COL, query=42)                      # parecido com o ponto 42
client.query_points(COL, query=models.RecommendQuery(...))
client.query_points(COL, query=models.DiscoverQuery(...))
client.query_points(COL, query=models.ContextQuery(...))
client.query_points(COL, prefetch=[...], query=models.FusionQuery(fusion=models.Fusion.RRF))
client.query_points(COL, query=models.NearestQuery(nearest=v, mmr=models.Mmr(diversity=0.5)))
client.query_points_groups(COL, query=v, group_by="doc_id", limit=5, group_size=3)
client.query_batch_points(COL, requests=[...])
client.scroll(COL, limit=500, offset=proximo)

# SNAPSHOT / ALIAS
client.create_snapshot(COL)
client.recover_snapshot(COL, location="file:///...")
client.update_collection_aliases(change_aliases_operations=[...])
```

### Condições de filtro

| Condição | Uso |
|---|---|
| `MatchValue(value=x)` | igualdade |
| `MatchAny(any=[...])` | IN |
| `MatchExcept(**{"except": [...]})` | NOT IN |
| `MatchText(text="...")` | contém frase (requer índice de texto) |
| `MatchTextAny(text="...")` | contém qualquer palavra |
| `Range(gte=, lte=, gt=, lt=)` | faixa numérica |
| `DatetimeRange(gte=, lte=)` | faixa de data |
| `GeoRadius` / `GeoBoundingBox` | geolocalização |
| `ValuesCount(gte=n)` | tamanho de array |
| `IsEmptyCondition` / `IsNullCondition` | vazio / nulo |
| `HasIdCondition(has_id=[...])` | por ID |
| `NestedCondition(nested=...)` | objeto aninhado |

### Tipos de query

| Query | Para quê |
|---|---|
| vetor cru | vizinho mais próximo |
| ID do ponto | "parecido com este" |
| `NearestQuery` + `Mmr` | resultados diversos |
| `RecommendQuery` | positivos e negativos |
| `DiscoverQuery` | busca guiada por âncoras |
| `ContextQuery` | exploração de região |
| `FusionQuery` | híbrida (RRF / DBSF) |
| lista de vetores | rerank multivector (ColBERT) |

---

## 25. Links

- Documentação oficial: https://qdrant.tech/documentation/
- Relevância e MMR: https://qdrant.tech/documentation/search/search-relevance/
- Repositório do cliente Python: https://github.com/qdrant/qdrant-client
- Changelog do cliente (o que mudou em cada versão): https://github.com/qdrant/qdrant-client/releases

> A documentação separada do cliente Python (`python-client.qdrant.tech`) foi **descontinuada** na 1.18 — tudo está consolidado em `qdrant.tech/documentation`.
