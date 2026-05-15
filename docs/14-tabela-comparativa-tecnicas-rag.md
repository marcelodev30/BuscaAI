# Tabela Comparativa de Técnicas de RAG

Este documento apresenta uma comparação sistemática das principais técnicas de RAG descritas na literatura de 2024–2026. Para cada técnica, são apresentadas: a ideia central, os pontos fortes, as limitações, o custo computacional, o caso de uso indicado e a referência primária.

A tabela final consolida tudo para consulta rápida.

---

## Técnicas comparadas

### Naive RAG

**Ideia central:** pipeline linear de três etapas — indexação, recuperação por similaridade vetorial, geração pelo LLM. Sem otimizações em nenhuma etapa.

**Pontos fortes:**
- Simples de implementar.
- Pouca infraestrutura necessária.
- Ponto de partida natural para qualquer projeto.

**Limitações:**
- Baixa precisão em queries ambíguas ou com termos exatos.
- Sofre com o fenômeno "Lost in the Middle" quando muitos chunks são recuperados.
- Sem reranking, traz ruído junto com resultados relevantes.
- Não diferencia tipos de query.

**Custo:** baixo. Uma chamada de embedding por query + uma busca + uma chamada de LLM.

**Caso de uso indicado:** protótipos, provas de conceito, bases pequenas, situações onde os usuários fazem queries previsíveis e bem formadas.

**Referência:** Lewis et al. (2020).

---

### Advanced RAG

**Ideia central:** adiciona otimizações ao Naive RAG nas etapas de pré-retrieval (query rewriting, HyDE, query expansion) e pós-retrieval (reranking, compressão de contexto).

**Pontos fortes:**
- Aumento significativo de precisão e recall em relação ao Naive RAG.
- O reranker é o componente isolado de maior ganho documentado.
- Ainda é um pipeline linear, fácil de raciocinar.

**Limitações:**
- Adiciona latência (reranker pode custar 100–200ms para 30 candidatos).
- Query expansion via LLM aumenta custo de tokens.
- Continua sendo um pipeline fixo — não se adapta à query.

**Custo:** médio. Adiciona uma chamada de reranker (e opcionalmente uma de LLM para expansion) por query.

**Caso de uso indicado:** produção em bases de tamanho médio com necessidade de qualidade superior ao Naive RAG, sem o orçamento ou complexidade do Modular RAG completo.

**Referência:** Gao et al. (2024) — "Retrieval-Augmented Generation for Large Language Models: A Survey".

---

### Modular RAG

**Ideia central:** decompõe o pipeline em módulos independentes e reconfiguráveis (estilo LEGO). Cada módulo — retriever, reranker, gerador, validador, roteador — pode ser trocado independentemente.

**Pontos fortes:**
- Flexibilidade máxima para adaptar a casos de uso diferentes.
- Manutenibilidade — trocar um módulo não quebra os outros.
- Permite "hot-swap" de modelos conforme novos lançamentos.
- Estado da arte atual segundo a literatura consolidada.

**Limitações:**
- Complexidade de design e de operação maior.
- Exige boa orquestração (LangGraph, DSPy, ou similar).
- Curva de aprendizado para desenvolvedores não familiarizados.

**Custo:** depende dos módulos ativados. A modularidade em si não custa nada; o custo vem das escolhas dentro dela.

**Caso de uso indicado:** produção em escala, frameworks reutilizáveis, sistemas que precisam evoluir ao longo do tempo, plataformas multi-tenant.

**Referência:** Gao et al. (2024) — "Modular RAG: Transforming RAG Systems into LEGO-like Reconfigurable Frameworks".

---

### Hybrid RAG (Hybrid Search)

**Ideia central:** combina retrieval lexical (BM25) com retrieval denso, e funde os resultados (geralmente via Reciprocal Rank Fusion).

**Pontos fortes:**
- Captura tanto termo exato (códigos, IDs, jargão) quanto significado semântico.
- Linha de base que consistentemente supera retrieval de método único em benchmarks.
- BM25 supera retrieval denso em domínios técnicos específicos (documentos financeiros, código, identificadores).

**Limitações:**
- Exige manter dois índices (lexical e vetorial).
- Exige gerar dois embeddings por chunk na ingestão.
- A fusão (RRF) tem hiperparâmetros que podem precisar de tuning.

**Custo:** médio. Ingestão mais cara (dois embeddings), busca em paralelo ao retriever lexical.

**Caso de uso indicado:** praticamente todos os casos de produção. É o consenso atual como padrão.

**Referência:** Sharma (2025), Sultania et al. (2024).

---

### Hierarchical RAG (RAPTOR / índice hierárquico)

