# LangGraph — Orquestrando o Sistema

O LangGraph é a peça que **controla o fluxo** do BuscaAI. Este arquivo explica o que é um grafo de execução, do zero, e como o LangGraph é usado no projeto.

---

## O que é um grafo (o conceito puro)

Esqueça código por um momento. Um grafo é simplesmente **nós conectados por arestas**.

```
[A] → [B] → [C]
        ↓
       [D]
```

- **Nó** = "onde você está" / uma etapa do processo.
- **Aresta** = "para onde você pode ir" / a transição entre etapas.

Um pipeline de RAG é naturalmente um grafo: você tem etapas que dependem umas das outras, e às vezes o caminho muda dependendo do que aconteceu antes.

---

## O que o LangGraph adiciona: estado compartilhado

O LangGraph pega a ideia de grafo e adiciona um **estado compartilhado**. Imagine uma folha de papel que passa por todas as etapas. Cada nó pode ler o que está escrito nela e escrever coisas novas.

```
A folha começa:   { query: "o que é RAG?" }

Nó 1 lê a query e escreve a estratégia:
{ query: "o que é RAG?", estrategia: "hybrid" }

Nó 2 lê a estratégia, faz a busca, escreve os documentos:
{ query: "...", estrategia: "hybrid", documentos: [...] }
```

Cada nó **recebe o estado**, faz seu trabalho, e **retorna só o que mudou**.

---

## Arestas fixas e arestas condicionais

**Aresta fixa:** sempre vai de A para B, sem pensar.

**Aresta condicional:** olha o estado e **decide** para onde ir.

```
[busca feita]
      ↓
[precisa de reranker?]
    ↙          ↘
[sim]          [não]
[reranker]     [formatar resposta]
```

As arestas condicionais são o que dá ao BuscaAI a sua característica "adaptativa" — a decisão de qual caminho seguir é feita pela lógica do grafo, sem precisar de um agente de IA gastando tokens.

---

## Por que usar LangGraph em vez de código comum

Sem LangGraph, o mesmo fluxo seria um código procedural com `if` espalhados:

```python
def buscar(query):
    config = carregar_config()
    embedding = gerar_embedding(query)
    resultados = qdrant.search(embedding)
    if config["reranker"]:          # if solto no meio do código
        resultados = rerankar(resultados)
    return resultados
```

Funciona, mas conforme cresce fica difícil de manter, testar e modificar.

Com LangGraph você ganha:

- **Visibilidade** — dá para visualizar o fluxo como um diagrama real.
- **Condições limpas** — cada decisão é uma aresta, não um `if` enterrado.
- **Estado explícito** — você sabe exatamente o que trafega entre as etapas.
- **Fácil de modificar** — para adicionar uma etapa, você adiciona um nó e o conecta; não mexe no resto.
- **Observabilidade** — integra com ferramentas (como o LangSmith) que mostram cada nó executado e o estado em cada ponto.

---

## Exemplo concreto de montagem de um grafo

```python
from langgraph.graph import StateGraph
from typing import TypedDict, Literal

# 1. Define o estado — a "folha de papel"
class BuscaState(TypedDict):
    query: str
    config: dict
    embeddings: list
    documentos: list

# 2. Define cada nó (cada etapa)
def carregar_config(state: BuscaState):
    return {"config": configs_carregadas}

def gerar_embedding(state: BuscaState):
    vetor = embedding_model.embed(state["query"])
    return {"embeddings": vetor}

def buscar(state: BuscaState):
    docs = qdrant.search(
        query_vector=state["embeddings"],
        limit=state["config"]["top_k"]
    )
    return {"documentos": docs}

def rerankar(state: BuscaState):
    docs = reranker.rerank(state["query"], state["documentos"])
    return {"documentos": docs}

# 3. Define a condição da aresta condicional
def precisa_rerankar(state: BuscaState):
    return "reranker" if state["config"]["reranker"] else "fim"

# 4. Monta o grafo
grafo = StateGraph(BuscaState)
grafo.add_node("config", carregar_config)
grafo.add_node("embedding", gerar_embedding)
grafo.add_node("busca", buscar)
grafo.add_node("reranker", rerankar)

grafo.add_edge("config", "embedding")       # aresta fixa
grafo.add_edge("embedding", "busca")        # aresta fixa
grafo.add_conditional_edges("busca", precisa_rerankar)  # aresta condicional

grafo.set_entry_point("config")
pipeline = grafo.compile()
```

---

## Os grafos do BuscaAI

O BuscaAI tem três grafos independentes, cada um compilado uma vez e reutilizado sempre.

### Grafo de ingestão

Roda quando dados entram na base.

```
[carregar documento]
        ↓
[chunking]
        ↓
[extrair metadados naturais]   (fonte, página, document_id, data)
        ↓
[indexar no índice invertido]  (para a pré-filtragem léxica)
        ↓
[gerar embedding denso]
[gerar embedding esparso]
        ↓
[salvar no Qdrant]
```

### Grafo de busca

Roda a cada consulta.

```
[carregar config]
        ↓
[gerar embeddings da query]
        ↓
[pré-filtragem léxica]         10M → 50K
        ↓
[filtro de metadados]          (opcional)
        ↓
[busca híbrida]                → top 50
        ↓
[precisa de reranker?] ──não──→ [retornar]
        │ sim
        ↓
[reranker]                     → top 5
        ↓
[retornar]
```

### Grafo de chat

É o grafo de busca, com etapas a mais nas pontas para lidar com conversa.

```
[receber query + histórico]
        ↓
[reformular query com o contexto do histórico]
   "e qual a multa?" → "qual a multa por rescisão contratual?"
        ↓
[ ... mesmo fluxo do grafo de busca ... ]
        ↓
[montar prompt com os chunks + histórico]
        ↓
[LLM gera a resposta]
        ↓
[retornar resposta + fontes]
```

A etapa de **reformular a query** é importante: sem ela, perguntas de acompanhamento como "e qual a multa?" não encontrariam nada relevante na base, porque sozinhas não têm contexto suficiente.

---

## Por que LangGraph e não LangChain "clássico"

O LangChain tem dois mundos: o clássico (chains lineares) e o LangGraph (fluxos como grafos de estado, mais moderno e pensado para fluxos complexos e decisões condicionais).

O BuscaAI usa LangGraph porque precisa de decisões condicionais no fluxo (reranker sim/não, por exemplo) e porque deixa a porta aberta para evoluções mais sofisticadas no futuro. A ressalva honesta: o LangGraph tem uma curva de aprendizado maior, então o fluxo precisa ser bem documentado para outros desenvolvedores entenderem.
