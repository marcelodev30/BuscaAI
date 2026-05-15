# Avaliação de Qualidade

Como saber se o sistema de RAG é bom? Sem medir, tudo é chute. Este arquivo cobre as métricas de qualidade e o framework RAGAS.

---

## O problema

O desenvolvedor configurou: busca híbrida, reranker ligado, chunk de 512 tokens. Mas isso é bom? É melhor que outra configuração? Sem métricas objetivas, não há resposta — só opinião.

---

## Métricas de retrieval (qualidade da busca)

Estas métricas medem se a **busca** está recuperando os documentos certos.

### Recall@K

Dos documentos relevantes que existem, quantos foram recuperados (entre os K primeiros)?

```
Query: "rescisão contratual"
Documentos relevantes que existem na base: 5
Recuperados no top 5: 4 são relevantes

Recall@5 = 4/5 = 0.80
```

Recall baixo = a busca está **perdendo** documentos importantes.

### Precision@K

Dos K documentos recuperados, quantos são realmente relevantes?

```
Recuperados no top 5: 4 relevantes, 1 irrelevante
Precision@5 = 4/5 = 0.80
```

Precision baixa = a busca está trazendo **lixo** junto.

### MRR (Mean Reciprocal Rank)

O documento mais relevante apareceu em que posição? Quanto mais perto do topo, melhor o MRR.

---

## RAGAS — avaliação do pipeline RAG completo

RAGAS (*Retrieval Augmented Generation Assessment*) é um framework open source específico para avaliar pipelines RAG. Ele vai além do retrieval — avalia também a **resposta gerada** pela LLM.

O documento oficial do projeto BuscaAI cita o RAGAS explicitamente como o framework de avaliação a ser usado.

### As quatro métricas do RAGAS

#### 1. Faithfulness (fidelidade)

A resposta gerada está **ancorada nos documentos** recuperados? Ou a LLM inventou coisas?

```
Chunk recuperado: "O prazo de rescisão é de 30 dias."

Resposta gerada:
"O prazo de rescisão é de 30 dias       ← está no chunk ✓
 e pode ser negociado entre as partes." ← NÃO está no chunk ✗

Faithfulness baixo → a LLM está alucinando.
```

#### 2. Answer Relevancy (relevância da resposta)

A resposta de fato **responde à pergunta**?

```
Query: "qual o prazo de rescisão?"

Resposta A: "O prazo é de 30 dias."         → Answer Relevancy alto ✓
Resposta B: "O contrato foi assinado em 2020." → Answer Relevancy baixo ✗
            (verdadeiro, mas não responde a pergunta)
```

#### 3. Context Precision (precisão do contexto)

Os chunks recuperados eram **relevantes** para a query?

```
Query: "qual o prazo de rescisão?"
Chunks recuperados:
  1. "O prazo de rescisão é de 30 dias."   → relevante ✓
  2. "O aviso deve ser por escrito."        → relevante ✓
  3. "A empresa foi fundada em 1990."       → irrelevante ✗
  4. "O CEO é João Silva."                  → irrelevante ✗
  5. "A multa por atraso é de 10%."         → irrelevante ✗

Context Precision = 2/5 = 0.40 → retrieval trazendo lixo.
```

#### 4. Context Recall (cobertura do contexto)

**Todos** os chunks necessários para responder foram recuperados?

```
Query: "quais as condições de rescisão?"
Chunks necessários para a resposta completa:
  1. "prazo de 30 dias"     → recuperado ✓
  2. "aviso por escrito"    → recuperado ✓
  3. "multa de 10%"         → NÃO recuperado ✗

Context Recall = 2/3 = 0.67 → perdeu informação importante.
```

### Como o RAGAS calcula

O RAGAS usa uma **LLM como juiz** — não são regras fixas, é a LLM analisando semanticamente. Por exemplo, para Faithfulness, ele pega cada frase da resposta e pergunta à LLM se aquela frase tem suporte nos chunks.

### O que o RAGAS precisa para rodar

```
question:     a query
answer:       a resposta gerada pelo seu RAG
contexts:     os chunks que foram recuperados
ground_truth: a resposta esperada (opcional — sem ela, perde-se só o Context Recall)
```

### Interpretando os resultados

O RAGAS não só diz "está ruim" — ele aponta **onde** está ruim, o que orienta o ajuste:

```
Faithfulness baixo       → LLM alucinando → ajustar o system prompt ou aumentar top_k
Answer Relevancy baixo   → resposta fora do alvo → query expansion ou trocar a LLM
Context Precision baixo  → retrieval trazendo lixo → reduzir top_k ou trocar o reranker
Context Recall baixo     → retrieval perdendo coisa → aumentar chunk_size ou top_k
```

---

## O endpoint /benchmark

No BuscaAI, a avaliação é feita pelo endpoint `/benchmark`. A ideia, decidida no projeto, é que o desenvolvedor mande **tudo na própria requisição** — as queries de teste, os documentos esperados, e quais estratégias comparar — e receba os resultados de uma vez, sem precisar configurar arquivos separados.

```
POST /benchmark
{
  "queries": [
    {
      "query": "qual o prazo de rescisão?",
      "documentos_esperados": ["contrato.pdf:3"],
      "resposta_esperada": "30 dias com aviso por escrito"
    }
  ],
  "estrategias": ["bm25", "dense", "hybrid"],
  "incluir_ragas": true
}
```

O framework então roda cada estratégia, gera a resposta com a LLM para cada uma, passa tudo pelo RAGAS, e devolve um comparativo:

```
{
  "resultados": {
    "bm25":   { retrieval: {...}, ragas: {...}, performance: {...} },
    "dense":  { retrieval: {...}, ragas: {...}, performance: {...} },
    "hybrid": { retrieval: {...}, ragas: {...}, performance: {...} }
  },
  "recomendacao": {
    "estrategia": "hybrid",
    "motivo": "melhor RAGAS e retrieval, latência aceitável"
  },
  "comparacao_baseline": {
    "melhoria_vs_bm25": "31% no recall"
  }
}
```

Cada estratégia é avaliada em três dimensões: **retrieval** (recall, precision, MRR), **ragas** (as quatro métricas) e **performance** (latência média e de pico).

---

## Avaliação contínua em produção

Além do benchmark sob demanda, o sistema pode monitorar as queries reais que acontecem em produção:

```python
EVALUATION = {
    "enabled": True,
    "log_queries": True,            # registra o que foi perguntado e retornado
    "latency_tracking": True,       # mede o tempo de cada busca
    "low_score_threshold": 0.5,     # define o que é "score baixo"
    "alert_on_low_score": True      # avisa quando uma query tem resultado ruim
}
```

Isso permite detectar **degradação** ao longo do tempo — por exemplo, se a qualidade começa a cair conforme a base cresce.

---

## Por que isso importa para o projeto

O documento oficial do BuscaAI prevê, na Meta 4 (Validação Experimental), avaliar a acurácia semântica usando o RAGAS e fazer benchmarking de latência, além de comparar a solução com métodos de busca convencionais e com fine-tuning. O endpoint `/benchmark` com RAGAS integrado é exatamente a ferramenta que viabiliza essa meta.
