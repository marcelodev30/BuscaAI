# Cache e Observabilidade

Este arquivo cobre duas coisas que mantêm o sistema eficiente e depurável em produção: o cache de queries e o sistema de logs e métricas.

---

## Cache de queries

### O problema

Numa aplicação real, as mesmas perguntas são feitas repetidamente. Sem cache, cada pergunta idêntica passa pelo pipeline inteiro:

```
"qual o prazo de rescisão?" — usuário A às 10h
→ pré-filtragem → busca híbrida → reranker → LLM → resposta

"qual o prazo de rescisão?" — usuário B às 10h05
→ pré-filtragem → busca híbrida → reranker → LLM → resposta (tudo de novo)
```

Isso gasta tempo, consome recursos do Qdrant e, principalmente, **custa tokens de LLM** a cada vez.

### A solução

O cache armazena o resultado de uma query e, quando a mesma query chega de novo, devolve o resultado armazenado sem passar pelo pipeline.

```
"qual o prazo de rescisão?" — usuário A às 10h
→ pipeline completo → resposta → salva no cache

"qual o prazo de rescisão?" — usuário B às 10h05
→ achou no cache → devolve direto (sem pipeline, sem custo)
```

### Como funciona por baixo

O Redis é usado como backend do cache. A lógica é simples:

```
1. query chega
2. gera um hash da query (identificador único)
3. verifica se esse hash existe no Redis
4. se existe → devolve o resultado armazenado
5. se não existe → roda o pipeline → salva no Redis → devolve
```

O hash garante que queries idênticas (mesmo texto, mesma capitalização) apontem para o mesmo resultado. Queries parecidas mas diferentes geram hashes diferentes e passam pelo pipeline normalmente.

### TTL — quanto tempo o cache dura

TTL (*Time To Live*) é o tempo que um resultado fica no cache antes de expirar. Depois que expira, a próxima vez que aquela query chegar ela vai ao pipeline de novo e o resultado é renovado.

```python
CACHE = {
    "enabled": True,
    "backend": "redis",
    "ttl": 3600    # resultado fica no cache por 1 hora
}
```

Escolher o TTL é um trade-off:

```
TTL curto (ex: 5 minutos)
→ resultados sempre frescos
→ pouco aproveitamento do cache

TTL longo (ex: 24 horas)
→ mais eficiente
→ mas se os dados da base mudaram, o cache pode devolver resultado desatualizado
```

Para bases que mudam pouco (documentos jurídicos, manuais técnicos), TTL de horas ou dias faz sentido. Para bases com atualizações frequentes, TTL mais curto ou invalidação manual.

### Invalidação

Quando dados novos são ingeridos, parte do cache pode ficar desatualizada. O framework invalida o cache automaticamente quando uma ingestão **de fato altera dados** — ou seja, quando pelo menos um chunk foi adicionado, modificado ou removido.

Esse detalhe é importante por causa da reingestão agendada. Como a detecção de mudança usa hash do conteúdo (ver o arquivo de operação), a maioria das reingestões agendadas não muda nada — o hash bate, nenhum chunk é tocado. Nesses casos o cache **não** é invalidado, porque não há motivo: os dados são os mesmos. O cache só é limpo quando a ingestão realmente mexeu na base.

O dev também pode forçar a limpeza manualmente:

```bash
rag cache clear    # limpa todo o cache
```

### Quando o cache não ajuda

- Queries únicas e variadas — se cada usuário pergunta algo diferente, o cache não tem reaproveitamento.
- Base com atualizações muito frequentes — o cache expira antes de ser reutilizado.
- Ambiente de desenvolvimento/testes — o dev quer ver o resultado real, não o cacheado.

O cache pode ser desligado completamente no settings:

```python
CACHE = {"enabled": False}
```

---

## Observabilidade

Observabilidade é a capacidade de entender o que está acontecendo **dentro** do sistema a partir do que ele produz para fora: logs, métricas e rastreamento.

Sem observabilidade, quando algo dá errado ou fica lento, você não tem como saber onde nem por quê.

---

## Logs

### O que o BuscaAI loga

O sistema registra eventos em três categorias:

**Logs de query** — cada busca que acontece:
```
{
  "timestamp": "2024-05-14T10:23:45",
  "query": "qual o prazo de rescisão?",
  "estrategia": "hybrid",
  "pre_filter_candidatos": 48231,
  "chunks_recuperados": 50,
  "chunks_finais": 5,
  "reranker": true,
  "cache_hit": false,
  "latencia_total_ms": 342,
  "score_top1": 0.94,
  "usuario": "dev@empresa.com"
}
```

