# Conceitos Fundamentais

Este arquivo explica o vocabulário básico do projeto. Se algum termo nos outros documentos não fizer sentido, ele provavelmente está explicado aqui.

---

## O que é Recuperação de Informação

Recuperação de Informação (em inglês, *Information Retrieval* ou IR) é a área que estuda como localizar informação relevante dentro de grandes coleções de documentos. É o campo por trás dos buscadores.

O problema central: você tem uma coleção enorme de textos e uma pergunta. Como encontrar, rápido, os trechos que respondem à pergunta?

Historicamente isso era feito com modelos matemáticos e estatísticos que estimam o quão "relevante" um documento é para uma consulta. Três modelos clássicos:

- **Booleano** — o documento contém ou não contém os termos. Resposta sim/não.
- **Vetorial** — documentos e consultas viram vetores num espaço, e a relevância é a proximidade entre eles.
- **Probabilístico** — estima a probabilidade de um documento ser relevante. É a base do BM25.

A grande limitação desses modelos clássicos: eles dependem de correspondência de palavras. Se a pergunta usa uma palavra e o documento usa um sinônimo, a busca pode falhar.

---

## O que é uma LLM

LLM significa *Large Language Model* — Modelo de Linguagem de Grande Escala. São modelos treinados sobre enormes quantidades de texto, capazes de entender e gerar linguagem natural. Exemplos: GPT, Claude, Llama.

O que as LLMs trouxeram de novo para a busca: elas entendem **contexto e intenção**, não só palavras. Uma busca tradicional por "data de nascimento de Dom Pedro II" falha se o documento diz "Dom Pedro II nasceu em 2 de dezembro de 1825" sem usar a expressão "data de nascimento". Uma LLM entende que as duas coisas são equivalentes.

As LLMs têm duas limitações importantes:

- **Alucinação** (*hallucination*) — geram respostas que parecem corretas mas são falsas. Isso acontece porque o modelo é probabilístico: ele prevê a próxima palavra mais provável, sem um mecanismo interno de verificação de verdade.
- **Conhecimento congelado** — o modelo só sabe o que estava nos dados de treino. Não conhece informação nova nem dados privados de uma empresa.

---

## O que é RAG

RAG significa *Retrieval-Augmented Generation* — Geração Aumentada por Recuperação.

A ideia: em vez de confiar só no que a LLM "decorou" no treino, você dá a ela uma base de dados externa para consultar **no momento da pergunta**. O modelo busca trechos relevantes nessa base e usa esses trechos como fundamento para gerar a resposta.

Funcionamento básico:

1. Chega uma pergunta.
2. Um mecanismo de busca recupera os documentos relevantes na base.
3. Esses documentos são colocados junto com a pergunta no contexto enviado à LLM.
4. A LLM gera a resposta fundamentada nesses documentos.

Por que isso é bom:

- O modelo base não muda — você atualiza o conhecimento só atualizando a base de dados, sem retreinar nada.
- Reduz alucinação, porque a resposta é guiada por trechos reais recuperados.
- É adequado para cenários dinâmicos, onde os dados mudam com frequência.

A limitação do RAG: a cada pergunta ele precisa fazer o processo de busca. Em bases gigantescas, esse processamento repetido pode virar um gargalo de custo e tempo.

---

## RAG versus Fine-tuning

Existem duas formas principais de fazer uma LLM trabalhar com conhecimento específico.

**Fine-tuning** é re-treinar o modelo com novos dados, de modo que o conhecimento fique gravado nos próprios pesos da rede neural.

- Vantagem: a resposta é rápida, porque não precisa consultar nada externo.
- Desvantagens: re-treinar é caro e exige infraestrutura pesada; é inviável se a base muda muito; e o modelo continua sujeito a alucinação porque não há verificação de veracidade.

**RAG** mantém o modelo intacto e consulta uma base externa em tempo de execução.

- Vantagens: atualizar é barato (só mexe na base), reduz alucinação, ideal para dados dinâmicos.
- Desvantagem: cada consulta gera custo de busca.

Resumo: para bases dinâmicas, grandes e com exigência de confiabilidade, RAG é a escolha mais adequada.

---

## O que é um Chunk

Um documento inteiro é grande demais para ser tratado como uma unidade de busca. Por isso ele é dividido em pedaços menores, chamados **chunks**.

Por que dividir: quando alguém faz uma pergunta, você quer recuperar exatamente o trecho relevante, não o documento de 50 páginas inteiro. Chunks menores tornam a busca precisa.

O tamanho do chunk é uma decisão delicada (tratada em detalhe no arquivo de chunking): pequeno demais perde contexto, grande demais perde precisão.

---

## O que é um Embedding

Um **embedding** é a representação de um texto como uma lista de números — um vetor.

A mágica do embedding: textos com **significados parecidos** geram vetores **próximos** nesse espaço numérico. Textos sobre assuntos diferentes geram vetores distantes.

Exemplo:

```
"Como instalar Python"  → [0.23, 0.87, 0.12, 0.95, ...]
"Instalação do Python"  → [0.24, 0.85, 0.11, 0.94, ...]   ← muito próximo
"Receita de bolo"       → [0.91, 0.03, 0.67, 0.11, ...]   ← distante
```

Isso permite "buscar por significado": você transforma a pergunta em vetor e procura os vetores mais próximos na base.

