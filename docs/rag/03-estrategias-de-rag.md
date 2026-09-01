# Estratégias de RAG

Existem várias maneiras de arquitetar um sistema RAG. Este arquivo explica os principais "tipos" de RAG, o que cada um faz, e quais foram escolhidos para o BuscaAI.

---

## Modular RAG

É a abordagem onde cada componente do pipeline é **plugável e configurável**: o carregador de documentos, o chunking, o modelo de embedding, a estratégia de busca, o reranker — tudo pode ser trocado ou ajustado.

O BuscaAI é, na sua classificação principal, um **Modular RAG**. A ideia do framework é justamente expor esses componentes de forma que o desenvolvedor "module" o sistema conforme a necessidade dele, através de um arquivo de configuração central.

As estratégias abaixo são, na prática, sub-estratégias que vivem dentro do Modular RAG.

---

## Hybrid RAG

É o RAG cuja etapa de busca é **híbrida** — combina busca lexical (BM25) com busca semântica (densa), fundindo os resultados com RRF.

No BuscaAI, Hybrid Retrieval é a estratégia de busca **padrão**. O raciocínio: cada tipo de dado e cada tipo de query tem uma estratégia mais eficaz, mas como o framework é genérico e não sabe o que vai receber, a busca híbrida é a aposta mais segura — ela cobre tanto o caso "preciso do termo exato" quanto o caso "preciso do significado".

Detalhes de como a busca híbrida funciona estão no arquivo de estratégias de busca.

---

## Hierarchical RAG (árvore de conhecimento)

Também chamado de índice hierárquico. Uma estratégia mais avançada onde, além dos chunks, você cria **resumos em camadas**.

O problema que resolve: se um documento é enorme e a pergunta é geral, nenhum chunk específico tem a resposta — ela está espalhada pelo documento todo.

A solução são resumos hierárquicos:

```
Nível 3 (mais geral):
[Resumo do documento inteiro]

Nível 2 (intermediário):
[Resumo cap. 1]  [Resumo cap. 2]  [Resumo cap. 3]

Nível 1 (específico):
[chunk 1][chunk 2][chunk 3][chunk 4][chunk 5][chunk 6]
```

Na busca: pergunta geral acerta no nível 3; pergunta específica acerta no nível 1.

**Decisão no projeto:** o Hierarchical RAG foi **removido** do escopo do BuscaAI, para simplificar. A consequência é que também saiu a etapa de classificar a query como "específica ou geral" (ela só existia para decidir em qual nível buscar). O arquivo de decisões e trade-offs detalha esse raciocínio.

---

## Adaptive RAG

É o RAG que **adapta a estratégia em tempo de execução**, dependendo da entrada. Por exemplo: decidir, com base na query, qual caminho de busca seguir, ou se aplica reranker ou não.

O BuscaAI tem uma característica de Adaptive RAG, mas numa forma **leve**: as decisões adaptativas são feitas como **arestas condicionais no grafo** do LangGraph (ver o arquivo sobre LangGraph), não com um agente de IA decidindo a cada passo. Isso dá a flexibilidade do roteamento adaptativo sem o custo de tokens de um multiagente.

---

## Graph RAG — e por que NÃO é usado

Graph RAG é uma arquitetura **completamente diferente** das anteriores. Aqui você não extrai só chunks — você extrai **entidades e as relações entre elas**, e monta um grafo de conhecimento.

```
Documento: "A Microsoft comprou o GitHub em 2018 por 7.5 bilhões"
                ↓
        Entidades e relações:
        [Microsoft] —comprou→ [GitHub]
        [GitHub] —valor→ [7.5 bilhões]
        [Microsoft] —ano→ [2018]
```

Esse grafo fica num banco de grafos (como o Neo4j), e a busca navega pelas **relações**, não por proximidade semântica.

### Por que o Graph RAG é muito mais custoso

- **Na ingestão:** para cada chunk, é preciso chamar uma LLM para extrair entidades e relações. Em 10 milhões de chunks, isso é custo proibitivo.
- **Na busca:** a query também precisa ser analisada para identificar entidades antes de navegar o grafo.
- **Na manutenção:** quando um dado muda, as relações no grafo precisam ser recalculadas — bem mais complexo que atualizar um vetor.

### Quando o Graph RAG valeria a pena

Só quando as **relações entre entidades** são o cerne da busca. Exemplo de pergunta que só o Graph RAG responde bem:

> "Quais empresas foram adquiridas por empresas americanas que também têm investimento da Microsoft?"

Isso é navegação de grafo pura. Para perguntas normais sobre o conteúdo de documentos, o RAG vetorial com busca híbrida resolve melhor e muito mais barato.

### Conclusão para o BuscaAI

Como a base do BuscaAI é gigantesca e genérica, Graph RAG seria inviável como padrão. Ele poderia, no máximo, ser uma estratégia **opcional** na configuração, para quem realmente precisar — mas não entra no escopo principal.

### Atenção a uma confusão comum

"Graph RAG" não tem nada a ver com o "grafo HNSW" do banco vetorial, nem com o "grafo do LangGraph":

| Termo | O que é | Você escolhe? | Custo extra |
|---|---|---|---|
| **HNSW** | estrutura interna do banco vetorial | não, é automático | quase nenhum |
| **Grafo do LangGraph** | forma de orquestrar o fluxo do sistema | sim | nenhum |
| **Graph RAG** | arquitetura baseada em grafo de conhecimento | sim | muito alto |

---

## Self-RAG e Corrective RAG — o que ficou de fora

Dois tipos mais sofisticados que **não** entraram no BuscaAI, mas vale conhecer:

- **Self-RAG** — o modelo avalia os próprios resultados e decide se precisa buscar de novo.
- **Corrective RAG** — se os documentos recuperados forem irrelevantes, o sistema corrige a query e tenta novamente.

Os dois exigem uma LLM dentro do laço de busca, o que significa custo de tokens a cada consulta. Poderiam ser recursos opcionais no futuro, mas não fazem parte do padrão.

---

## Como o BuscaAI se classifica

Juntando tudo, a classificação formal do BuscaAI é:

```
Modular RAG
   ├── Hybrid Retrieval        (busca padrão)
   └── Adaptive Routing        (decisões como arestas condicionais no grafo)
```

O Hierarchical Retrieval foi considerado e removido. O Graph RAG, o Self-RAG e o Corrective RAG ficaram fora do escopo. É uma arquitetura sólida e bem posicionada no estado da arte, sem complexidade excessiva.
