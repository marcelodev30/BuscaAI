# Decisões de Projeto e Trade-offs

Este arquivo reúne as discussões de "vale a pena ou não" que aconteceram ao longo do projeto. Cada seção é uma decisão, com as opções consideradas, os prós e contras, e a escolha final com a justificativa.

---

## Arquivo de configuração vs. classificação automática vs. multiagente

**O problema:** o framework precisa escolher a melhor estratégia de busca, mas é genérico e não sabe que tipo de dado vai receber.

**Opção 1 — Arquivo de configuração.** O desenvolvedor define explicitamente a estratégia.
- Prós: custo zero em tempo de execução, previsível, dá controle total a quem usa.
- Contras: exige que o dev saiba o que está fazendo (mas, como o público é de desenvolvedores, isso é previsibilidade, não fricção).

**Opção 2 — Classificar o dado automaticamente na ingestão.**
- Prós: o dev não precisa configurar nada.
- Contras: o tipo do dado não determina sozinho a estratégia (a forma como se pergunta também conta); tem custo de processamento na ingestão.

**Opção 3 — Multiagente que decide em tempo de execução.**
- Prós: adaptação máxima.
- Contras: gasto excessivo de tokens para uma decisão que, na maioria dos casos, é estável — a base não muda a cada query.

**Decisão:** arquivo de configuração como base, com a possibilidade de o framework analisar a base **uma única vez** na ingestão para sugerir uma config. O multiagente foi descartado pelo custo. Como o público-alvo são desenvolvedores, a configuração explícita é uma vantagem.

---

## Construir sobre o LangChain ou independente

**Decisão:** construir **sobre** o LangChain. Ele já resolve loaders, chunking, adaptadores de banco vetorial, embeddings e até BM25/busca híbrida. O trabalho do BuscaAI não é reimplementar isso — é **orquestrar** e expor uma interface limpa por cima.

---

## LangChain clássico vs. LangGraph

**Decisão:** LangGraph. O projeto precisa de decisões condicionais no fluxo (ex: aplicar reranker ou não) e o LangGraph modela isso de forma limpa, como arestas condicionais. Também deixa a porta aberta para fluxos mais sofisticados no futuro. A ressalva: curva de aprendizado maior, exige boa documentação. (Detalhes no arquivo sobre LangGraph.)

---

## HNSW (grafo) tem custo maior que um banco vetorial "normal"?

Esta foi uma confusão importante esclarecida no projeto.

**A dúvida:** transformar a base num "grafo" (HNSW) não seria mais custoso do que usar um banco vetorial normal?

**O esclarecimento:** o HNSW **é** o banco vetorial normal. Qdrant, Pinecone, Weaviate já usam HNSW internamente por padrão. Não é uma escolha entre "banco normal" e "banco com grafo" — o grafo já está lá, transparente.

- O custo de construir o HNSW é pago **uma vez, na ingestão**, e de forma incremental.
- Em troca, **todas as buscas** ficam rápidas.
- A alternativa real (banco sem índice, busca linear) só é viável para bases pequenas.

**Conclusão:** não há decisão a tomar aqui — usar o Qdrant normalmente já resolve. O custo que merece atenção em base gigantesca não é o HNSW, é a **geração dos embeddings** (que chama API externa por chunk).

---

## Graph RAG vs. RAG vetorial

**A dúvida:** valeria a pena usar Graph RAG?

**Análise:** Graph RAG extrai entidades e relações com uma LLM para cada chunk — custo proibitivo em base gigantesca, tanto na ingestão quanto na manutenção. Só compensa quando as relações entre entidades são o cerne da busca.

**Decisão:** RAG vetorial com busca híbrida é o padrão. Graph RAG poderia ser, no máximo, uma opção de configuração para casos específicos — mas fora do escopo principal. (Detalhes no arquivo de estratégias de RAG.)

---

## Manter ou remover as "collections"

**O que era:** collections seriam agrupamentos de dados dentro do banco vetorial (como tabelas de um banco relacional).

**O problema levantado:** elas aumentam a complexidade — o dev precisa saber em qual collection está cada dado, gerenciar várias, e a busca não atravessa collections. Pior: numa busca real, a resposta muitas vezes está espalhada por vários "domínios".

**A alternativa:** uma collection única, com tudo junto, e filtros por metadado quando (e se) o dev quiser restringir.

**Decisão:** **remover** collections como conceito obrigatório. Isso simplifica a API, a configuração e o código. Collections poderiam sobreviver só como opção para quem precisa de isolamento total (multi-tenant real). Resultado: a API deixou de ter `/collections/{id}/...` e passou a ter `/ingest`, `/search` diretos.

---

## O filtro de metadado é obrigatório?

**A dúvida:** se a busca híbrida é o padrão, o desenvolvedor é obrigado a configurar e passar filtros?

**Decisão:** não. O filtro é **opcional**. Por padrão, a busca híbrida varre tudo. O filtro só entra quando o dev explicitamente quer restringir (ex: buscar só numa fonte). Consequentemente, os metadados também viraram opcionais — o framework salva só os metadados "naturais" (fonte, página, data), sem exigir nada do dev.

---

## Classificar os chunks vs. pré-filtragem léxica