**Ideia central:** além dos chunks, cria resumos em camadas — resumo de seção, de capítulo, de documento. Na busca, escolhe-se em qual camada buscar conforme a generalidade da query.

**Pontos fortes:**
- Responde bem tanto a perguntas específicas quanto gerais.
- Resolve o problema de "a resposta está espalhada por um documento longo".

**Limitações:**
- Ingestão muito mais cara — exige LLM gerando resumos em múltiplos níveis.
- Manutenção complexa quando os dados mudam (precisa regerar resumos).
- Lógica de roteamento entre níveis adiciona complexidade.

**Custo:** alto na ingestão (LLM para resumos), médio na busca.

**Caso de uso indicado:** bases relativamente estáticas com documentos longos onde a resposta a perguntas gerais não está num único trecho.

**Referência:** Sarthi et al. (2024) — RAPTOR.

---

### Adaptive RAG

**Ideia central:** classificador (geralmente T5 pequeno) determina a complexidade da query antes do retrieval, e roteia entre três estratégias: sem retrieval, single-hop, multi-hop.

**Pontos fortes:**
- Economia de custo — não paga retrieval caro em queries simples.
- Não compromete qualidade em queries complexas.
- Validado experimentalmente: classificador leve iguala baselines sempre-caros com custo substancialmente menor.

**Limitações:**
- Exige treinar e manter o classificador.
- O classificador adiciona uma etapa de latência.
- A precisão do roteamento depende da qualidade do classificador.

**Custo:** baixo extra (classificador é pequeno). O ganho é evitar o custo das estratégias caras quando desnecessárias.

**Caso de uso indicado:** sistemas em produção com volume alto de queries de complexidade variada.

**Referência:** Jeong et al. (2024).

---

### Self-RAG

**Ideia central:** o próprio LLM gera "reflection tokens" especiais que decidem se precisa recuperar mais documentos, se a resposta é boa, e se deve continuar gerando. O LLM vira controlador do processo.

**Pontos fortes:**
- Adapta o retrieval iterativamente à medida que gera a resposta.
- Reduz alucinação ao permitir que o modelo questione as próprias respostas.
- Lida bem com queries multi-step.

**Limitações:**
- Exige LLM treinado especificamente para gerar reflection tokens (ou prompt engineering pesado).
- Múltiplas chamadas de LLM por query → custo alto.
- O mecanismo de auto-reflexão pode levar o sistema a "pensar demais" e gerar saídas que não são realmente sustentadas pelos dados.

**Custo:** alto. Múltiplas chamadas de LLM por query.

**Caso de uso indicado:** QA crítico onde a qualidade vale mais que o custo, casos com queries complexas que se beneficiam de raciocínio iterativo.

**Referência:** Asai et al. (2024).

---

### Corrective RAG (CRAG)

**Ideia central:** um avaliador leve avalia a qualidade dos documentos recuperados. Se confiança baixa, dispara busca web complementar. Se confiança média, refina. Se alta, segue normalmente.

**Pontos fortes:**
- Robusto a falhas do retrieval — não passa lixo para o LLM.
- Integra busca web como fallback automático.
- Reduz alucinação por má fundamentação.

**Limitações:**
- 4 chamadas de LLM por query no scoring, mais possível busca web mais refinamento — custo significativo de tokens.
- Calibração dos limiares (alta/média/baixa confiança) precisa ser feita por base.
- Dependência da disponibilidade e qualidade da busca web.

**Custo:** alto. Avaliador + possível busca externa + refinamento.

**Caso de uso indicado:** bases com cobertura desigual onde a busca web faz sentido como complemento, sistemas críticos onde recuperação ruim é inaceitável.

**Referência:** Yan et al. (2024).

---

### Agentic RAG

**Ideia central:** um agente LLM orquestra o processo de retrieval dinamicamente — escolhe ferramentas, decide quando buscar, quando re-buscar, quando combinar fontes. O retrieval não é uma etapa de pré-processamento; é uma operação dinâmica guiada pelo raciocínio.

**Pontos fortes:**
- Máxima flexibilidade — lida com queries arbitrariamente complexas.
- Combina múltiplas estratégias e fontes conforme necessário.
- Estado da arte atual em sistemas de fronteira.

**Limitações:**
- Custo de tokens muito alto — várias chamadas de LLM por query.
- Latência alta — múltiplos passos sequenciais.
- Complexidade de design e debugging significativa.
- Comportamento menos previsível que pipelines fixos.

**Custo:** muito alto. Cada query pode gerar 5–20 chamadas de LLM.

**Caso de uso indicado:** assistentes de pesquisa, copilots especializados, casos onde qualidade da resposta justifica custo elevado por query.

**Referência:** Ravuru et al. (2024), Lopatina et al. (2026).

---

### GraphRAG

