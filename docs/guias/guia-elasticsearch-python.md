# Guia Completo: Elasticsearch com Python

> Baseado no cliente oficial `elasticsearch-py` **9.x** (versão atual: 9.5.0, requer Python 3.10+).
> A API mudou bastante da versão 7 para a 8/9 — se você achar tutorial usando `body={...}`, é antigo.

---

## 1. Conceitos básicos (rápido, mas necessário)

Elasticsearch é um banco de busca distribuído. O modelo mental:

| Conceito | O que é | Analogia SQL |
|---|---|---|
| **Índice** (index) | Coleção de documentos | Tabela |
| **Documento** | Um JSON com `_id` | Linha |
| **Campo** (field) | Chave do JSON | Coluna |
| **Mapping** | Definição dos tipos dos campos | Schema |
| **Shard** | Pedaço físico do índice | Partição |
| **Réplica** | Cópia de um shard | Réplica |
| **Analyzer** | Quebra texto em tokens para busca | — |

O truque central é o **índice invertido**: em vez de guardar "documento → palavras", ele guarda "palavra → documentos". Por isso a busca full-text é instantânea.

### `text` vs `keyword` — a confusão nº 1

```
"Notebook Dell XPS"
```

- Como `text`  → analisado, vira `["notebook", "dell", "xps"]`. Serve para **buscar**.
- Como `keyword` → guardado inteiro, `"Notebook Dell XPS"`. Serve para **filtrar, agrupar e ordenar**.

Na dúvida, mapeie os dois (é o padrão do ES):

```json
"nome": {
  "type": "text",
  "fields": { "raw": { "type": "keyword" } }
}
```

Aí você busca em `nome` e agrupa/ordena em `nome.raw`.

---

## 2. Subir o Elasticsearch localmente

**Opção mais rápida (script oficial, sobe ES + Kibana):**

```bash
curl -fsSL https://elastic.co/start-local | sh
```

**Docker manual, sem segurança (só para estudo):**

```bash
docker run -d --name es \
  -p 9200:9200 \
  -e "discovery.type=single-node" \
  -e "xpack.security.enabled=false" \
  -e "ES_JAVA_OPTS=-Xms1g -Xmx1g" \
  docker.elastic.co/elasticsearch/elasticsearch:9.3.0
```

Teste:

```bash
curl http://localhost:9200
```

**docker-compose.yml para desenvolvimento:**

```yaml
services:
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:9.3.0
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=false
      - ES_JAVA_OPTS=-Xms1g -Xmx1g
    ports:
      - "9200:9200"
    volumes:
      - esdata:/usr/share/elasticsearch/data
    healthcheck:
      test: ["CMD-SHELL", "curl -s http://localhost:9200 >/dev/null || exit 1"]
      interval: 10s
      retries: 10

  kibana:
    image: docker.elastic.co/kibana/kibana:9.3.0
    environment:
      - ELASTICSEARCH_HOSTS=http://elasticsearch:9200
    ports:
      - "5601:5601"
    depends_on:
      elasticsearch:
        condition: service_healthy

volumes:
  esdata:
```

---

## 3. Instalação do cliente Python

```bash
pip install "elasticsearch>=9,<10"

# extras úteis
pip install "elasticsearch[async]"    # cliente assíncrono (aiohttp)
pip install "elasticsearch[orjson]"   # serialização JSON mais rápida
```

> **Regra de ouro de versão:** o major do cliente deve casar com o major do servidor.
> ES 9.x → `elasticsearch>=9,<10`. ES 8.x → `elasticsearch>=8,<9`.

---

## 4. Conectando

### 4.1 Local sem segurança

```python
from elasticsearch import Elasticsearch

es = Elasticsearch("http://localhost:9200")

print(es.info())
print(es.ping())  # True/False
```

### 4.2 Com usuário e senha (HTTPS, padrão do ES 8+)

```python
es = Elasticsearch(
    "https://localhost:9200",
    basic_auth=("elastic", "sua_senha"),
    ca_certs="/caminho/http_ca.crt",
)
```

Pegando o certificado do container:

```bash
docker cp es:/usr/share/elasticsearch/config/certs/http_ca.crt .
```

### 4.3 Com API Key (recomendado em produção)

```python
es = Elasticsearch(
    "https://meu-cluster:9200",
    api_key="SUA_API_KEY_BASE64",
)

# ou no formato (id, api_key)
es = Elasticsearch("https://meu-cluster:9200", api_key=("id_da_key", "valor"))
```

### 4.4 Elastic Cloud

```python
es = Elasticsearch(
    cloud_id="meu-deploy:dXMtZWFzdDE...",
    api_key="SUA_API_KEY",
)
```

### 4.5 Configurações de conexão que importam

```python
es = Elasticsearch(
    ["https://no1:9200", "https://no2:9200", "https://no3:9200"],
    api_key="...",
    request_timeout=30,          # timeout por requisição (segundos)
    max_retries=3,               # tentativas em caso de falha
    retry_on_timeout=True,
    http_compress=True,          # gzip — vale muito em bulk
    verify_certs=True,
    sniff_on_start=False,        # descoberta de nós; cuidado atrás de proxy
)
```

### 4.6 `.options()` — ajustes por chamada

Substitui os antigos parâmetros `ignore=`, `request_timeout=` inline:

```python
# ignorar erro 404 ao deletar índice inexistente
es.options(ignore_status=404).indices.delete(index="produtos")

# timeout maior só nesta chamada
es.options(request_timeout=120).search(index="produtos", query={"match_all": {}})

# headers customizados
es.options(headers={"X-Origem": "meu-app"}).info()
```

### 4.7 Padrão de projeto: cliente único e reutilizado

```python
# es_client.py
import os
from functools import lru_cache
from elasticsearch import Elasticsearch

@lru_cache(maxsize=1)
def get_es() -> Elasticsearch:
    return Elasticsearch(
        os.environ.get("ES_URL", "http://localhost:9200"),
        api_key=os.environ.get("ES_API_KEY"),
        request_timeout=30,
        max_retries=3,
        retry_on_timeout=True,
        http_compress=True,
    )
```

O cliente é thread-safe e mantém pool de conexões. **Nunca** crie um `Elasticsearch()` por requisição.

---

## 5. Índices: criar, inspecionar, deletar

```python
INDICE = "produtos"

# existe?
if es.indices.exists(index=INDICE):
    es.indices.delete(index=INDICE)

# criar com settings + mappings
es.indices.create(
    index=INDICE,
    settings={
        "number_of_shards": 1,
        "number_of_replicas": 0,
        "refresh_interval": "1s",
    },
    mappings={
        "properties": {
            "nome":      {"type": "text",
                          "fields": {"raw": {"type": "keyword"}}},
            "descricao": {"type": "text"},
            "categoria": {"type": "keyword"},
            "preco":     {"type": "float"},
            "estoque":   {"type": "integer"},
            "ativo":     {"type": "boolean"},
            "tags":      {"type": "keyword"},
            "criado_em": {"type": "date"},
            "local":     {"type": "geo_point"},
        }
    },
)
```

