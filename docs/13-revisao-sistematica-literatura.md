# Revisão Sistemática da Literatura: Recuperação de Informação, LLMs e RAG (Estado da Arte 2024–2026)

Este documento sintetiza o estado da arte em Recuperação de Informação (IR), Modelos de Linguagem de Grande Escala (LLMs) e Retrieval-Augmented Generation (RAG) entre 2024 e início de 2026, com foco nas decisões de arquitetura relevantes para o projeto **BuscaAI**.

A revisão está organizada em quatro eixos:

1. Evolução dos paradigmas de RAG
2. Estratégias de recuperação (lexical, densa, híbrida)
3. Aprimoramentos do pipeline (chunking, reranking, query expansion)
4. Arquiteturas modulares e agênticas

---

## 1. A evolução dos paradigmas de RAG

A literatura organiza a evolução do RAG em três grandes paradigmas, conforme a taxonomia consolidada por Gao et al. (2024), em "Retrieval-Augmented Generation for Large Language Models: A Survey", que examina detalhadamente a progressão dos paradigmas, encompassando Naive RAG, Advanced RAG e Modular RAG.

### Naive RAG

O paradigma fundacional, introduzido por Lewis et al. (2020). Consiste em três etapas lineares: indexação, recuperação e geração. Naive RAG enfrenta múltiplos desafios em recuperação, geração e aumentação — entre eles, baixa precisão no retrieval, dificuldade com queries ambíguas e tendência a passar contexto irrelevante para o LLM.

### Advanced RAG

Surge como resposta às limitações do Naive RAG. O paradigma Advanced RAG envolve processamento adicional na pré-recuperação e pós-recuperação. Antes da recuperação, métodos como reescrita de query, roteamento e expansão podem ser usados para alinhar diferenças semânticas entre perguntas e chunks de documentos. Após a recuperação, reranquear o corpus de documentos recuperados pode evitar o fenômeno "Lost in the Middle".

As técnicas centrais que caracterizam Advanced RAG, segundo a literatura recente:

- **Pré-recuperação**: query expansion, query rewriting, HyDE (Hypothetical Document Embeddings).
- **Pós-recuperação**: reranking com cross-encoders, compressão de contexto, fusão de resultados (RRF).

### Modular RAG

Representa o estado da arte atual. Gao et al. (2024), em trabalho subsequente, propõem o framework Modular RAG: examina as limitações do paradigma RAG existente e introduz o framework Modular RAG, que transcende a arquitetura linear tradicional, abraçando um design mais avançado que integra mecanismos de roteamento, escalonamento e fusão.

A literatura caracteriza o Modular RAG como uma decomposição em componentes reconfiguráveis. Ao decompor sistemas RAG complexos em módulos independentes e operadores especializados, facilita um framework altamente reconfigurável. Os três paradigmas mantêm uma relação de herança: Advanced RAG é um caso especial de Modular RAG, enquanto Naive RAG é um caso especial de Advanced RAG.

### A consolidação em 2024–2026

Análises recentes confirmam essa consolidação. Entre 2024 e o final de 2025, RAG amadureceu de pipelines lineares de "recupere-depois-gere" para sistemas modulares e agênticos capazes de planejamento, uso de ferramentas e auto-correção. As três mudanças que definem o estado da arte segundo essa síntese: recuperação híbrida e re-rankeada para superar os limites do vetorial-apenas, raciocínio estruturado via GraphRAG, e laços de controle autônomos (RAG Agêntico) que iterativamente planejam, recuperam e verificam.

---

## 2. Estratégias de recuperação

### Limites do retrieval puramente vetorial

A literatura é convergente em apontar as limitações do retrieval denso isolado. Limitações do retrieval vetorial-apenas (deriva semântica, tensão recall-precisão, lacunas relacionais) impulsionaram a hibridização com retrieval esparso e a adição de re-ranking por cross-encoder para melhorar fundamentação e reduzir alucinações.