**Ideia central:** extrai entidades e relações dos documentos via LLM e constrói um grafo de conhecimento. Na busca, navega pelas relações em vez de (ou além de) buscar por similaridade.

**Pontos fortes:**
- Responde a queries que exigem navegação por relações ("quais empresas foram adquiridas por X que também investem em Y").
- Detecção de comunidades permite resumos globais do corpus.
- Combina bem com retrieval vetorial em arquiteturas híbridas.

**Limitações:**
- Custo de ingestão proibitivo — uma chamada de LLM por chunk para extração de entidades.
- Manutenção complexa quando dados mudam (recalcular relações).
- Não substitui retrieval vetorial; é complementar para casos específicos.

**Custo:** muito alto na ingestão. Médio na busca, dependendo da complexidade do grafo.

**Caso de uso indicado:** bases onde as relações entre entidades são o cerne das consultas — análise jurídica de cadeia societária, investigação biomédica de interações, due diligence empresarial.

**Referência:** Edge et al. (2024) — Microsoft GraphRAG.

---

## Tabela comparativa consolidada

| Técnica | Custo de Ingestão | Custo por Query | Latência | Complexidade | Ganho de Qualidade vs Naive | Adotada no BuscaAI? |
|---|---|---|---|---|---|---|
| **Naive RAG** | Baixo | Baixo | Baixa | Baixa | — (baseline) | Não — superado |
| **Advanced RAG** | Baixo | Médio | Média | Média | Alto | Parcialmente (reranker) |
| **Modular RAG** | Variável | Variável | Variável | Alta | Alto | **Sim — padrão arquitetural** |
| **Hybrid RAG** | Médio (2 embeddings) | Médio | Média | Média | Alto | **Sim — estratégia de busca padrão** |
| **Hierarchical RAG** | Muito alto | Médio | Média | Alta | Alto em queries gerais | Não — fora do escopo |
| **Adaptive RAG** | Baixo | Variável | Variável | Média | Médio (otimiza custo) | Sim, em forma leve (arestas condicionais) |
| **Self-RAG** | Baixo | Alto | Alta | Alta | Alto | Não — custo de tokens |
| **Corrective RAG (CRAG)** | Baixo | Alto | Alta | Alta | Alto | Não — custo de tokens |
| **Agentic RAG** | Baixo | Muito alto | Muito alta | Muito alta | Muito alto | Não — custo proibitivo |
| **GraphRAG** | Muito alto | Médio | Média | Muito alta | Alto em queries relacionais | Não — custo proibitivo na ingestão |

---

## Posicionamento do BuscaAI

A combinação adotada pelo BuscaAI é deliberadamente conservadora em custo e ambiciosa em arquitetura:

```
Modular RAG (arquitetura)
   ├── Hybrid Retrieval (busca padrão)
   ├── Pré-filtragem léxica (etapa antes da busca)
   ├── Reranker opcional (Advanced RAG)
   └── Adaptive Routing leve (arestas condicionais no LangGraph)
```

A escolha do que **não** incluir como padrão é tão importante quanto a do que incluir. Self-RAG, CRAG, Agentic RAG e GraphRAG ficaram fora do escopo principal por motivos consistentes com a literatura: todos exigem LLM no laço de retrieval ou de ingestão, com custo de tokens incompatível com bases gigantescas e genéricas — o caso de uso central do framework.

Esses recursos podem, em versões futuras do BuscaAI, ser oferecidos como opções configuráveis no settings — Self-RAG e CRAG como modos de busca premium, GraphRAG como módulo opcional para casos de uso com forte componente relacional. Mas como padrão, a combinação atual representa o melhor equilíbrio entre estado da arte e viabilidade econômica documentado na literatura de 2024–2026.

---

## Resumo executivo

A literatura recente é convergente em três pontos:

1. **Modular RAG é o paradigma arquitetural dominante.** Pipelines lineares foram superados; sistemas reconfiguráveis são o padrão.
2. **Hybrid Search é a linha de base de retrieval.** Densa apenas perde para híbrida em praticamente todos os benchmarks.
3. **Reranking é o componente isolado de maior ganho.** Quando o orçamento permite, sempre vale a pena.

E é cautelosa em três outros:

1. **Self-RAG, CRAG e Agentic RAG têm custo alto de tokens** e devem ser adotados consciente das implicações operacionais.
2. **GraphRAG tem custo de ingestão proibitivo** em bases grandes e só compensa quando relações são o cerne da consulta.
3. **Query expansion ajuda em alguns casos e atrapalha em outros** — não deve ser ativada por padrão.

O BuscaAI se posiciona exatamente nesse mapa: adota o consenso, deixa portas abertas para os recursos avançados, e evita os custos proibitivos onde a literatura aponta que não compensam.