### Inspecionar

```python
es.indices.get_mapping(index=INDICE)      # mapping atual
es.indices.get_settings(index=INDICE)     # settings
es.indices.stats(index=INDICE)            # estatísticas
es.count(index=INDICE)["count"]           # nº de documentos

# listagem legível (formato do cat API)
print(es.cat.indices(format="json"))
print(es.cat.health(format="json"))
```

### Adicionar campo a um mapping existente

Você pode **adicionar** campos, mas não **mudar o tipo** de um campo existente.

```python
es.indices.put_mapping(
    index=INDICE,
    properties={"desconto": {"type": "float"}},
)
```

Se precisar mudar tipo → criar índice novo + `reindex` (seção 12).

---

## 6. CRUD de documentos

### Indexar (criar ou substituir)

```python
from datetime import datetime

doc = {
    "nome": "Notebook Dell XPS 13",
    "descricao": "Ultrabook leve com tela InfinityEdge",
    "categoria": "informatica",
    "preco": 8999.90,
    "estoque": 12,
    "ativo": True,
    "tags": ["notebook", "dell", "premium"],
    "criado_em": datetime.now(),
}

resp = es.index(index=INDICE, id="1", document=doc)
print(resp["result"])  # 'created' ou 'updated'
```

Sem `id` o Elasticsearch gera um automaticamente:

```python
resp = es.index(index=INDICE, document=doc)
print(resp["_id"])
```

### `create` — falha se já existir

```python
from elasticsearch import ConflictError

try:
    es.create(index=INDICE, id="1", document=doc)
except ConflictError:
    print("Documento já existe")
```

### Buscar por ID

```python
from elasticsearch import NotFoundError

try:
    r = es.get(index=INDICE, id="1")
    print(r["_source"])
except NotFoundError:
    print("Não encontrado")

# só alguns campos
es.get(index=INDICE, id="1", source_includes=["nome", "preco"])

# só checar existência (mais barato)
es.exists(index=INDICE, id="1")
```

### Buscar vários IDs de uma vez

```python
r = es.mget(index=INDICE, ids=["1", "2", "3"])
for d in r["docs"]:
    if d["found"]:
        print(d["_source"]["nome"])
```

### Atualizar (parcial)

```python
es.update(index=INDICE, id="1", doc={"preco": 7999.90, "estoque": 10})
```

### Upsert — atualiza se existe, cria se não existe

```python
es.update(
    index=INDICE,
    id="99",
    doc={"preco": 100.0},
    doc_as_upsert=True,
)
```

### Atualizar com script (ex.: decrementar estoque)

```python
es.update(
    index=INDICE,
    id="1",
    script={
        "source": "ctx._source.estoque -= params.qtd",
        "lang": "painless",
        "params": {"qtd": 3},
    },
)
```

Script com upsert e lógica condicional:

```python
es.update(
    index=INDICE,
    id="1",
    script={
        "source": """
            if (ctx._source.estoque >= params.qtd) {
                ctx._source.estoque -= params.qtd;
                ctx._source.vendidos = (ctx._source.vendidos ?: 0) + params.qtd;
            } else {
                ctx.op = 'noop';
            }
        """,
        "params": {"qtd": 3},
    },
    upsert={"estoque": 0, "vendidos": 0},
)
```

### Deletar

```python
es.delete(index=INDICE, id="1")
es.options(ignore_status=404).delete(index=INDICE, id="inexistente")
```

### `refresh` — por que "indexei mas não aparece na busca"

O ES só torna documentos visíveis após um *refresh* (padrão: a cada 1s).

```python
es.index(index=INDICE, id="1", document=doc, refresh=True)       # espera o refresh
es.index(index=INDICE, id="1", document=doc, refresh="wait_for") # melhor: enfileira
es.indices.refresh(index=INDICE)                                 # força manualmente
```

> Em produção **não** use `refresh=True` a cada documento — mata a performance. Use `"wait_for"` só quando precisar ler logo em seguida (ex.: testes).

### Controle de concorrência otimista

```python
r = es.get(index=INDICE, id="1")
seq, primary = r["_seq_no"], r["_primary_term"]

es.index(
    index=INDICE, id="1", document=doc,
    if_seq_no=seq, if_primary_term=primary,   # falha se alguém alterou antes
)
```

---

## 7. Bulk — indexação em massa (a parte que importa na prática)

Indexar 1 documento por requisição é lento. Use `helpers.bulk`.

### 7.1 Básico

```python
from elasticsearch import helpers

def gerar_acoes(produtos):
    for p in produtos:
        yield {
            "_index": INDICE,
            "_id": p["sku"],
            "_source": p,
        }

sucesso, erros = helpers.bulk(es, gerar_acoes(produtos), raise_on_error=False)
print(f"{sucesso} indexados, {len(erros)} erros")
```

### 7.2 Ações mistas (index, update, delete)

```python
acoes = [
    {"_op_type": "index",  "_index": INDICE, "_id": "1", "_source": {"nome": "A"}},
    {"_op_type": "update", "_index": INDICE, "_id": "2", "doc": {"preco": 50}},
    {"_op_type": "delete", "_index": INDICE, "_id": "3"},
    {"_op_type": "create", "_index": INDICE, "_id": "4", "_source": {"nome": "D"}},
]
helpers.bulk(es, acoes, raise_on_error=False)
```

### 7.3 `streaming_bulk` — com barra de progresso e tratamento por item

```python
from elasticsearch import helpers

ok = falhas = 0
for sucesso, info in helpers.streaming_bulk(
    es,
    gerar_acoes(produtos),
    chunk_size=1000,
    max_chunk_bytes=10 * 1024 * 1024,   # 10MB
    raise_on_error=False,
    max_retries=3,
    initial_backoff=2,
):
    if sucesso:
        ok += 1
    else:
        falhas += 1
        print("Falhou:", info)

print(f"OK: {ok} | Falhas: {falhas}")
```

Com `tqdm`:

```python
from tqdm import tqdm

for sucesso, info in tqdm(
    helpers.streaming_bulk(es, gerar_acoes(produtos), chunk_size=500),
    total=len(produtos),
):
    pass
```

### 7.4 `parallel_bulk` — múltiplas threads

```python
for sucesso, info in helpers.parallel_bulk(
    es,
    gerar_acoes(produtos),
    thread_count=4,
    chunk_size=500,
    queue_size=4,
):
    if not sucesso:
        print(info)
```