Análises de produção identificam um padrão consistente de falha: os tipos de query que sistematicamente falham sob retrieval denso puro seguem um padrão consistente: códigos de erro e identificadores (strings exatas como 0x80070005, INV-2024-00847 ou ENOMEM têm sinal de representação semântica próximo de zero); SKUs de produtos e números de modelo (RTX-4090 e RTX-4070 são semanticamente quase idênticos no espaço de embedding, mas são produtos diferentes).

### BM25 — relevância renovada

Apesar de ser um algoritmo das décadas de 1980-90, BM25 mantém papel central. BM25 permanece altamente competitivo e frequentemente supera os recuperadores neurais sob condições de correspondência lexical: em QA de domínio aberto (Natural Questions), o recall top-1 de BM25 é 22.1%; recuperadores densos (DPR) atingem 48.7%, mas pipelines híbridos chegam a 53.4%.

Um achado contraintuitivo em domínios específicos: BM25 supera o retrieval denso de estado da arte em documentos financeiros, desafiando a suposição comum de que a busca semântica universalmente domina. Esse resultado reforça o argumento contra adotar retrieval denso como única estratégia em frameworks genéricos.

### Busca híbrida como linha de base

A literatura recente é praticamente unânime em recomendar busca híbrida como padrão. Busca híbrida (densa + esparsa) mais re-ranking tornou-se a stack de linha de base, consistentemente superando retrieval de método único em relevância e factualidade em tarefas empresariais de QA e busca.

Em uma ampla gama de benchmarks de retrieval e RAG, o BM25 híbrido consistentemente supera tanto recuperadores apenas-esparsos quanto apenas-densos — frequentemente por margens de dois dígitos em nDCG e MAP.

### Reciprocal Rank Fusion (RRF)

O método dominante de fusão entre buscas densa e esparsa. Top-k denso e top-k BM25 em paralelo. Fusão via RRF (pontuação de busca híbrida usando RRF). O RRF é preferido por não exigir calibração entre escalas de score — ele opera apenas sobre as posições (ranks).

### Modelos esparsos neurais

Uma evolução recente são os modelos esparsos aprendidos (SPLADE, BGE-M3). Modelos como BGE-M3 (lançado em janeiro de 2024) unificam modos densos, esparsos e de interação tardia em um único checkpoint de 550M parâmetros, reduzindo substancialmente a complexidade de infraestrutura para equipes que antes precisavam de três modelos separados.

Há também extensões do próprio BM25. BMX estende o BM25 com similaridade ponderada por entropia e aumentação semântica via paráfrases geradas por LLM, melhorando o nDCG@10 em 1–2 pontos em cenários zero-shot e de contexto longo.

---

## 3. Aprimoramentos do pipeline

### Reranking como componente de maior impacto

Estudos comparativos recentes apontam o reranker como o componente isolado de maior ganho. Um pipeline de dois estágios combinando retrieval híbrido com reranking neural alcança Recall@5 de 0.816 e MRR@3 de 0.605, superando todos os métodos de estágio único por uma grande margem. Reranking é o componente isolado mais impactante.

Há restrições práticas de latência. Um cross-encoder sobre 30 candidatos custa aproximadamente 100–200ms no total. O mesmo modelo aplicado a 200 candidatos estoura o orçamento de latência em 5–10x. A regra prática: ajuste o recall do primeiro estágio para que não seja necessário reranquear mais de 50 candidatos. Se você precisa reranquear mais de 200 para obter precisão aceitável, o retrieval do primeiro estágio está quebrado.

Alternativas ao cross-encoder também emergem. A interação tardia estilo ColBERT oferece uma alternativa que fica entre bi-encoders e cross-encoders. O mecanismo MaxSim calcula relevância como a soma das similaridades máximas por token de query sobre os tokens do documento — preservando alinhamento em nível de frase enquanto permite que representações de documentos sejam pré-computadas.

### Query Expansion — ganhos seletivos

A literatura mais recente é cautelosa com query expansion. Métodos de expansão de query (HyDE, multi-query) e retrieval adaptativo fornecem benefício limitado para queries numéricas precisas, enquanto retrieval contextual produz ganhos consistentes. O recomendado é tratar a query expansion como recurso opcional, configurável por caso de uso, não como padrão.

### Chunking