**O que era:** classificar cada chunk na ingestão (rotular como "jurídico", "técnico" etc.) para depois filtrar por categoria.

**Os problemas levantados:**
- Ninguém sabe que dados serão inseridos — não dá para definir as categorias de antemão.
- Usar uma LLM para classificar aumenta custo e tempo de ingestão.
- Usar um dicionário fixo de regras não funciona para dados genéricos.

**A alternativa:** pré-filtragem léxica com BM25 / índice invertido.

**Decisão:** **remover a classificação** e usar pré-filtragem léxica. Ela faz o mesmo trabalho (reduzir o universo de busca) de forma mais barata (sem modelo na ingestão), mais precisa (filtra por relevância real à query, não por categoria ampla) e agnóstica ao dado (funciona em qualquer domínio sem configuração). A ingestão passou a só extrair metadados naturais e indexar — sem etapa de classificação. (Detalhes no arquivo de estratégias de busca.)

---

## Hierarchical RAG (árvore de conhecimento) — manter ou não

**O que era:** criar resumos em camadas dos documentos, para responder bem tanto perguntas gerais quanto específicas.

**O problema:** adiciona complexidade significativa — geração de resumos na ingestão, lógica de decidir em qual nível buscar, classificação da query como "geral ou específica".

**Decisão:** **remover** do escopo, para simplificar. Com isso saiu também a etapa de classificar a query como geral/específica, que só existia para servir à hierarquia.

---

## Um embedding ou dois

**A dúvida:** seria mais simples gerar só um tipo de embedding e resolver a estratégia na hora da busca?

**O esclarecimento:** não, se a busca híbrida é o padrão. Busca híbrida **exige** os dois embeddings — o denso (significado) e o esparso (termo exato). Tanto na ingestão (salvar os dois por chunk) quanto na busca (gerar os dois para a query). Não há como contornar isso mantendo a busca híbrida.

**Decisão:** gerar e salvar os dois embeddings na ingestão. Para o esparso, usar o FastEmbed (com modelo SPLADE), que é o que o Qdrant foi otimizado para receber.

---

## Qdrant vs. OpenSearch/Elasticsearch — decisão em aberto

**O contexto:** o documento oficial do projeto cita OpenSearch, Meilisearch e Elasticsearch como motores candidatos, e prevê testes comparativos (Meta 2) justamente para escolher.

**A diferença central:**
- **Qdrant** — banco vetorial puro; a busca léxica precisa ser adicionada por fora.
- **OpenSearch / Elasticsearch** — motores de busca completos; já fazem busca léxica e vetorial no mesmo sistema, e já são distribuídos.

**Ponderação:** como o BuscaAI faz pré-filtragem léxica como peça central, um motor que já une léxico e vetorial (OpenSearch) poderia simplificar a stack. Por outro lado, o Qdrant tem o Filtered HNSW mais maduro e é leve para self-hosting.

**Status:** esta é a **única decisão de arquitetura em aberto**. Deve ser resolvida pelos testes comparativos da Meta 2 do projeto.

---

## Cache de queries — vale a pena?

**O problema:** em ambientes com queries repetidas, cada chamada passa pelo pipeline inteiro — pré-filtragem, busca híbrida, reranker, LLM. Tudo isso custa tempo e dinheiro.

**A decisão:** implementar cache com Redis, mas **desligável e com TTL configurável**.

- Prós: elimina custo e latência de queries idênticas, Redis já está na stack (fila de tarefas).
- Contras: resultado pode ficar desatualizado se os dados mudaram; não ajuda quando as queries são todas diferentes.

**Quando ligar:** bases que mudam pouco, com padrões de queries repetidas (FAQ, consultas padrão).

**Quando desligar:** desenvolvimento/testes, bases com atualizações muito frequentes, queries altamente variadas.

**Decisão sobre invalidação:** o cache é invalidado quando uma ingestão **de fato muda dados** — não a cada job concluído. Isso importa porque, com reingestão agendada (`SCHEDULE`), a maioria dos jobs não altera nada: o hash do conteúdo não mudou, então nenhum chunk foi tocado. Invalidar todo o cache nesses casos seria desperdício. A regra correta é: se o job alterou, adicionou ou removeu pelo menos um chunk, o cache é limpo; se o job rodou mas não mudou nada, o cache permanece. O dev também pode forçar limpeza manual. TTL padrão: 1 hora.

---

## Onde usar LLM e onde não usar

**O princípio adotado:** LLM custa tokens, então usar LLM só onde realmente agrega, e configurável por etapa. O framework permite escolher um provedor diferente para cada função:

```
geração da resposta final  → precisa de qualidade   → GPT-4o, Claude
expansão de query          → tarefa simples         → Groq, Llama local
reranker via LLM           → rapidez importa        → Groq
```

A ideia é o desenvolvedor pagar caro só onde precisa, e usar modelos baratos ou locais no resto.

Observação: a classificação de chunks na ingestão chegou a ser cogitada como uma função de LLM, mas foi **descartada** (ver a decisão "Classificar os chunks vs. pré-filtragem léxica" acima). Por isso ela não aparece nesta tabela — o BuscaAI não usa LLM na etapa de ingestão.