### 7.5 Indexando um CSV grande sem estourar memória

```python
import csv
from elasticsearch import helpers

def acoes_do_csv(caminho, indice):
    with open(caminho, newline="", encoding="utf-8") as f:
        for linha in csv.DictReader(f):
            yield {
                "_index": indice,
                "_id": linha["id"],
                "_source": {
                    "nome": linha["nome"],
                    "preco": float(linha["preco"]),
                    "categoria": linha["categoria"],
                },
            }

helpers.bulk(es, acoes_do_csv("produtos.csv", INDICE), chunk_size=2000)
```

### 7.6 Configurações para carga inicial pesada

```python
# antes da carga
es.indices.put_settings(index=INDICE, settings={
    "refresh_interval": "-1",     # desliga refresh
    "number_of_replicas": 0,      # sem réplicas
})

helpers.bulk(es, gerar_acoes(milhoes_de_docs), chunk_size=2000)

# depois da carga
es.indices.put_settings(index=INDICE, settings={
    "refresh_interval": "1s",
    "number_of_replicas": 1,
})
es.indices.forcemerge(index=INDICE, max_num_segments=1)
```

Isso pode deixar a carga **várias vezes** mais rápida.

---

## 8. Buscas — o catálogo de queries

Estrutura geral em 8.x/9.x: parâmetros no nível superior, sem `body`.

```python
r = es.search(
    index=INDICE,
    query={...},
    size=10,
    from_=0,        # note o underscore! 'from' é palavra reservada em Python
    sort=[...],
    aggs={...},
)

print(r["hits"]["total"]["value"])   # total de resultados
for hit in r["hits"]["hits"]:
    print(hit["_score"], hit["_source"]["nome"])
```

### 8.1 Tudo

```python
es.search(index=INDICE, query={"match_all": {}}, size=100)
```

### 8.2 `match` — busca full-text (analisada)

```python
es.search(index=INDICE, query={
    "match": {"descricao": "notebook leve"}
})
# encontra docs com "notebook" OU "leve"
```

Exigindo todos os termos:

```python
es.search(index=INDICE, query={
    "match": {
        "descricao": {"query": "notebook leve", "operator": "and"}
    }
})
```

Ou uma porcentagem mínima:

```python
es.search(index=INDICE, query={
    "match": {
        "descricao": {"query": "notebook leve barato", "minimum_should_match": "75%"}
    }
})
```

### 8.3 `match_phrase` — frase exata na ordem

```python
es.search(index=INDICE, query={
    "match_phrase": {"descricao": "ultrabook leve"}
})

# permitindo palavras entre os termos
es.search(index=INDICE, query={
    "match_phrase": {"descricao": {"query": "notebook premium", "slop": 2}}
})
```

### 8.4 `multi_match` — vários campos

```python
es.search(index=INDICE, query={
    "multi_match": {
        "query": "dell xps",
        "fields": ["nome^3", "descricao", "tags"],   # ^3 = peso 3x
        "type": "best_fields",   # best_fields | most_fields | cross_fields | phrase
        "fuzziness": "AUTO",
    }
})
```

### 8.5 `term` / `terms` — valor exato (sem análise)

```python
# um valor
es.search(index=INDICE, query={"term": {"categoria": "informatica"}})

# vários valores (OR)
es.search(index=INDICE, query={"terms": {"categoria": ["informatica", "games"]}})
```

> ⚠️ `term` em campo `text` quase nunca funciona como esperado — use em `keyword`.

### 8.6 `range` — faixas de número e data

```python
es.search(index=INDICE, query={
    "range": {"preco": {"gte": 1000, "lte": 5000}}
})

es.search(index=INDICE, query={
    "range": {"criado_em": {"gte": "now-30d/d", "lte": "now"}}
})

es.search(index=INDICE, query={
    "range": {"criado_em": {"gte": "2026-01-01", "format": "yyyy-MM-dd"}}
})
```

### 8.7 `bool` — combinando condições (o mais usado de todos)

```python
es.search(index=INDICE, query={
    "bool": {
        "must":     [{"match": {"descricao": "notebook"}}],      # obrigatório, conta score
        "filter":   [                                            # obrigatório, SEM score (rápido, cacheado)
            {"term": {"ativo": True}},
            {"range": {"preco": {"lte": 10000}}},
        ],
        "should":   [{"term": {"tags": "premium"}}],              # opcional, aumenta score
        "must_not": [{"term": {"categoria": "usado"}}],           # exclusão
        "minimum_should_match": 0,
    }
})
```

**Regra prática:** filtro binário (sim/não) → `filter`. Relevância → `must`/`should`. `filter` é mais rápido porque não calcula score e é cacheado.

### 8.8 Existência, prefixo, curinga, regex, fuzzy

```python
# campo existe e não é nulo
es.search(index=INDICE, query={"exists": {"field": "desconto"}})

# começa com
es.search(index=INDICE, query={"prefix": {"nome.raw": "Note"}})

# curinga (custoso — evite iniciar com *)
es.search(index=INDICE, query={"wildcard": {"nome.raw": "Note*"}})

# regex
es.search(index=INDICE, query={"regexp": {"nome.raw": "Note.*13"}})

# tolerante a erro de digitação
es.search(index=INDICE, query={
    "fuzzy": {"nome": {"value": "notbook", "fuzziness": "AUTO"}}
})

# por IDs
es.search(index=INDICE, query={"ids": {"values": ["1", "2", "3"]}})
```

### 8.9 `query_string` e `simple_query_string`

```python
# sintaxe poderosa, mas quebra com input inválido — não exponha a usuário final
es.search(index=INDICE, query={
    "query_string": {
        "query": "(notebook OR laptop) AND dell NOT usado",
        "default_field": "descricao",
    }
})

# versão tolerante a erro de sintaxe — segura para caixa de busca pública
es.search(index=INDICE, query={
    "simple_query_string": {
        "query": "notebook +dell -usado",
        "fields": ["nome^2", "descricao"],
        "default_operator": "and",
    }
})
```

### 8.10 Ordenação

```python
es.search(
    index=INDICE,
    query={"match_all": {}},
    sort=[
        {"preco": {"order": "asc"}},
        {"criado_em": {"order": "desc"}},
        "_score",
    ],
)
```

> Ordenar por campo `text` dá erro. Use o subcampo `keyword` (`nome.raw`).

### 8.11 Escolhendo campos retornados (`_source`)

```python
es.search(index=INDICE, query={"match_all": {}}, source=["nome", "preco"])
es.search(index=INDICE, query={"match_all": {}}, source=False)          # só IDs
es.search(index=INDICE, query={"match_all": {}},
          source={"includes": ["nome*"], "excludes": ["nome.raw"]})
```

### 8.12 Highlight — destacar os trechos que casaram