Apesar de aparentemente trivial, a literatura aponta o chunking como fator que define a qualidade global do sistema. Estratégias documentadas:

- **Fixed-size chunking** — divisão por contagem de tokens.
- **Recursive character chunking** — divisão respeitando hierarquia de separadores (parágrafo, linha, frase).
- **Semantic chunking** — divisão por mudanças de significado, detectadas pela distância entre embeddings de frases adjacentes.
- **Structure-aware chunking** — divisão por estrutura nativa do documento (markdown, código, HTML).

---

## 4. Arquiteturas modulares e agênticas

### Modular RAG como padrão arquitetural

A defesa do Modular RAG como padrão é consistente em fontes recentes. Modular RAG reformula o pipeline como componentes estilo LEGO (recuperadores, rankeadores, geradores, validadores, roteadores) que podem ser reconfigurados por tarefa, permitindo manutenibilidade e troca a quente conforme os modelos melhoram.

A justificativa prática: desacopla a arquitetura monolítica em componentes que se otimizam independentemente, incluindo pré-processamento de query, recuperadores, rerankers e geradores. Essa arquitetura permite que desenvolvedores substituam ou atualizem módulos específicos com base em necessidades específicas de domínio.

### Adaptive RAG — roteamento por complexidade de query

Proposto por Jeong et al. (2024). Adaptive-RAG treina um classificador T5-Large com rótulos de complexidade derivados automaticamente para rotear entre três estratégias de retrieval, e demonstra que um roteador de complexidade de três classes pode igualar baselines sempre-caros com custo substancialmente menor.

A ideia central: Adaptive RAG projetado para otimizar o uso de LLMs com retrieval augmentado selecionando dinamicamente a melhor abordagem para lidar com queries com base em sua complexidade. Diferentemente de métodos existentes que ou tratam queries simples com overhead computacional desnecessário ou falham em queries complexas multi-step, este framework emprega um classificador (um LLM menor) para determinar a complexidade da query e adaptar a estratégia de retrieval adequadamente.

### Self-RAG

Asai et al. (2023). O LLM é equipado para julgar a qualidade do próprio retrieval e decidir quando re-recuperar. Self-RAG: um padrão modular de destaque introduzido em 2024 e amplamente adotado em 2025. Em Self-RAG, o próprio LLM é equipado para "julgar" sua performance. Ele gera instruções de retrieval, critica suas próprias saídas e as passagens recuperadas, e decide se precisa recuperar mais informação ou produzir uma resposta final.

### Corrective RAG (CRAG)

Proposto em 2024. CRAG é direcionado a auto-corrigir resultados do recuperador e melhorar a utilização de documentos para geração. Um avaliador de retrieval leve é introduzido para avaliar a qualidade geral dos documentos recuperados para uma dada query. O avaliador de retrieval quantifica um grau de confiança, permitindo diferentes ações de recuperação de conhecimento — Correct, Incorrect, Ambiguous — com base na avaliação. Para casos Incorrect e Ambiguous, buscas web em larga escala são integradas estrategicamente para resolver limitações em corpora estáticos e limitados.

A relação entre Self-RAG e CRAG, segundo a literatura: os dois são complementares, não alternativos. Self-RAG pode decidir se deve recuperar; CRAG pode avaliar e corrigir o que foi recuperado. Em um sistema de produção podem ser combinados.

Limitações documentadas do CRAG e Self-RAG:

- Calibração de limiar de score: os limiares precisam de ajuste por base de conhecimento. Confiabilidade da busca web: resultados de busca variam em qualidade. Aumento de custo: scoring (4 chamadas de LLM por query) mais possível busca web mais refinamento adiciona overhead significativo de tokens em comparação com retrieval básico.
- O mecanismo de auto-reflexão pode, por exemplo, às vezes levar a saídas que não são realmente sustentadas pelos dados (o sistema essencialmente "pensando demais").

### Agentic RAG

A fronteira atual. Abordagens híbridas-modulares: RAG em sua forma mais flexível combina roteamento, looping, reflexão e orquestração modular. As tarefas são divididas entre componentes especializados, coordenados por um agente que pode reconfigurar dinamicamente o workflow de acordo com a query ou o contexto de raciocínio.