Os embeddings são gerados por modelos próprios para isso. Um exemplo conhecido é o Sentence-BERT, que gera embeddings de frases. Esses modelos modernos usam uma arquitetura chamada *transformer*, baseada em mecanismos de atenção, que capta dependências de significado no texto.

---

## Embedding denso e embedding esparso

Existem dois tipos de embedding, e eles servem a propósitos diferentes.

**Embedding denso** é o vetor de significado descrito acima — uma lista de números contínuos onde cada posição tem um valor. Captura semântica. É o que permite achar "encerramento de acordo" quando você busca "rescisão de contrato".

**Embedding esparso** é uma representação onde a maioria das posições é zero, e só algumas têm valor — cada posição corresponde a um termo do vocabulário, com um peso. Captura presença e importância de termos. A forma mais simples de embedding esparso vem de algoritmos como BM25, que atribuem peso só às palavras que de fato aparecem no texto.

```
Embedding denso:   [0.23, 0.87, 0.12, 0.95, 0.44, ...]   (tudo preenchido)
Embedding esparso: {"contrato": 0.8, "rescisão": 0.6}    (só alguns termos têm peso)
```

Existem também embeddings esparsos mais sofisticados, gerados por modelos neurais (como o SPLADE), que conseguem atribuir peso até a termos relacionados que não aparecem literalmente no texto. Esse é o tipo usado pelo BuscaAI, e está detalhado no arquivo de recursos avançados.

A busca híbrida usa o embedding denso e o esparso ao mesmo tempo. Por isso, na ingestão, é preciso gerar e salvar os dois para cada chunk.

---

## O que é um Banco Vetorial

Um **banco vetorial** é um banco de dados especializado em armazenar embeddings e fazer busca por proximidade entre eles de forma eficiente.

Comparação com banco relacional:

```
Banco relacional        Banco vetorial
─────────────────────────────────────
tabela              =   collection
linha               =   chunk + vetor
coluna              =   metadado (payload)
índice comum        =   índice HNSW
```

Exemplos de bancos vetoriais: Qdrant, Pinecone, Weaviate, e o pgvector (extensão do PostgreSQL).

Cada item salvo num banco vetorial tem: o vetor (ou vetores, no caso híbrido), e um conjunto de metadados associados — chamados de *payload* — como nome do arquivo de origem, página, data de ingestão.

---

## O que é BM25

BM25 é um algoritmo clássico de recuperação de informação, baseado no modelo probabilístico. Ele estima o quão relevante um documento é para uma consulta, com base na frequência dos termos.

A intuição do BM25:

- Um documento que contém os termos da busca é relevante.
- Termos **raros** valem mais que termos comuns. Se a busca tem a palavra "rescisão" e a palavra "de", a presença de "rescisão" é muito mais informativa.
- Há um limite: repetir o mesmo termo 100 vezes não torna o documento 100 vezes mais relevante. O ganho satura.

BM25 é busca **lexical** — depende de correspondência de palavras. Não entende sinônimos nem contexto. Mas é extremamente rápido e funciona muito bem para termos técnicos e específicos, onde a palavra exata importa.

No projeto, BM25 aparece em dois papéis: como uma das estratégias de busca, e como mecanismo de **pré-filtragem léxica** (explicado no arquivo de estratégias de busca).

---

## O que é Reranker

Um **reranker** é um modelo que pega os resultados de uma busca e os **reordena** com mais precisão.

Por que ele existe: a busca inicial (híbrida, por exemplo) é rápida mas usa um critério relativamente grosseiro, e recupera, digamos, os 50 candidatos mais promissores. Entre esses 50, alguns são realmente ótimos e outros são ruído. O reranker analisa cada um dos 50 com mais cuidado e coloca os realmente relevantes no topo.

```
busca híbrida → top 50 candidatos (rápido, critério grosseiro)
      ↓
reranker → reordena → top 5 finais (lento, critério fino)
```

Em bases gigantescas o reranker é quase obrigatório, porque a busca inicial inevitavelmente traz alguns resultados irrelevantes. Em bases pequenas e bem comportadas, pode ser dispensável.

Tipos de reranker: modelos *cross-encoder* (rodam localmente) ou serviços como o Cohere Rerank.

---

## O que é RRF (Reciprocal Rank Fusion)

Quando você faz busca híbrida, tem dois conjuntos de resultados: um da busca densa e um da busca esparsa. Como combinar os dois numa lista única?

RRF — *Reciprocal Rank Fusion* — é o método mais usado. Ele olha a **posição** (rank) de cada documento em cada lista e combina. Um documento que aparece bem colocado nas duas listas sobe; um que aparece bem em só uma sobe menos.

A ideia central é fundir por posição, não por score bruto — porque os scores da busca densa e da esparsa estão em escalas diferentes e não dá para somar diretamente.

---

## O que é Indexação Incremental

**Indexar** é o processo de preparar os dados para busca — no caso do RAG, transformar documentos em chunks, gerar embeddings e salvar no banco.

**Indexação incremental** significa conseguir adicionar dados novos **sem reprocessar tudo de novo**. Numa base gigantesca, reindexar milhões de chunks toda vez que um documento novo entra é inviável. O sistema precisa conseguir só acrescentar o que mudou.

Isso se conecta com o conceito de **dinamicidade das bases**: bases reais não são estáticas, recebem dados novos o tempo todo, e o sistema de busca tem que acompanhar.