```python
r = es.search(
    index=INDICE,
    query={"match": {"descricao": "ultrabook leve"}},
    highlight={
        "fields": {"descricao": {}},
        "pre_tags": ["<mark>"],
        "post_tags": ["</mark>"],
        "fragment_size": 150,
        "number_of_fragments": 3,
    },
)

for hit in r["hits"]["hits"]:
    for frag in hit.get("highlight", {}).get("descricao", []):
        print(frag)
```

### 8.13 Campos calculados (`runtime_mappings` e `script_fields`)

```python
r = es.search(
    index=INDICE,
    runtime_mappings={
        "preco_com_imposto": {
            "type": "double",
            "script": "emit(doc['preco'].value * 1.15)",
        }
    },
    query={"range": {"preco_com_imposto": {"lte": 5000}}},
    fields=["nome", "preco_com_imposto"],
    source=False,
)
```

### 8.14 Ajustando relevância com `function_score`

```python
es.search(index=INDICE, query={
    "function_score": {
        "query": {"match": {"descricao": "notebook"}},
        "functions": [
            {"filter": {"term": {"tags": "promocao"}}, "weight": 3},
            {"field_value_factor": {
                "field": "vendidos", "modifier": "log1p", "missing": 0
            }},
            {"gauss": {"criado_em": {"origin": "now", "scale": "30d", "decay": 0.5}}},
        ],
        "score_mode": "sum",
        "boost_mode": "multiply",
    }
})
```

### 8.15 Entendendo o score (`explain`)

```python
r = es.explain(index=INDICE, id="1", query={"match": {"descricao": "notebook"}})
print(r["explanation"])

# ou junto da busca
es.search(index=INDICE, query={"match": {"descricao": "notebook"}}, explain=True)
```

---

## 9. Paginação

### 9.1 `from` + `size` — só para poucas páginas

```python
pagina, tamanho = 3, 20
es.search(index=INDICE, query={"match_all": {}},
          from_=(pagina - 1) * tamanho, size=tamanho)
```

Limite padrão: 10.000 resultados (`index.max_result_window`). **Não** aumente esse limite — use `search_after`.

### 9.2 `search_after` — paginação profunda correta

```python
def paginar(es, indice, tamanho=100):
    sort = [{"criado_em": "asc"}, {"_id": "asc"}]   # precisa ser único
    search_after = None

    while True:
        params = {"index": indice, "query": {"match_all": {}},
                  "sort": sort, "size": tamanho}
        if search_after:
            params["search_after"] = search_after

        r = es.search(**params)
        hits = r["hits"]["hits"]
        if not hits:
            break

        yield from hits
        search_after = hits[-1]["sort"]

for hit in paginar(es, INDICE):
    print(hit["_source"]["nome"])
```

### 9.3 `search_after` + PIT (Point in Time) — resultados consistentes

```python
pit = es.open_point_in_time(index=INDICE, keep_alive="2m")
pit_id = pit["id"]

search_after = None
try:
    while True:
        params = {
            "query": {"match_all": {}},
            "pit": {"id": pit_id, "keep_alive": "2m"},
            "sort": [{"_shard_doc": "asc"}],
            "size": 500,
        }
        if search_after:
            params["search_after"] = search_after

        r = es.search(**params)
        hits = r["hits"]["hits"]
        if not hits:
            break

        for h in hits:
            print(h["_source"]["nome"])

        search_after = hits[-1]["sort"]
        pit_id = r["pit_id"]
finally:
    es.close_point_in_time(id=pit_id)
```

### 9.4 `helpers.scan` — jeito mais simples de varrer tudo

```python
from elasticsearch import helpers

for doc in helpers.scan(
    es,
    index=INDICE,
    query={"query": {"term": {"categoria": "informatica"}}},
    size=1000,
    scroll="5m",
):
    print(doc["_source"]["nome"])
```

Ideal para exportação/ETL. Não garante ordem, mas é eficiente e simples.

---

## 10. Agregações — a parte analítica

### 10.1 Métricas simples

```python
r = es.search(
    index=INDICE,
    size=0,                       # não quer os documentos, só os números
    aggs={
        "preco_medio":  {"avg":   {"field": "preco"}},
        "preco_max":    {"max":   {"field": "preco"}},
        "preco_min":    {"min":   {"field": "preco"}},
        "receita":      {"sum":   {"field": "preco"}},
        "estatisticas": {"stats": {"field": "preco"}},
        "categorias_distintas": {"cardinality": {"field": "categoria"}},
        "percentis": {"percentiles": {"field": "preco", "percents": [50, 90, 99]}},
    },
)

print(r["aggregations"]["preco_medio"]["value"])
print(r["aggregations"]["estatisticas"])
```

### 10.2 `terms` — agrupar por valor (GROUP BY)

```python
r = es.search(index=INDICE, size=0, aggs={
    "por_categoria": {
        "terms": {"field": "categoria", "size": 20, "order": {"_count": "desc"}}
    }
})

for b in r["aggregations"]["por_categoria"]["buckets"]:
    print(b["key"], b["doc_count"])
```

### 10.3 Agregações aninhadas

```python
r = es.search(index=INDICE, size=0, aggs={
    "por_categoria": {
        "terms": {"field": "categoria", "size": 10},
        "aggs": {
            "preco_medio": {"avg": {"field": "preco"}},
            "estoque_total": {"sum": {"field": "estoque"}},
            "mais_caros": {
                "top_hits": {
                    "size": 3,
                    "sort": [{"preco": "desc"}],
                    "_source": ["nome", "preco"],
                }
            },
        },
    }
})

for b in r["aggregations"]["por_categoria"]["buckets"]:
    print(f"{b['key']}: {b['doc_count']} itens, média R$ {b['preco_medio']['value']:.2f}")
    for h in b["mais_caros"]["hits"]["hits"]:
        print("   -", h["_source"]["nome"])
```

Ordenando os buckets por uma sub-agregação:

```python
aggs={
    "por_categoria": {
        "terms": {"field": "categoria", "order": {"preco_medio": "desc"}},
        "aggs": {"preco_medio": {"avg": {"field": "preco"}}},
    }
}
```

### 10.4 `date_histogram` — série temporal

```python
r = es.search(index=INDICE, size=0, aggs={
    "por_mes": {
        "date_histogram": {
            "field": "criado_em",
            "calendar_interval": "month",     # day, week, month, quarter, year
            "format": "yyyy-MM",
            "min_doc_count": 0,
            "time_zone": "America/Sao_Paulo",
        },
        "aggs": {
            "receita": {"sum": {"field": "preco"}},
            "acumulado": {"cumulative_sum": {"buckets_path": "receita"}},
            "media_movel": {
                "moving_fn": {"buckets_path": "receita", "window": 3,
                              "script": "MovingFunctions.unweightedAvg(values)"}
            },
        },
    }
})

for b in r["aggregations"]["por_mes"]["buckets"]:
    print(b["key_as_string"], b["doc_count"], b["receita"]["value"])
```