A comparação cognitiva proposta na literatura é interessante: apresentamos uma revisão abrangente dos métodos de RAG Agêntico de Raciocínio, categorizando-os em dois sistemas primários: raciocínio predefinido, que segue pipelines modulares fixos para impulsionar o raciocínio, e raciocínio agêntico, onde o modelo autonomamente orquestra interação de ferramentas durante a inferência.

### GraphRAG

Estrutura o corpus como grafo de entidades e relações. GraphRAG impõe estrutura (entidades, relações, comunidades) sobre corpora não estruturados para suportar travessias locais guiadas por query, e detecção global baseada em comunidades.

Combinações também aparecem: sua forma mais avançada é o Agentic GraphRAG, onde um agente LLM decide dinamicamente se uma query é melhor servida por busca de similaridade vetorial, travessia de grafo de conhecimento, ou uma combinação de ambos, baseado na natureza da query.

A literatura é cuidadosa, no entanto, em apontar o custo de adoção: GraphRAG exige extração de entidades e relações via LLM durante a ingestão, o que é proibitivo em bases extensas.

---

## 5. Síntese e relevância para o BuscaAI

O posicionamento do BuscaAI dentro do estado da arte fica claro à luz da literatura:

**Padrão arquitetural adotado** — Modular RAG, alinhado com a recomendação dominante de Gao et al. (2024) e com a consolidação observada em 2024–2026.

**Estratégia de retrieval** — Hybrid Search (denso + esparso + RRF), alinhada com a literatura unânime que aponta busca híbrida como linha de base superior.

**Reranking** — incorporado como etapa pós-retrieval opcional, alinhado com os achados que apontam o reranker como o componente isolado de maior ganho.

**Pré-filtragem léxica** — etapa antes da busca híbrida, mecanismo coerente com a função de "porteiro lexical" que BM25 desempenha bem em escala.

**Adaptive routing leve** — uso de arestas condicionais no LangGraph para decisões de fluxo, capturando o espírito do Adaptive RAG sem o custo de um classificador treinado.

**O que ficou fora, com justificativa** — Self-RAG, Corrective RAG e GraphRAG, todos exigem LLM no laço de retrieval ou na ingestão, com custo de tokens incompatível com o caso de uso de bases gigantescas e genéricas. A literatura confirma esses custos como barreiras reais à adoção em produção.

---

## Referências citadas

- **Gao, Y., Xiong, Y., Gao, X., Jia, K., Pan, J., Bi, Y., Dai, Y., Sun, J., Wang, M., Wang, H.** (2024). Retrieval-Augmented Generation for Large Language Models: A Survey. arXiv:2312.10997v3.
- **Gao, Y., Xiong, Y., Wang, M., Wang, H.** (2024). Modular RAG: Transforming RAG Systems into LEGO-like Reconfigurable Frameworks. arXiv:2407.21059.
- **Lewis, P., et al.** (2020). Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks. NeurIPS.
- **Jeong, S., Baek, J., Cho, S., Hwang, S. J., Park, J. C.** (2024). Adaptive-RAG: Learning to Adapt Retrieval-Augmented Large Language Models through Question Complexity. NAACL.
- **Asai, A., et al.** (2024). Self-RAG: Learning to Retrieve, Generate, and Critique through Self-Reflection. ICLR.
- **Yan, S. Q., et al.** (2024). Corrective Retrieval Augmented Generation. arXiv:2401.15884.
- **Edge, D., et al.** (2024). From Local to Global: A Graph RAG Approach to Query-Focused Summarization. Microsoft Research.
- **Sharma, C.** (2025). Retrieval-Augmented Generation: A Comprehensive Survey of Architectures, Enhancements, and Robustness Frontiers. arXiv:2506.00054.
- **Ranjan, R.** (2024). A Comprehensive Survey of Retrieval-Augmented Generation (RAG): Evolution, Current Landscape and Future Directions. arXiv:2410.12837.
- **Robertson, S., Zaragoza, H.** (2009). The probabilistic relevance framework: BM25 and beyond. Foundations and Trends in IR.