**Logs de ingestão** — cada job processado:
```
{
  "job_id": "a3f8c2...",
  "source": "contrato.pdf",
  "status": "concluido",
  "chunks_gerados": 47,
  "duracao_ms": 8420,
  "erros": 0
}
```

**Logs de erro** — qualquer falha no sistema:
```
{
  "timestamp": "2024-05-14T11:05:12",
  "nivel": "erro",
  "componente": "embedding",
  "mensagem": "OpenAI API timeout após 30s",
  "job_id": "b7d91f...",
  "tentativa": 2
}
```

### Onde os logs ficam

Por padrão no PostgreSQL, o que permite consultar com SQL:

```sql
-- queries mais lentas dos últimos 7 dias
SELECT query, latencia_total_ms
FROM query_logs
WHERE timestamp > NOW() - INTERVAL '7 days'
ORDER BY latencia_total_ms DESC
LIMIT 20;

-- taxa de cache hit
SELECT
  COUNT(*) FILTER (WHERE cache_hit = true) AS cache_hits,
  COUNT(*) AS total,
  ROUND(AVG(CASE WHEN cache_hit THEN 1.0 ELSE 0.0 END) * 100, 1) AS taxa_pct
FROM query_logs
WHERE timestamp > NOW() - INTERVAL '1 day';
```

### Acessando logs pela CLI

```bash
rag logs                    # últimos 50 logs
rag logs --tail 100         # últimos 100
rag logs --filter erro      # só erros
rag logs --filter ingestao  # só ingestões
```

---

## Métricas

Além dos logs (eventos), o sistema expõe **métricas agregadas** — números que resumem o estado do sistema ao longo do tempo.

### O endpoint /metrics

```
GET /metrics
→ {
    "queries": {
      "total_hoje": 1842,
      "latencia_media_ms": 287,
      "latencia_p95_ms": 612,
      "latencia_p99_ms": 891,
      "cache_hit_rate": 0.34
    },
    "retrieval": {
      "score_medio": 0.81,
      "queries_score_baixo": 23    ← queries com score abaixo do threshold
    },
    "ingestao": {
      "jobs_hoje": 3,
      "chunks_total": 10482341,
      "ultimo_job": "2024-05-14T02:00:00"
    },
    "infraestrutura": {
      "qdrant_status": "ok",
      "redis_status": "ok",
      "postgres_status": "ok",
      "workers_ativos": 3
    }
  }
```

### O comando rag status

É um resumo visual das métricas de infraestrutura:

```bash
rag status
→ Qdrant:    ✅ online  (10.2M chunks)
→ Redis:     ✅ online  (cache: 1.2k entradas, hit rate: 34%)
→ Postgres:  ✅ online
→ Workers:   ✅ 3 ativos
→ Jobs:      2 em fila, 1 processando (67% concluído)
→ Último backup: 2024-05-14 03:00 ✅
```

---

## Alertas

O sistema pode avisar quando algo sai do normal:

```python
LOGGING = {
    "enabled": True,
    "backend": "postgresql",
    "log_queries": True,
    "log_results": True,
    "alertas": {
        "latencia_alta_ms": 2000,       # avisa se query demorar mais de 2s
        "score_baixo_threshold": 0.5,   # avisa se resultado tiver score baixo
        "erro_ingestao": True,          # avisa se job falhar
        "backup_falhou": True,
        "notify": "admin@empresa.com"
    }
}
```

---

## Como usar observabilidade para depurar problemas

### "A busca está devolvendo resultados ruins"

```
1. Olha o score_medio nas métricas
   → se < 0.6, o problema é no retrieval

2. Olha os logs da query específica
   → quantos candidatos a pré-filtragem retornou?
   → o reranker estava ligado?

3. Roda um benchmark com RAGAS
   → qual das 4 métricas está baixa?
   → a dica de ajuste está no arquivo 09-avaliacao.md
```

### "A busca está lenta"

```
1. Olha a latência_p99 nas métricas
   → onde está o gargalo? (latência total vs latência de cada etapa)

2. Olha os logs de query com latência alta
   → pre_filter_candidatos muito alto? Ajusta top_n no PRE_FILTERING
   → reranker está dominando o tempo? Considera desligar ou trocar

3. Verifica o cache hit rate
   → se < 20% com queries repetidas, verifica se o cache está habilitado
```

### "A ingestão falhou"

```
1. rag logs --filter erro
   → qual componente falhou? (embedding, qdrant, loader)

2. GET /ingest/status/{job_id}
   → em qual chunk falhou? (o checkpoint diz onde recomeçar)

3. POST /ingest/cancel/{job_id} se precisar cancelar
   → depois inicia de novo — o checkpoint garante que não reprocessa tudo
```