### 10.5 `range` e `histogram`

```python
aggs={
    "faixas_de_preco": {
        "range": {
            "field": "preco",
            "ranges": [
                {"key": "barato",     "to": 500},
                {"key": "medio",      "from": 500, "to": 2000},
                {"key": "caro",       "from": 2000},
            ],
        }
    },
    "distribuicao": {"histogram": {"field": "preco", "interval": 1000}},
}
```

### 10.6 `filters` — vários grupos nomeados

```python
aggs={
    "grupos": {
        "filters": {
            "filters": {
                "ativos":    {"term": {"ativo": True}},
                "sem_estoque": {"term": {"estoque": 0}},
                "promocao":  {"term": {"tags": "promocao"}},
            }
        },
        "aggs": {"preco_medio": {"avg": {"field": "preco"}}},
    }
}
```

### 10.7 `composite` — paginar agregações grandes

```python
after = None
while True:
    agg = {"composite": {"size": 1000,
                         "sources": [{"cat": {"terms": {"field": "categoria"}}}]}}
    if after:
        agg["composite"]["after"] = after

    r = es.search(index=INDICE, size=0, aggs={"paginado": agg})
    buckets = r["aggregations"]["paginado"]["buckets"]
    if not buckets:
        break

    for b in buckets:
        print(b["key"]["cat"], b["doc_count"])

    after = r["aggregations"]["paginado"].get("after_key")
    if not after:
        break
```

### 10.8 Padrão "busca facetada" (e-commerce)

```python
r = es.search(
    index=INDICE,
    size=10,
    query={
        "bool": {
            "must": [{"multi_match": {"query": "notebook", "fields": ["nome^2", "descricao"]}}],
            "filter": [{"term": {"ativo": True}}],
        }
    },
    aggs={
        "categorias": {"terms": {"field": "categoria", "size": 10}},
        "marcas": {"terms": {"field": "tags", "size": 10}},
        "faixas": {"range": {"field": "preco", "ranges": [
            {"to": 1000}, {"from": 1000, "to": 5000}, {"from": 5000}
        ]}},
    },
)
```

---

## 11. Análise de texto (e o caso do português)

### Testando um analyzer

```python
r = es.indices.analyze(analyzer="standard", text="Notebooks São Ótimos!")
print([t["token"] for t in r["tokens"]])
# ['notebooks', 'são', 'ótimos']

r = es.indices.analyze(analyzer="portuguese", text="Notebooks São Ótimos!")
print([t["token"] for t in r["tokens"]])
# stemming aplicado: 'notebook', 'sao', 'otim'
```

### Índice configurado para português (com acento tolerante)

```python
es.indices.create(
    index="artigos",
    settings={
        "analysis": {
            "filter": {
                "pt_stemmer": {"type": "stemmer", "language": "light_portuguese"},
                "pt_stop":    {"type": "stop", "stopwords": "_portuguese_"},
            },
            "analyzer": {
                "pt_br": {
                    "type": "custom",
                    "tokenizer": "standard",
                    "filter": ["lowercase", "asciifolding", "pt_stop", "pt_stemmer"],
                }
            },
        }
    },
    mappings={
        "properties": {
            "titulo": {
                "type": "text",
                "analyzer": "pt_br",
                "fields": {"raw": {"type": "keyword"}},
            },
            "corpo": {"type": "text", "analyzer": "pt_br"},
        }
    },
)
```

Com `asciifolding`, buscar "orgao" encontra "órgão". Com o stemmer, "correndo" encontra "correr".

### Autocomplete com `edge_ngram`

```python
es.indices.create(
    index="sugestoes",
    settings={
        "analysis": {
            "tokenizer": {
                "autocomplete_tok": {
                    "type": "edge_ngram", "min_gram": 2, "max_gram": 20,
                    "token_chars": ["letter", "digit"],
                }
            },
            "analyzer": {
                "autocomplete": {
                    "tokenizer": "autocomplete_tok",
                    "filter": ["lowercase", "asciifolding"],
                },
                "autocomplete_search": {
                    "tokenizer": "lowercase",
                    "filter": ["asciifolding"],
                },
            },
        }
    },
    mappings={
        "properties": {
            "nome": {
                "type": "text",
                "analyzer": "autocomplete",              # na indexação, gera prefixos
                "search_analyzer": "autocomplete_search", # na busca, não gera
            }
        }
    },
)

es.search(index="sugestoes", query={"match": {"nome": "note"}})
```

> O `search_analyzer` diferente é essencial. Sem ele, a busca também vira n-gramas e os resultados ficam péssimos.

### `completion suggester` — autocomplete otimizado

```python
es.indices.create(index="produtos_ac", mappings={
    "properties": {
        "nome": {"type": "text"},
        "sugestao": {"type": "completion"},
    }
})

es.index(index="produtos_ac", document={
    "nome": "Notebook Dell XPS",
    "sugestao": {"input": ["Notebook Dell XPS", "Dell XPS", "XPS 13"], "weight": 10},
})
es.indices.refresh(index="produtos_ac")

r = es.search(index="produtos_ac", suggest={
    "completa": {
        "prefix": "note",
        "completion": {"field": "sugestao", "size": 5, "skip_duplicates": True},
    }
})

for opt in r["suggest"]["completa"][0]["options"]:
    print(opt["text"])
```

### Correção de digitação ("você quis dizer?")

```python
r = es.search(index=INDICE, suggest={
    "corrige": {
        "text": "notbook",
        "term": {"field": "descricao", "suggest_mode": "popular"},
    }
})
```

---

## 12. Operações em massa: update/delete by query e reindex

### Update by query

```python
r = es.update_by_query(
    index=INDICE,
    query={"term": {"categoria": "informatica"}},
    script={
        "source": "ctx._source.preco *= params.fator",
        "params": {"fator": 0.9},   # 10% de desconto
    },
    conflicts="proceed",
    wait_for_completion=False,      # roda em background e retorna um task id
)
task_id = r["task"]

# acompanhar
print(es.tasks.get(task_id=task_id))
```

### Delete by query

```python
es.delete_by_query(
    index=INDICE,
    query={"range": {"criado_em": {"lt": "now-1y"}}},
    conflicts="proceed",
)
```

### Reindex — copiar/migrar índice

