# Padrões de Fluxo em RAG Modular — Comparativo Completo

Guia completo dos 6 padrões de orquestração do Modular RAG (Gao et al. 2024).
Cada padrão tem diagrama, explicação, métricas, exemplos da literatura e casos de uso.

**Fonte principal:** Gao et al. (2024) — "Modular RAG: Transforming RAG Systems into
LEGO-like Reconfigurable Frameworks" (arXiv:2407.21059)

---

## Sumário

1. [O que são padrões de fluxo](#1-o-que-são-padrões-de-fluxo)
2. [Padrão Linear](#2-padrão-linear-sequential)
3. [Padrão Condicional](#3-padrão-condicional-conditional)
4. [Padrão Ramificado](#4-padrão-ramificado-branching)
5. [Padrão Iterativo / Loop](#5-padrão-iterativo--loop)
6. [Padrão Adaptativo](#6-padrão-adaptativo-adaptive)
7. [Padrão Multi-Agente](#7-padrão-multi-agente)
8. [Tabela comparativa geral](#8-tabela-comparativa-geral)
9. [Regras de escolha](#9-regras-de-escolha)
10. [Status no BuscaAI](#10-status-no-buscaai)

---

## 1. O que são padrões de fluxo

No Modular RAG, o pipeline é modelado como um **grafo computacional** onde:
- **Nós** = módulos (pré-filtro, retrieval, reranker, geração, juiz...)
- **Arestas** = fluxo de dados e controle entre módulos

Os padrões de fluxo descrevem a **topologia desse grafo** — como os módulos
se conectam e se controlam mutuamente.

```
Gao et al. (2024) identificam 4 padrões canônicos:
  1. Linear      → grafo acíclico direto (DAG simples)
  2. Condicional → arestas condicionais (if-then)
  3. Ramificado  → múltiplos nós em paralelo + fusão
  4. Loop/Iterativo → ciclos controlados por módulo Juiz

A literatura de 2025 adiciona dois padrões emergentes:
  5. Adaptativo  → LLM controla o próprio fluxo via tokens
  6. Multi-Agente → múltiplos LLMs com papéis especializados
```

A orquestração no BuscaAI é feita via **LangGraph StateGraph**,
que suporta todos os 6 padrões nativamente.

---

## 2. Padrão Linear (Sequential)

### O que é

Módulos executam em **sequência fixa**. A saída de cada módulo é a entrada
do próximo. Sem ramificações, sem loops. A estrutura mais simples do Modular RAG.

### Fluxo

```
query
  ↓
pré-filtro (BM25)
  ↓
retrieval (busca híbrida)
  ↓
reranker (cross-encoder)
  ↓
geração (LLM)
  ↓
cache (salva resultado)
  ↓
resposta
```

### Implementação LangGraph

```python
from langgraph.graph import StateGraph
from typing import TypedDict

class RAGState(TypedDict):
    query:     str
    candidatos: list
    chunks:    list
    resposta:  str

graph = StateGraph(RAGState)

graph.add_node("prefiltro",  prefiltro_fn)
graph.add_node("retrieval",  retrieval_fn)
graph.add_node("reranker",   reranker_fn)
graph.add_node("geracao",    geracao_fn)
graph.add_node("cache",      cache_fn)

graph.add_edge("prefiltro", "retrieval")
graph.add_edge("retrieval", "reranker")
graph.add_edge("reranker",  "geracao")
graph.add_edge("geracao",   "cache")

graph.set_entry_point("prefiltro")
pipeline = graph.compile()
```

### Métricas típicas

```
Latência:      ~200–600ms (sem LLM) / ~800ms–2s (com LLM)
Custo/query:   baixo — 1 embedding + 1 reranker + 1 LLM
Qualidade:     ★★★☆☆ — boa para queries diretas, limitada em multi-hop
Complexidade:  ★☆☆☆☆ — mais simples de implementar e debugar
```

### Pontos positivos

- Fácil de debugar — trace linear, erro fácil de localizar
- Determinístico — mesma query = mesmo resultado
- Latência previsível — sem variação por tipo de query
- Ideal para produção estável e bem definida

### Pontos negativos

- Sem adaptação por tipo de query
- Custo igual para queries simples e complexas
- Sem correção de erros no pipeline
- Falha em queries multi-hop que requerem múltiplas buscas

### Exemplos na literatura

- Advanced RAG (padrão de mercado)
- LangChain LCEL pipeline
- LlamaIndex QueryEngine
- **BuscaAI default (MVP)**

### Casos de uso indicados

- Chatbot de suporte ao cliente
- Busca corporativa interna
- FAQ automatizado
- MVP e POC
- Casos onde latência é crítica

---

## 3. Padrão Condicional (Conditional)

### O que é

Um **router** examina a query e seleciona dinamicamente entre pipelines
alternativos. Diferente do ramificado: seleciona **um** caminho, não executa todos.
Base do Adaptive RAG (Jeong et al. 2024).

### Fluxo

```
query
  ↓
[router — classifica query]
  ↓
  ├── simples   → LLM direto (sem retrieval)
  ├── média     → RAG padrão (retrieval + geração)
  ├── complexa  → RAG multi-hop (decomposição + múltiplos retrievals)
  ├── estrutural → SQL direto (dados estruturados)
  └── recente   → busca web (informações atuais)
```

### Tipos de router

```
1. Heurístico (~$0, <5ms):
   if len(query) < 20 and not KEYWORDS_RAG:
       return "llm_direto"

2. Classificador LLM (~$0.001, ~200ms):
   "Classifique: simples/média/complexa. Query: {query}"
   → Groq Llama 3.1 8B (mais barato)

3. Embedding + KNN (~$0, ~20ms):
   modelo sklearn treinado com exemplos de cada categoria
```

### Implementação LangGraph

```python
def router(state: RAGState) -> str:
    query = state["query"]
    if len(query.split()) < 8 and not any(k in query for k in KEYWORDS):
        return "llm_direto"
    elif any(k in query for k in MULTI_HOP_KEYWORDS):
        return "multi_hop"
    else:
        return "rag_padrao"

graph.add_conditional_edges(
    "router",
    router,
    {
        "llm_direto":  "geracao_direta",
        "rag_padrao":  "retrieval",
        "multi_hop":   "decomposicao",
    }
)
```

### Métricas típicas

```
Latência:      variável (5ms para llm_direto, 600ms para rag_padrao)
Custo/query:   baixo-médio — economia de 60–80% vs sempre usar RAG completo
Qualidade:     ★★★★☆ — melhor que linear por usar pipeline certo
Complexidade:  ★★★☆☆ — requer manutenção das regras de roteamento
```

### Pontos positivos

- Economiza 60–80% de custo de LLM em produção
- Queries simples respondem em milissegundos
- Cada sub-pipeline otimizado para seu tipo de query
- Base do Adaptive RAG — estado da arte em eficiência

### Pontos negativos

- Erro de classificação → pipeline completamente errado
- Manutenção das regras de roteamento exige curadoria
- Difícil definir fronteiras entre categorias
- Router LLM adiciona custo e latência

### Exemplos na literatura

- **Adaptive RAG** (Jeong et al. 2024, NAACL)
- AT-RAG — topic-aware routing
- MAO-ARAG — planner com RL
- LangGraph conditional_edges
- **BuscaAI routing (MVP parcial)**

### Casos de uso indicados

- Chatbots com queries muito variadas
- Múltiplas fontes de dados (vetorial + SQL + web)
- Otimização de custo em produção
- Sistemas com SLA de latência variável por tipo

---

## 4. Padrão Ramificado (Branching)

### O que é

Múltiplas buscas executam **em paralelo** (variações da query, múltiplos índices
ou estratégias distintas). Resultados são **fundidos com RRF**.

Diferença fundamental do condicional:
- Condicional: seleciona **UM** caminho
- Ramificado: executa **TODOS** e funde

### Sub-tipos

```
A. Pré-Retrieval Branching (Multi-Query):
   query → expande em N variações → N retrievals paralelos → RRF
   Exemplo: RAG Fusion

B. Pós-Retrieval Branching (por documento):
   query → retrieval → N gerações (uma por chunk) → ensemble
   Exemplo: REPLUG

C. Multi-Index Retrieval:
   query → busca em índice_1, índice_2, índice_3 em paralelo → RRF
   Exemplo: Multi-Index RAG

D. Estratégias paralelas:
   query → busca densa + busca esparsa → RRF
   Exemplo: Hybrid Search (já no BuscaAI)
```

### Fluxo (RAG Fusion)

```
query
  ↓
[expansão de query — LLM gera N variações]
  ↓
  ├──→ retrieval(variação_1) ──→ ranking_1
  ├──→ retrieval(variação_2) ──→ ranking_2
  └──→ retrieval(variação_3) ──→ ranking_3
                                    ↓
                              [RRF fusão]
                                    ↓
                               top-K chunks
                                    ↓
                              reranker + geração
```

### Implementação LangGraph

```python
import asyncio

async def retrieval_paralelo(state: RAGState) -> RAGState:
    variacoes = state["variacoes_query"]

    # executa N retrievals em paralelo
    tasks = [retrieval_fn(v) for v in variacoes]
    rankings = await asyncio.gather(*tasks)

    # funde com RRF
    state["chunks"] = rrf_fusion(rankings, k=60)
    return state

graph.add_node("expande_query",   expande_fn)
graph.add_node("retrieval_multi", retrieval_paralelo)
graph.add_node("reranker",        reranker_fn)
graph.add_node("geracao",         geracao_fn)
```

### Métricas típicas

```
Latência:      paralelo ≈ 1 retrieval + overhead (não N × retrieval)
Custo/query:   médio — N embeddings de query + fusão
Qualidade:     ★★★★☆ — recall significativamente maior
Complexidade:  ★★★☆☆ — fusão adiciona camada de lógica
```

### Pontos positivos

- Recall@5 significativamente maior que busca simples
- Robusto a vocabulary mismatch (usuário usa vocabulário diferente dos docs)
- Paralelismo reduz latência do caso N× serial
- Captura múltiplas perspectivas da mesma query

### Pontos negativos

- Custo N× de embedding de query (N variações)
- Fusão pode introduzir ruído se variações forem ruins
- LLM de expansão pode gerar variações não relevantes
- Mais difícil de debugar que linear

### Exemplos na literatura

- **RAG Fusion** (Shi et al. 2024)
- **REPLUG** — geração por documento com ensemble
- Multi-Query RAG (LangChain)
- RT-RAG — árvore de sub-queries (2025)
- ComposeRAG — módulos componíveis

### Casos de uso indicados

- Domínios com vocabulário muito variado (jurídico, médico)
- Usuários com linguagem diferente dos documentos
- Bases com múltiplas fontes heterogêneas
- Casos onde recall é mais crítico que custo

---

## 5. Padrão Iterativo / Loop

### O que é

Retrieval e geração se **retroalimentam** em múltiplos ciclos. Um módulo **Juiz**
controla quando parar. Cada iteração usa o output anterior para refinar a busca.

### Sub-tipos

```
A. Iterativo fixo (N iterações):
   loop sempre executa exatamente N vezes
   Mais previsível em custo e latência

B. Iterativo adaptativo (para quando satisfeito):
   Juiz avalia qualidade e decide continuar ou parar
   ITER-RETGEN, IRCoT

C. Recursivo (RAPTOR):
   chunks → LLM resume → resumos → LLM resume... (árvore de abstração)
   Não é query-time — ocorre na indexação

D. Reflexivo com tokens (Self-RAG):
   LLM gera reflection tokens em cada passo
   [RETRIEVE], [ISREL], [ISSUP], [ISUSE]
```

### Fluxo (iterativo adaptativo)

```
query
  ↓
retrieval (round 1)
  ↓
geração parcial (round 1)
  ↓
[juiz — resposta satisfatória?]
  ├── sim → resposta final
  └── não → query refinada com contexto parcial
               ↓
            retrieval (round 2) ← usa geração anterior como contexto
               ↓
            geração parcial (round 2)
               ↓
            [juiz] → (itera até N máximo ou satisfeito)
```

### Critério de parada

```python
class JuizRAG:
    def __init__(self, max_iteracoes: int = 3, threshold: float = 0.8):
        self.max_iter = max_iteracoes
        self.threshold = threshold

    def deve_continuar(self, state: RAGState) -> bool:
        if state["iteracao"] >= self.max_iter:
            return False     # critério de segurança

        score = self.avaliar_resposta(state["resposta_parcial"])
        return score < self.threshold   # continua se insatisfatório
```

### Métricas típicas

```
Latência:      2–4s por iteração × N iterações (imprevisível)
Custo/query:   alto — N LLM calls + N retrievals
Qualidade:     ★★★★★ — melhor para multi-hop
Complexidade:  ★★★★☆ — critério de parada é crítico
```

### Pontos positivos

- Resolve queries que precisam de múltiplos fatos encadeados
- Cada iteração usa evidências acumuladas das anteriores
- Detecta quando a resposta é insatisfatória e tenta novamente
- Base de CRAG, Self-RAG, ITER-RETGEN — todos provados em benchmarks

### Pontos negativos

- Custo de múltiplas LLM calls (3–5× do linear)
- Latência alta e imprevisível
- Risco de loop infinito sem critério de parada robusto
- Critério de parada do Juiz é difícil de calibrar

### Exemplos na literatura

- **Self-RAG** (Asai et al. 2024, ICLR) — reflection tokens
- **ITER-RETGEN** — iteração retrieval-geração-retrieval
- **CRAG** (Yan et al. 2024) — corrective retrieval loop
- **RAPTOR** (Sarthi et al. 2024, ICLR) — loop de resumo recursivo
- **IRCoT** — Interleaving Retrieval Chain-of-Thought
- **RT-RAG** (2025) — reasoning tree com traversal bottom-up

### Casos de uso indicados

- Perguntas multi-hop ("quem fundou a empresa que adquiriu X?")
- Análise científica profunda
- Saúde — diagnóstico diferencial
- Jurídico — análise de precedentes encadeados
- Pesquisa que requer síntese de múltiplas fontes

---

## 6. Padrão Adaptativo (Adaptive)

### O que é

O **LLM controla ativamente o próprio fluxo** — decide quando buscar, o que buscar
e quando parar, usando tokens especiais (Self-RAG) ou raciocínio explícito (ReAct, FLARE).
É o padrão de maior qualidade e maior custo.

### Reflection Tokens (Self-RAG)

```
[RETRIEVE]   → deve buscar mais informações? (sim/não)
[ISREL]      → este chunk é relevante para a query? (relevante/irrelevante)
[ISSUP]      → a resposta é suportada pelos chunks? (totalmente/parcialmente/não)
[ISUSE]      → a resposta é útil para o usuário? (5/4/3/2/1)
[ISCON]      → a resposta é consistente internamente? (sim/não)
```

### Fluxo (Self-RAG)

```
query
  ↓
LLM: "preciso buscar?" → [RETRIEVE=sim]
  ↓
busca documentos
  ↓
LLM avalia chunk 1: [ISREL=relevante]
LLM avalia chunk 2: [ISREL=irrelevante] → descarta
  ↓
LLM gera resposta parcial
  ↓
LLM: [ISSUP=totalmente] [ISUSE=5] → satisfeito, retorna
OU
LLM: [ISSUP=parcialmente] → [RETRIEVE=sim] novamente (loop)
```

### Fluxo (FLARE — Forward-Looking Active Retrieval)

```
query
  ↓
LLM começa a gerar token a token
  ↓
se token de baixa confiança detectado:
  → pausa geração
  → gera query a partir do contexto atual
  → busca documentos relevantes
  → retoma geração com novo contexto
  ↓
resposta final com múltiplas buscas interleaved
```

### Métricas típicas

```
Latência:      2–5s (4–8 LLM calls em média)
Custo/query:   muito alto — 4–8× do linear
Qualidade:     ★★★★★ — máxima qualidade disponível
Complexidade:  ★★★★☆ — requer LLM fine-tuned para Self-RAG
```

### Pontos positivos

- Máxima qualidade de resposta
- Sabe quando não sabe (não alucina por falta de contexto)
- Auto-avaliação integrada de fidelidade e utilidade
- Transparência do raciocínio via reflection tokens

### Pontos negativos

- 4–8 LLM calls por query — custo proibitivo em escala
- Self-RAG requer modelo fine-tuned nos reflection tokens
- Comportamento emergente difícil de prever e controlar
- Latência inaceitável para aplicações em tempo real

### Exemplos na literatura

- **Self-RAG** (Asai et al. 2024, ICLR)
- **FLARE** — Forward-Looking Active Retrieval
- **Active RAG** — retrieval proativo
- **IRCoT** — Chain-of-Thought interleaved com retrieval
- **CyberRAG** — loop Retrieval-and-Reason com confiança

### Casos de uso indicados

- Saúde missão crítica (diagnóstico, prescrição)
- Jurídico de alto impacto (contratos, litígios)
- Volume baixo onde qualidade > custo
- Aplicações onde alucinação é inaceitável
- Pesquisa científica e análise de compliance

---

## 7. Padrão Multi-Agente

### O que é

Múltiplos agentes LLM com **papéis especializados** colaboram para resolver
a query. Um **Planner** decompõe a tarefa e orquestra **Executor Agents**
que executam operações específicas (retrieval, SQL, cálculo, reranking, sumarização).

### Arquitetura

```
query
  ↓
[Planner Agent]
  decompõe em sub-tarefas
  seleciona agentes necessários
  define ordem de execução
  ↓
  ├── [Agente Retrieval]   → busca vetorial
  ├── [Agente SQL]         → consulta banco estruturado
  ├── [Agente Reranker]    → reordena candidatos
  ├── [Agente Extractor]   → extrai fatos relevantes
  └── [Agente Summarizer]  → resume evidências longas
  ↓
[Síntese / QA Agent]
  combina evidências de todos os agentes
  gera resposta final coerente
  ↓
resposta
```

### Variantes

```
MA-RAG (2025):
  Planner + Extractor + QA Agent
  Evita context overflow em multi-hop via sumarização por passo

MAO-ARAG (2025):
  Planner treinado com Reinforcement Learning
  Minimiza custo (tokens + latência + API calls)
  ao mesmo tempo que maximiza qualidade

ComposeRAG (2025):
  Módulos independentes intercambiáveis
  Self-reflection para revisar decomposição
  Transparência total do raciocínio

LangGraph Multi-Agent:
  Cada agente é um subgrafo LangGraph
  Comunicação via mensagens no estado compartilhado
```

### Implementação LangGraph

```python
# Subgrafos para cada agente especializado
retrieval_agent = create_retrieval_subgraph()
sql_agent       = create_sql_subgraph()
synth_agent     = create_synthesis_subgraph()

# Grafo principal com planner
main_graph = StateGraph(MultiAgentState)
main_graph.add_node("planner",   planner_fn)
main_graph.add_node("retrieval", retrieval_agent)
main_graph.add_node("sql",       sql_agent)
main_graph.add_node("synthesis", synth_agent)

# Planner decide quais agentes acionar
main_graph.add_conditional_edges(
    "planner",
    route_to_agents,
    {"retrieval": "retrieval", "sql": "sql"}
)
main_graph.add_edge("retrieval", "synthesis")
main_graph.add_edge("sql",       "synthesis")
```

### Métricas típicas

```
Latência:      3–15s (5–20 LLM calls)
Custo/query:   muito alto — multiplicado pelo número de agentes
Qualidade:     ★★★★★ — melhor para análises complexas multi-fonte
Complexidade:  ★★★★★ — coordenação de agentes é o maior desafio
```

### Pontos positivos

- Máxima flexibilidade — cada agente especializado em sua tarefa
- Paralelismo entre agentes reduz latência vs serial
- Escalável — adicionar novo agente sem alterar os existentes
- MAO-ARAG otimiza automaticamente o workflow via RL

### Pontos negativos

- 5–20 LLM calls por query — custo muito alto
- Coordenação complexa — estado compartilhado precisa ser bem projetado
- Comportamento emergente difícil de prever
- Debugging complexo — qual agente causou o erro?

### Exemplos na literatura

- **MA-RAG** (2025) — Multi-Agent RAG
- **MAO-ARAG** (2025) — Multi-Agent Orchestration com RL
- **ComposeRAG** (2025) — composable multi-hop RAG
- **Agentic RAG** (Ravuru 2024)
- **LangGraph multi-agent** — framework de implementação

### Casos de uso indicados

- Análise de dados multi-fonte (SQL + vetorial + web)
- Relatórios executivos automatizados
- Copilot para analistas financeiros ou jurídicos
- Sistemas onde cada tipo de query precisa de specialist
- Volume baixo com budget alto por query

---

## 8. Tabela comparativa geral

| Padrão | Origem | Fluxo | Custo/query | Latência | Qualidade | Complexidade | Status BuscaAI |
|---|---|---|---|---|---|---|---|
| **Linear** | Lewis 2020 | A→B→C→D | baixo | ~500ms | ★★★☆☆ | ★☆☆☆☆ | **padrão MVP** |
| **Condicional** | Jeong 2024 | router→[A\|B\|C] | baixo-médio | variável | ★★★★☆ | ★★★☆☆ | **parcial MVP** |
| **Ramificado** | Gao 2024 | A→[B₁‖B₂‖B₃]→RRF | médio | paralelo | ★★★★☆ | ★★★☆☆ | roadmap v1.x |
| **Iterativo** | ITER-RETGEN | A→B→juiz→↩ | alto | 2–4s | ★★★★★ | ★★★★☆ | roadmap |
| **Adaptativo** | Asai 2024 | [RETRIEVE]?→loop | muito alto | 2–5s | ★★★★★ | ★★★★☆ | roadmap premium |
| **Multi-Agente** | MA-RAG 2025 | planner→[ag₁‖ag₂]→síntese | muito alto | 3–15s | ★★★★★ | ★★★★★ | experimental |

---

## 9. Regras de escolha

```
TIPO DE QUERY              PADRÃO RECOMENDADO       RAZÃO
──────────────────────────────────────────────────────────────────
Simples e direta           Linear                   Custo mínimo, latência baixa
Variadas (simples + complexas) Condicional          Economiza 60-80% no custo
Vocabulário variado        Ramificado (RAG Fusion)  Recall alto
Multi-hop encadeada        Iterativo                Refinamento progressivo
Missão crítica (saúde/jur) Adaptativo               Máxima fidelidade
Multi-fonte + análise      Multi-agente             Especialização por fonte

RESTRIÇÃO                  EXCLUI
───────────────────────────────────────────
Latência < 1s              Iterativo, Adaptativo, Multi-agente
Custo < $0.01/query        Adaptativo, Multi-agente
Sem GPU local              Não afeta (todos suportam API)
Previsibilidade necessária Linear (único determinístico)
Volume > 100k queries/mês  Evitar Adaptativo e Multi-agente
```

---

## 10. Status no BuscaAI

```
PADRÃO         STATUS          CONFIGURAÇÃO
──────────────────────────────────────────────────────────────────────
Linear         ✓ MVP           padrão — usa hybrid search + reranker
Condicional    ✓ MVP parcial   routing.enabled = True no settings
                               classifica: llm_direto | rag_padrao | multi_hop
Ramificado     → roadmap v1.x  LLM_FEATURES.query_expansion = True
                               gera N variações + retrieval paralelo + RRF
Iterativo      → roadmap       modo iterativo — max_iterations configurável
                               Judge module avalia qualidade por turno
Adaptativo     → premium       Self-RAG mode — requer LLM fine-tuned
                               custo estimado: 4-8× do linear
Multi-Agente   → experimental  LangGraph multi-agent subgraphs
                               planner + executor agents especializados
──────────────────────────────────────────────────────────────────────
```

### Configuração do padrão no BuscaAI

```python
# rag_settings.py

# PADRÃO LINEAR (default)
RETRIEVAL = {
    "strategy":   "hybrid",
    "top_k":      50,
    "reranker":   True,
    "final_top_k": 5,
}

# ADICIONAR CONDICIONAL
LLM = {
    "routing": {
        "enabled": True,
        "simple":  "groq",      # queries simples → modelo barato
        "medium":  "openai",    # queries médias
        "complex": "anthropic", # queries complexas
    }
}

# ADICIONAR RAMIFICADO (v1.x)
LLM_FEATURES = {
    "query_expansion": {
        "enabled":   True,
        "n_variacoes": 3,       # gera 3 variações da query
        "provider":  "groq",    # usa modelo barato para expandir
    }
}

# ADICIONAR ITERATIVO (roadmap)
RETRIEVAL = {
    "strategy":     "hybrid",
    "iterative":    True,
    "max_iter":     3,
    "iter_threshold": 0.8,  # para quando faithfulness ≥ 0.8
}
```

---

## Referências

- **Gao et al. (2024)** — "Modular RAG: Transforming RAG Systems into LEGO-like Reconfigurable Frameworks" (arXiv:2407.21059)
- **Jeong et al. (2024)** — "Adaptive-RAG: Learning to Adapt Retrieval-Augmented Large Language Models through Question Complexity" (NAACL)
- **Asai et al. (2024)** — "Self-RAG: Learning to Retrieve, Generate, and Critique through Self-Reflection" (ICLR)
- **Yan et al. (2024)** — "Corrective Retrieval Augmented Generation" (arXiv:2401.15884)
- **Sarthi et al. (2024)** — "RAPTOR: Recursive Abstractive Processing for Tree-Organized Retrieval" (ICLR)
- **OpenRAG (2024)** — "Modular RAG and RAG Flow: Part II" (Medium)
- **MA-RAG (2025)** — "Multi-Agent Retrieval-Augmented Generation via Collaborative Chain-of-Thought" (arXiv:2505.20096)
- **ComposeRAG (2025)** — "A Modular and Composable RAG" (arXiv:2506.00232)
- **PromptLayer (2024)** — "Modular RAG: LEGO-like Reconfigurable Frameworks"
