# BuscaAI — Material de Estudo

Este conjunto de documentos reúne, de forma organizada, tudo o que foi discutido sobre o projeto **BuscaAI**: um framework de RAG (Retrieval-Augmented Generation) híbrido, genérico, voltado para desenvolvedores que precisam fazer busca em bases de dados muito grandes.

O material foi escrito para quem **não conhece o assunto** e quer estudá-lo do zero. Cada arquivo trata de um tema específico, então não é preciso ler tudo de uma vez.

## Como ler

Se você é iniciante completo, leia nesta ordem:

1. **01-conceitos-fundamentais.md** — o vocabulário básico. O que é RAG, banco vetorial, embedding, chunk, LLM. Comece aqui.
2. **02-estrategias-de-busca.md** — como a busca funciona por dentro: busca densa, esparsa, híbrida, HNSW, pré-filtragem léxica.
3. **03-estrategias-de-rag.md** — os "tipos" de RAG: Modular, Hybrid, Hierarchical, Adaptive, Graph RAG.
4. **04-chunking.md** — como dividir documentos em pedaços, que é uma etapa que define a qualidade de tudo.
5. **05-langgraph.md** — o que é um grafo de execução e como o LangGraph orquestra o sistema.
6. **06-decisoes-e-tradeoffs.md** — as discussões de "vale a pena ou não": as vantagens e desvantagens de cada escolha.
7. **07-arquitetura-do-framework.md** — como o BuscaAI é montado: estrutura de pastas, arquivo de configuração, API, CLI.
8. **08-operacao.md** — o que mantém o sistema funcionando em produção: ingestão assíncrona, atualização/deleção de dados, backup, segurança.
9. **09-avaliacao.md** — como medir se o sistema é bom: métricas de retrieval e o framework RAGAS.
10. **10-cache-e-observabilidade.md** — cache de queries (o que é, TTL, invalidação) e como monitorar o sistema em produção com logs, métricas e alertas.
11. **11-recursos-avancados.md** — três recursos opcionais: query expansion (expandir a busca com LLM), SPLADE/FastEmbed (embeddings esparsos neurais) e multi-tenant (isolamento entre clientes).
12. **12-chatbot-de-validacao.md** — o protótipo de validação do projeto: o que é, como funciona o histórico de conversa, streaming, e como ele é usado para coletar as métricas do projeto.
13. **13-revisao-sistematica-literatura.md** — revisão do estado da arte em IR, LLMs e RAG no período 2024–2026, com os achados que sustentam as decisões do projeto e referências às fontes primárias.
14. **14-tabela-comparativa-tecnicas-rag.md** — comparação sistemática das principais técnicas de RAG da literatura recente, com tabela consolidada de custos, ganhos e adequação ao caso de uso do BuscaAI.

## O que é o BuscaAI em uma frase

Um framework que um desenvolvedor configura uma vez (em um arquivo central, parecido com o `settings.py` do Django), sobe com um comando, e passa a ter um sistema de busca inteligente sobre suas bases de dados — acessível por uma API HTTP ou por linha de comando.

## Glossário rápido

Termos que aparecem o tempo todo no material:

- **RAG** — Retrieval-Augmented Generation. Técnica em que uma IA consulta uma base externa antes de responder.
- **LLM** — Large Language Model. Modelo de linguagem de grande escala (ex: GPT, Claude).
- **Chunk** — pedaço de um documento, depois de ele ser dividido.
- **Embedding** — representação de um texto como uma lista de números (um vetor).
- **Banco vetorial** — banco de dados especializado em guardar e buscar embeddings.
- **Retrieval** — a etapa de "recuperação", ou seja, de buscar os trechos relevantes.
- **Busca híbrida** — combinação de busca por palavra-chave com busca por significado.