```python
es.reindex(
    source={"index": "produtos_v1"},
    dest={"index": "produtos_v2"},
    wait_for_completion=False,
)

# com filtro e transformação
es.reindex(
    source={
        "index": "produtos_v1",
        "query": {"term": {"ativo": True}},
        "_source": ["nome", "preco", "categoria"],
    },
    dest={"index": "produtos_v2"},
    script={"source": "ctx._source.migrado_em = params.agora",
            "params": {"agora": "2026-08-29"}},
)

# de outro cluster (precisa liberar reindex.remote.whitelist)
es.reindex(
    source={"remote": {"host": "http://outro-cluster:9200",
                       "username": "elastic", "password": "senha"},
            "index": "produtos"},
    dest={"index": "produtos"},
)
```

### Aliases — o padrão para migração sem downtime

```python
# app sempre lê do alias "produtos"
es.indices.put_alias(index="produtos_v1", name="produtos")

# ... cria produtos_v2 com novo mapping, reindexa ...

# troca atômica: ninguém percebe
es.indices.update_aliases(actions=[
    {"remove": {"index": "produtos_v1", "alias": "produtos"}},
    {"add":    {"index": "produtos_v2", "alias": "produtos"}},
])

es.indices.delete(index="produtos_v1")
```

**Use alias desde o dia 1.** É a diferença entre migrar em 10 segundos e derrubar a aplicação.

### Index templates — mapping automático para índices novos

```python
es.indices.put_index_template(
    name="logs_template",
    index_patterns=["logs-*"],
    template={
        "settings": {"number_of_shards": 1, "number_of_replicas": 1},
        "mappings": {
            "properties": {
                "@timestamp": {"type": "date"},
                "nivel": {"type": "keyword"},
                "mensagem": {"type": "text"},
                "servico": {"type": "keyword"},
            }
        },
    },
    priority=100,
)
```

Qualquer índice `logs-2026.08.29` criado depois já nasce com esse mapping.

---

## 13. Busca vetorial e semântica (kNN)

### 13.1 `dense_vector` + kNN

```python
es.indices.create(index="docs_vetor", mappings={
    "properties": {
        "texto": {"type": "text"},
        "embedding": {
            "type": "dense_vector",
            "dims": 384,
            "index": True,
            "similarity": "cosine",   # cosine | dot_product | l2_norm
        },
    }
})
```

Indexando com `sentence-transformers`:

```python
from sentence_transformers import SentenceTransformer
from elasticsearch import helpers

modelo = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")

textos = ["Como trocar a bateria do notebook", "Configurar rede Wi-Fi", ...]

acoes = [
    {"_index": "docs_vetor",
     "_source": {"texto": t, "embedding": modelo.encode(t).tolist()}}
    for t in textos
]
helpers.bulk(es, acoes)
```

Buscando:

```python
vetor = modelo.encode("bateria acabando rápido").tolist()

r = es.search(
    index="docs_vetor",
    knn={
        "field": "embedding",
        "query_vector": vetor,
        "k": 5,
        "num_candidates": 100,
        "filter": {"term": {"categoria": "hardware"}},   # filtro combinado
    },
    source=["texto"],
)
```

### 13.2 Busca híbrida (léxica + vetorial) com RRF

Combina os pontos fortes das duas: BM25 pega termos exatos, vetor pega sentido.

```python
r = es.search(
    index="docs_vetor",
    retriever={
        "rrf": {
            "retrievers": [
                {"standard": {"query": {"match": {"texto": "bateria notebook"}}}},
                {"knn": {"field": "embedding", "query_vector": vetor,
                         "k": 50, "num_candidates": 200}},
            ],
            "rank_window_size": 50,
            "rank_constant": 20,
        }
    },
    size=10,
)
```

### 13.3 `semantic_text` — deixa o ES gerar o embedding

Requer um *inference endpoint* configurado no cluster.

```python
es.indices.create(index="docs_semantico", mappings={
    "properties": {
        "conteudo": {"type": "semantic_text", "inference_id": "meu-endpoint"},
    }
})

es.index(index="docs_semantico", document={"conteudo": "Como trocar a bateria"})

es.search(index="docs_semantico", query={
    "semantic": {"field": "conteudo", "query": "bateria descarregando"}
})
```

---

## 14. Cliente assíncrono

```bash
pip install "elasticsearch[async]"
```

```python
import asyncio
from elasticsearch import AsyncElasticsearch

async def main():
    es = AsyncElasticsearch("http://localhost:9200")
    try:
        await es.index(index="produtos", id="1", document={"nome": "Teste"})
        await es.indices.refresh(index="produtos")

        r = await es.search(index="produtos", query={"match_all": {}})
        for hit in r["hits"]["hits"]:
            print(hit["_source"])

        # várias buscas em paralelo
        resultados = await asyncio.gather(
            es.search(index="produtos", query={"term": {"categoria": "a"}}),
            es.search(index="produtos", query={"term": {"categoria": "b"}}),
            es.search(index="produtos", query={"term": {"categoria": "c"}}),
        )
    finally:
        await es.close()   # sempre feche

asyncio.run(main())
```

Bulk assíncrono:

```python
from elasticsearch.helpers import async_bulk, async_streaming_bulk

async def gerar():
    for p in produtos:
        yield {"_index": "produtos", "_source": p}

await async_bulk(es, gerar())

async for ok, info in async_streaming_bulk(es, gerar(), chunk_size=500):
    if not ok:
        print(info)
```

---

## 15. DSL — a API "pythônica"

Desde a versão 8.18/9.0 o pacote `elasticsearch-dsl` foi **descontinuado** e integrado ao cliente principal. Troque `elasticsearch_dsl` (underscore) por `elasticsearch.dsl` (ponto).

```python
# antes:  from elasticsearch_dsl import Search
# agora:  from elasticsearch.dsl import Search
```

### 15.1 `Search` — queries encadeadas

```python
from elasticsearch.dsl import Search, Q

s = (
    Search(using=es, index="produtos")
    .query("match", descricao="notebook")
    .filter("term", ativo=True)
    .filter("range", preco={"lte": 10000})
    .exclude("term", categoria="usado")
    .sort("-preco", "criado_em")
    .source(["nome", "preco"])
    .extra(size=20)
)

print(s.to_dict())   # ver o JSON gerado — ótimo para depurar

for hit in s:
    print(hit.nome, hit.preco)

resp = s.execute()
print(resp.hits.total.value)
```

### 15.2 `Q` — compondo com operadores

```python
from elasticsearch.dsl import Q

q = Q("match", nome="notebook") & Q("term", ativo=True)
q = Q("match", nome="notebook") | Q("match", nome="laptop")
q = ~Q("term", categoria="usado")

q = Q("bool",
      must=[Q("match", descricao="notebook")],
      should=[Q("term", tags="premium")],
      minimum_should_match=1)

s = Search(using=es, index="produtos").query(q)
```

### 15.3 Agregações no DSL

