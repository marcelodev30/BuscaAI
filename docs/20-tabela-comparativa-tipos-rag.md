# Tabela Comparativa — Tipos de RAG

Todos os paradigmas e técnicas reconhecidos pela literatura 2024–2026
como RAG ou extensões de RAG, com métricas de precisão, custo e casos de uso.

---

## O que conta como RAG segundo o estado da arte

De acordo com Gao et al. (2024) e os surveys mais recentes, RAG exige três elementos obrigatórios:

```
1. Recuperação  — buscar em fonte externa
2. Augmentação  — combinar o que foi buscado com a query
3. Geração      — LLM gera a resposta usando o contexto recuperado
```

A taxonomia canônica reconhece uma única árvore genealógica:

```
Naive RAG  ⊂  Advanced RAG  ⊂  Modular RAG
```

Extensões formalmente aceitas: GraphRAG, Agentic RAG, Multimodal RAG, Hybrid RAG.

Técnicas como HyDE, CRAG, Self-RAG, RAPTOR, RAG Fusion e reranking são
**módulos dentro do Modular RAG** — estratégias de pré-retrieval, retrieval
ou pós-retrieval, não paradigmas independentes.

---

## Tabela comparativa

| Tipo de RAG | Latência/query | Custo/query | Recall@5 | Precision@5 | Faithfulness | Complexidade | Casos de uso |
|---|---|---|---|---|---|---|---|
| **Naive RAG** | ~200ms | baixo (só embedding) | 0.45 | 0.40 | 0.55 | ★★☆☆☆ | POC, demos, validação |
| **Advanced RAG** | ~600ms | médio (embed + reranker) | 0.78 | 0.74 | 0.80 | ★★★☆☆ | Produção geral, suporte |
| **Modular RAG** | ~600ms | médio (depende da config) | 0.82 | 0.80 | 0.83 | ★★★★☆ | Base do BuscaAI, todos os casos |
| **Adaptive RAG (leve)** | ~400ms | baixo–médio | 0.80 | 0.78 | 0.81 | ★★★☆☆ | Queries variadas, economia de custo |
| **HyDE** | +500ms | médio (+1 LLM call) | 0.75 | 0.72 | 0.78 | ★★☆☆☆ | Queries vagas, texto denso |
| **Self-RAG** | 2–5s | muito alto (4–8 LLM calls) | 0.90 | 0.88 | 0.93 | ★★★★★ | Saúde, jurídico crítico |
| **CRAG** | 2–4s | alto (avaliador + busca web) | 0.88 | 0.85 | 0.88 | ★★★★☆ | Base incompleta, eventos recentes |
| **RAG Fusion** | 1–2s | médio (N × retrieval) | 0.85 | 0.70 | 0.80 | ★★★☆☆ | Vocabulário variado, jurídico |
| **RAPTOR** | ~800ms | alto (ingestão cara via LLM) | 0.86 | 0.82 | 0.84 | ★★★★☆ | Queries gerais + específicas |
| **Multi-Vector RAG** | ~500ms | médio (N × embed na ingestão) | 0.84 | 0.80 | 0.82 | ★★★☆☆ | Docs longos, alta cobertura |
| **GraphRAG** | 1–3s | muito alto (LLM por chunk) | 0.92 | 0.90 | 0.94 | ★★★★★ | Base estática, queries relacionais |
| **Agentic RAG** | 3–15s | muito alto (5–20 LLM calls) | 0.94 | 0.90 | 0.91 | ★★★★★ | Análise complexa, multi-fonte |
| **Long Context RAG** | 2–8s | muito alto (tokens = base toda) | 0.98 | 0.88 | 0.85 | ★☆☆☆☆ | Bases pequenas, recall crítico |
| **Speculative RAG** | 1–3s | alto (2 LLM passes) | 0.80 | 0.76 | 0.82 | ★★★★☆ | LLM com conhecimento forte |
| **Multimodal RAG** | 1–4s | muito alto (modelo visual) | 0.83 | 0.78 | 0.80 | ★★★★★ | Laudos, manuais técnicos |

> Métricas: valores médios estimados com base em benchmarks publicados 2024–2026.
> Recall@5 e Precision@5 referem-se ao retrieval. Faithfulness é métrica RAGAS de geração.

---

## Classificação por categoria

### Paradigmas canônicos (Gao et al. 2024)

| Paradigma | Posição na taxonomia |
|---|---|
| Naive RAG | fundacional — indexação + retrieval + geração |
| Advanced RAG | adiciona pré e pós-retrieval ao Naive |
| Modular RAG | grafo configurável de módulos plugáveis |

### Extensões aceitas pela literatura

| Extensão | O que adiciona |
|---|---|
| GraphRAG | retrieval em grafo de entidades e relações |
| Agentic RAG | agente LLM controla dinamicamente o retrieval |
| Multimodal RAG | retrieval em texto, imagem e tabela |
| Hybrid RAG | fusão de retrieval lexical + semântico (BM25 + denso + RRF) |

### Técnicas dentro do Modular RAG

| Técnica | Onde atua no pipeline |
|---|---|
| HyDE | pré-retrieval — enriquece o embedding da query |
| RAG Fusion | retrieval — múltiplas variações + RRF |
| Self-RAG | orquestração — LLM avalia e decide quando buscar |
| CRAG | pós-retrieval — avalia qualidade e corrige se necessário |
| RAPTOR | indexação — árvore hierárquica de resumos |
| Multi-Vector | indexação — múltiplas representações por documento |
| Speculative RAG | geração — gera hipótese antes de verificar |

---

## O que não é RAG

| Técnica | Por que não é RAG |
|---|---|
| Fine-tuning | conhecimento vira paramétrico, sem retrieval em inferência |
| Long context sem retrieval | sem etapa de busca — é long-context inference |
| In-context learning puro | sem fonte externa, sem índice |
| Prompt engineering | sem augmentation com dados externos |
| Tool use não-knowledge | agente usa calculadora ou API, sem recuperar conhecimento |

---

## Referências

- Gao, Y. et al. (2024). Retrieval-Augmented Generation for Large Language Models: A Survey. arXiv:2312.10997
- Gao, Y. et al. (2024). Modular RAG: Transforming RAG Systems into LEGO-like Reconfigurable Frameworks. arXiv:2407.21059
- Brown, A. et al. (2025). A Systematic Literature Review of RAG: Techniques, Metrics, and Challenges. arXiv:2508.06401
- Singh, A. et al. (2025). Agentic Retrieval-Augmented Generation: A Survey on Agentic RAG. arXiv:2501.09136
- Edge, D. et al. (2024). From Local to Global: A Graph RAG Approach. Microsoft Research