```python
s = Search(using=es, index="produtos")[:0]
s.aggs.bucket("por_cat", "terms", field="categoria", size=10) \
      .metric("preco_medio", "avg", field="preco") \
      .metric("top", "top_hits", size=3)

resp = s.execute()
for b in resp.aggregations.por_cat.buckets:
    print(b.key, b.doc_count, b.preco_medio.value)
```

### 15.4 `Document` — mapeamento estilo ORM

```python
from elasticsearch.dsl import Document, Text, Keyword, Float, Date, Boolean, connections

connections.create_connection(hosts=["http://localhost:9200"])

class Produto(Document):
    nome      = Text(fields={"raw": Keyword()})
    descricao = Text(analyzer="portuguese")
    categoria = Keyword()
    preco     = Float()
    ativo     = Boolean()
    criado_em = Date()

    class Index:
        name = "produtos"
        settings = {"number_of_shards": 1, "number_of_replicas": 0}

    def desconto(self, pct):
        self.preco *= (1 - pct / 100)
        self.save()

# cria o índice com o mapping da classe
Produto.init()

# salvar
p = Produto(meta={"id": "1"}, nome="Notebook Dell", categoria="informatica",
            preco=8999.90, ativo=True, criado_em=datetime.now())
p.save()

# ler
p = Produto.get(id="1")
print(p.nome)

# atualizar
p.preco = 7999.90
p.save()

# buscar
for p in Produto.search().query("match", nome="notebook"):
    print(p.nome, p.preco)

# deletar
p.delete()
```

### 15.5 Objetos aninhados

```python
from elasticsearch.dsl import InnerDoc, Nested, Object

class Avaliacao(InnerDoc):
    autor = Keyword()
    nota  = Float()
    texto = Text()

class Produto(Document):
    nome        = Text()
    avaliacoes  = Nested(Avaliacao)
    fabricante  = Object(properties={"nome": Keyword(), "pais": Keyword()})

    class Index:
        name = "produtos"

p = Produto(nome="Notebook")
p.avaliacoes.append(Avaliacao(autor="joao", nota=5, texto="Excelente"))
p.save()
```

Query em campo `nested` (a diferença entre `nested` e `object` importa: `object` "achata" os arrays e mistura os valores):

```python
es.search(index="produtos", query={
    "nested": {
        "path": "avaliacoes",
        "query": {"bool": {"must": [
            {"term": {"avaliacoes.autor": "joao"}},
            {"range": {"avaliacoes.nota": {"gte": 4}}},
        ]}},
        "inner_hits": {},
    }
})
```

---

## 16. Tratamento de erros

```python
from elasticsearch import (
    Elasticsearch,
    ApiError,             # base dos erros HTTP do ES
    NotFoundError,        # 404
    ConflictError,        # 409
    BadRequestError,      # 400
    AuthenticationException,   # 401
    AuthorizationException,    # 403
    ConnectionError,      # rede
    ConnectionTimeout,
    TransportError,       # base de transporte
    SerializationError,
)

try:
    r = es.get(index="produtos", id="999")
except NotFoundError:
    print("Documento não existe")
except ConflictError:
    print("Conflito de versão")
except ConnectionTimeout:
    print("Timeout")
except ConnectionError as e:
    print("Cluster inacessível:", e)
except ApiError as e:
    print(f"Erro {e.status_code}: {e.error}")
    print(e.info)   # corpo completo da resposta de erro
```

### Erros dentro do bulk

O bulk pode retornar 200 e mesmo assim ter itens que falharam:

```python
sucesso, erros = helpers.bulk(es, acoes, raise_on_error=False, stats_only=False)

for erro in erros:
    for op, detalhe in erro.items():
        print(f"{op} id={detalhe.get('_id')}: {detalhe['error']['reason']}")
```

### Retry com backoff exponencial

```python
import time
from elasticsearch import ConnectionError, ConnectionTimeout

def com_retry(fn, tentativas=5, base=1.0):
    for i in range(tentativas):
        try:
            return fn()
        except (ConnectionError, ConnectionTimeout):
            if i == tentativas - 1:
                raise
            time.sleep(base * (2 ** i))

resultado = com_retry(lambda: es.search(index="produtos", query={"match_all": {}}))
```

### Verificação de saúde na inicialização

```python
def esperar_cluster(es, timeout=60):
    r = es.cluster.health(wait_for_status="yellow", timeout=f"{timeout}s")
    if r["status"] == "red":
        raise RuntimeError("Cluster em estado red")
    return r
```

---

## 17. Integrações

### 17.1 Pandas — resultados em DataFrame

```python
import pandas as pd
from elasticsearch import helpers

# via scan (qualquer volume)
docs = helpers.scan(es, index="produtos", query={"query": {"match_all": {}}})
df = pd.DataFrame([d["_source"] | {"_id": d["_id"]} for d in docs])

# agregação → DataFrame
r = es.search(index="produtos", size=0, aggs={
    "por_cat": {"terms": {"field": "categoria", "size": 50},
                "aggs": {"media": {"avg": {"field": "preco"}}}}
})
df_agg = pd.DataFrame([
    {"categoria": b["key"], "qtd": b["doc_count"], "preco_medio": b["media"]["value"]}
    for b in r["aggregations"]["por_cat"]["buckets"]
])
```

Indexando um DataFrame:

```python
def df_para_acoes(df, indice):
    for registro in df.to_dict(orient="records"):
        yield {"_index": indice, "_source": registro}

helpers.bulk(es, df_para_acoes(df, "produtos"), chunk_size=1000)
```

### 17.2 FastAPI

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Query
from elasticsearch import AsyncElasticsearch, NotFoundError

es: AsyncElasticsearch | None = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global es
    es = AsyncElasticsearch("http://localhost:9200")
    yield
    await es.close()

app = FastAPI(lifespan=lifespan)

@app.get("/buscar")
async def buscar(
    q: str,
    categoria: str | None = None,
    pagina: int = 1,
    tamanho: int = Query(20, le=100),
):
    filtros = [{"term": {"ativo": True}}]
    if categoria:
        filtros.append({"term": {"categoria": categoria}})

    r = await es.search(
        index="produtos",
        query={"bool": {
            "must": [{"multi_match": {"query": q, "fields": ["nome^2", "descricao"]}}],
            "filter": filtros,
        }},
        from_=(pagina - 1) * tamanho,
        size=tamanho,
        aggs={"categorias": {"terms": {"field": "categoria", "size": 10}}},
    )

    return {
        "total": r["hits"]["total"]["value"],
        "itens": [h["_source"] | {"id": h["_id"], "score": h["_score"]}
                  for h in r["hits"]["hits"]],
        "facetas": {b["key"]: b["doc_count"]
                    for b in r["aggregations"]["categorias"]["buckets"]},
    }

@app.get("/produtos/{pid}")
async def obter(pid: str):
    try:
        r = await es.get(index="produtos", id=pid)
        return r["_source"]
    except NotFoundError:
        raise HTTPException(404, "Produto não encontrado")
```

### 17.3 Django

```bash
pip install django-elasticsearch-dsl
```

```python
# documents.py
from django_elasticsearch_dsl import Document, fields
from django_elasticsearch_dsl.registries import registry
from .models import Produto

@registry.register_document
class ProdutoDocument(Document):
    categoria = fields.KeywordField(attr="categoria.nome")

    class Index:
        name = "produtos"
        settings = {"number_of_shards": 1, "number_of_replicas": 0}

    class Django:
        model = Produto
        fields = ["nome", "descricao", "preco", "ativo"]
        related_models = [Categoria]
```

```bash
python manage.py search_index --rebuild
```

O pacote sincroniza automaticamente via signals de `save`/`delete`.

---

## 18. Boas práticas e armadilhas comuns

### Performance de busca

- Use `filter` em vez de `must` para condições binárias — não calcula score e é cacheado.
- Não peça `size` grande sem precisar. `size=10000` é quase sempre erro de design.
- Restrinja `_source` aos campos que você usa de verdade.
- Prefira `keyword` a `text` quando o campo é só identificador — economiza índice e memória.
- Evite `wildcard` começando com `*` e `script` em query quente. Use `runtime_mappings` ou pré-calcule o campo.
- `search_after` para paginação profunda, nunca `from` alto.

### Performance de indexação

- Sempre `bulk`. Chunks de 5–15MB costumam ser o ponto ótimo.
- Desligue `refresh_interval` e réplicas durante carga inicial.
- Não use `refresh=True` em cada documento.
- Deixe o ES gerar IDs quando possível (é mais rápido que verificar IDs existentes).
- `http_compress=True` reduz muito o tráfego em bulk.

### Modelagem

- Use **alias** desde o começo. Migrar depois é muito mais fácil.
- Use **index template** para índices por data (`logs-*`).
- Mapping não muda tipo. Planeje ou aceite reindexar.
- Desligue índice de campos que você só armazena: `{"type": "text", "index": False}`.
- Cuidado com **explosão de mapping**: `dynamic: "strict"` evita campos criados por acidente.

```python
mappings={"dynamic": "strict", "properties": {...}}
```

### Operação

- Um cliente por processo, reutilizado.
- Sempre defina `request_timeout` e `max_retries`.
- Nunca exponha o ES direto na internet.
- Use API Key com permissões mínimas em vez do usuário `elastic`.
- Monitore `es.cluster.health()` — status `yellow` em nó único é normal (réplicas não alocadas).

### Armadilhas mais frequentes

| Sintoma | Causa provável |
|---|---|
| "Indexei mas não acha" | Falta de refresh |
| `term` não retorna nada em campo de texto | Campo é `text`, use o subcampo `.keyword` |
| Erro ao ordenar | Ordenando por campo `text`, use `.raw`/`.keyword` |
| "Result window is too large" | `from + size > 10000` → use `search_after` |
| Autocomplete retorna lixo | Falta `search_analyzer` no edge_ngram |
| Bulk "passou" mas faltam docs | Erros por item; cheque a lista de erros do retorno |
| Acento quebra a busca | Falta `asciifolding` no analyzer |

---

## 19. Cheat sheet

```python
# CONEXÃO
es = Elasticsearch("http://localhost:9200")
es = Elasticsearch("https://host:9200", api_key="...")
es.info(); es.ping()

# ÍNDICE
es.indices.create(index="i", mappings={...}, settings={...})
es.indices.exists(index="i")
es.indices.delete(index="i")
es.indices.refresh(index="i")
es.indices.put_mapping(index="i", properties={...})
es.indices.put_alias(index="i", name="alias")

# DOCUMENTO
es.index(index="i", id="1", document={...})
es.create(index="i", id="1", document={...})
es.get(index="i", id="1")
es.mget(index="i", ids=["1","2"])
es.exists(index="i", id="1")
es.update(index="i", id="1", doc={...})
es.update(index="i", id="1", script={...})
es.delete(index="i", id="1")
es.count(index="i")

# BULK
helpers.bulk(es, acoes)
helpers.streaming_bulk(es, acoes, chunk_size=1000)
helpers.parallel_bulk(es, acoes, thread_count=4)
helpers.scan(es, index="i", query={"query": {...}})

# BUSCA
es.search(index="i", query={...}, size=10, from_=0, sort=[...], aggs={...})
es.search(index="i", knn={...})
es.explain(index="i", id="1", query={...})
es.indices.analyze(analyzer="portuguese", text="...")

# EM MASSA
es.update_by_query(index="i", query={...}, script={...})
es.delete_by_query(index="i", query={...})
es.reindex(source={"index":"a"}, dest={"index":"b"})

# PIT / SCROLL
es.open_point_in_time(index="i", keep_alive="2m")
es.close_point_in_time(id=pit_id)

# CLUSTER
es.cluster.health()
es.cat.indices(format="json")
es.tasks.get(task_id="...")
```

### Queries

| Query | Uso |
|---|---|
| `match_all` | tudo |
| `match` | full-text, analisado |
| `match_phrase` | frase exata, ordem importa |
| `multi_match` | full-text em vários campos |
| `term` / `terms` | valor exato (keyword) |
| `range` | faixa numérica/data |
| `bool` | combinar must/filter/should/must_not |
| `exists` | campo presente |
| `prefix` / `wildcard` / `regexp` | padrões |
| `fuzzy` | tolerante a erro de digitação |
| `simple_query_string` | caixa de busca do usuário |
| `nested` | arrays de objetos |
| `function_score` | ajustar relevância |
| `knn` / `semantic` | busca vetorial/semântica |

### Agregações

| Agregação | Uso |
|---|---|
| `avg` `min` `max` `sum` `stats` | métricas |
| `cardinality` | contagem distinta (aproximada) |
| `percentiles` | p50, p90, p99 |
| `terms` | GROUP BY |
| `date_histogram` | série temporal |
| `histogram` / `range` | faixas |
| `filters` | grupos nomeados |
| `composite` | paginar agregações grandes |
| `top_hits` | documentos dentro de cada bucket |
| `cumulative_sum` / `moving_fn` | pipeline sobre buckets |

---

## 20. Links

- Cliente Python (docs oficiais): https://www.elastic.co/docs/reference/elasticsearch/clients/python
- Referência da API do Elasticsearch: https://www.elastic.co/guide/en/elasticsearch/reference/current/index.html
- Repositório: https://github.com/elastic/elasticsearch-py
- Migração de `elasticsearch-dsl` → `elasticsearch.dsl`: veja `dsl_migrating` na documentação
