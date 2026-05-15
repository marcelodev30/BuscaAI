# Estratégias de Busca

Este arquivo explica **como a busca funciona por dentro**: os tipos de busca, como elas se combinam, e as estruturas que tornam a busca rápida em escala.

---

## Busca densa (semântica)

A busca densa usa embeddings densos. Você transforma a pergunta num vetor e procura, na base, os vetores mais próximos.

O que ela faz bem: entende **significado**. Buscando "rescisão de contrato", ela encontra um trecho que fala em "encerramento de acordo", mesmo sem nenhuma palavra em comum.

O que ela faz mal: pode perder o documento que tem o **termo exato** que você quer, se o significado geral do trecho for um pouco diferente.

---

## Busca esparsa (lexical / BM25)

A busca esparsa usa embeddings esparsos — na prática, algoritmos como BM25. Ela procura correspondência de **termos**.

O que ela faz bem: encontra o **termo exato**. É ótima para conteúdo técnico, códigos, nomes próprios, identificadores — situações onde a palavra precisa bater.

O que ela faz mal: não entende sinônimos nem contexto. Buscando "rescisão", não acha "encerramento".

---

## Busca híbrida

Busca híbrida é a combinação das duas: roda a busca densa e a busca esparsa, e funde os resultados (geralmente com RRF).

```
Só densa:
"rescisão contratual" → acha "encerramento de acordo"   ✅
"rescisão contratual" → pode perder o termo exato        ❌

Só esparsa (BM25):
"rescisão contratual" → acha o termo exato               ✅
"rescisão contratual" → não acha "encerramento de acordo" ❌

Híbrida:
acha os dois                                              ✅
```

Por isso a busca híbrida é a estratégia **padrão** do BuscaAI. E é por isso também que, na ingestão, é preciso gerar **os dois embeddings** (denso e esparso) para cada chunk — sem os dois, não há busca híbrida.

---

## HNSW — como o banco vetorial busca rápido

HNSW significa *Hierarchical Navigable Small World*. É a estrutura de dados que permite busca rápida em milhões de vetores.

### O problema que ele resolve

A busca ingênua (chamada *Flat Index* ou busca linear) compara a pergunta com **todos** os vetores da base. Com 10 milhões de chunks, são 10 milhões de comparações por consulta. Inviável.

### Como o HNSW funciona

O HNSW é uma estrutura em **grafo de camadas**, parecida com um mapa com zoom:

```
Camada 2 (visão geral — poucos nós, conexões longas)
    [A] ————————————— [B] ————— [C]

Camada 1 (intermediária)
    [A] — [D] — [E] — [B] — [F] — [C]

Camada 0 (todos os nós — conexões curtas)
    [A]-[D]-[G]-[H]-[E]-[I]-[B]-[F]-[J]-[C]
```

A busca começa na camada de cima, encontra rapidamente a região aproximada, e vai descendo até os vizinhos mais próximos reais. Em vez de comparar 10 milhões, compara talvez 200.

### O ponto importante: HNSW é transparente

O HNSW é a estrutura **interna** do banco vetorial. Quando você salva um vetor no Qdrant, ele encaixa esse vetor no HNSW automaticamente. Você nunca vê, nunca gerencia o grafo. Não é uma escolha de arquitetura — é detalhe de implementação do banco.

Não confunda: **HNSW** (estrutura interna, automática) é completamente diferente de **Graph RAG** (uma arquitetura de sistema que você escolhe conscientemente — ver o arquivo de estratégias de RAG).

### Flat Index versus HNSW

| Chunks na base | Flat Index (linear) | HNSW |
|---|---|---|
| 10 mil | rápido | rápido |
| 1 milhão | lento | rápido |
| 10 milhões | inviável | rápido |

O Flat Index é **exato** — retorna o resultado matematicamente perfeito. O HNSW é **aproximado** — retorna o "quase mais próximo". Na prática, para RAG, essa diferença é insignificante: você não precisa do chunk matematicamente mais próximo, precisa do chunk *relevante*, e o HNSW acerta isso muito bem.

### O custo do HNSW

Construir o HNSW tem um custo, mas ele é pago **uma vez, na ingestão**, e o grafo é construído incrementalmente (cada vetor novo é encaixado no grafo existente, sem reconstruir tudo). Em troca, todas as buscas futuras são rápidas. Numa base com muitas consultas, é uma troca excelente.

---

## Filtered HNSW — busca com filtro de metadado

Esta seção descreve um recurso que só entra em cena **quando o filtro de metadados é usado**. Como vimos, no BuscaAI o filtro é opcional — a maioria das buscas não usa filtro nenhum. Mas quando o desenvolvedor *quer* restringir a busca (ex: "só nesta fonte", "só deste período"), o Filtered HNSW é o que faz isso funcionar bem. Vale entender por quê.

Imagine que você quer buscar **só** os chunks de uma fonte específica, ou de um período específico.

### A forma ingênua (e ruim)

```
1. HNSW busca os 50 mais próximos de toda a base
2. Você filtra os que batem com o critério
3. Sobram 3
```

Dois problemas:

- **Poucos resultados** — você pediu 50, filtrou, sobrou 3.
- **Perdeu os relevantes** — o HNSW trouxe os 50 mais próximos do universo *inteiro*. Os chunks que batem com seu filtro e são relevantes podem estar na posição 80, 200 — e você nunca vai vê-los.

### O Filtered HNSW

Em vez de filtrar **depois** da busca, o Filtered HNSW considera o filtro **durante** a navegação do grafo. Quando vai explorar um nó vizinho, ele já verifica se aquele nó passa no filtro. Se não passa, desvia e tenta outro caminho.

```
Query + filtro: fonte = "contrato.pdf"

Navegação normal iria: [A] → [B] → [C]
                                  ↑ não é de contrato.pdf, pula

Filtered HNSW desvia: [A] → [B] → [D] → [E]
                                        ↑ é de contrato.pdf, entra
```

O resultado: você busca **dentro** do subconjunto filtrado, em vez de buscar tudo e filtrar depois.

O Qdrant é um dos bancos vetoriais com a implementação mais madura de Filtered HNSW — foi um dos motivos da escolha dele no projeto.

---

## Pré-filtragem léxica

Esta é uma das peças centrais do BuscaAI. É uma etapa que roda **antes** da busca híbrida, para reduzir drasticamente o universo de chunks a processar.

### O fluxo

```
10 milhões de chunks na base
        ↓
pré-filtragem léxica (BM25 / índice invertido)
        ↓
~50 mil chunks candidatos
        ↓
busca híbrida nos 50 mil
        ↓
reranker nos ~100 melhores
        ↓
top 5 finais
```

Sem a pré-filtragem, a busca híbrida teria que processar 10 milhões. Com ela, processa 50 mil. (Os números são ilustrativos e configuráveis — o ponto é a redução de ordem de grandeza em cada etapa: milhões → dezenas de milhares → centenas → unidades.)

### Por que é tão rápida

A busca léxica usa um **índice invertido** — uma tabela que mapeia cada termo para a lista de chunks que o contêm:

```
"rescisão"  → [chunk_42, chunk_891, chunk_1203, ...]
"contrato"  → [chunk_42, chunk_156, chunk_891, ...]
"prazo"     → [chunk_42, chunk_891, chunk_3201, ...]

Query: "prazo rescisão contrato"
→ intersecção: chunk_42 e chunk_891 aparecem nos três
→ candidatos identificados quase instantaneamente
```

Não calcula nenhum vetor. É lookup de tabela hash — questão de microssegundos.

### Por que a pré-filtragem léxica substituiu a ideia de "classificar os chunks"

Durante o projeto cogitou-se classificar cada chunk na ingestão (rotular como "jurídico", "técnico" etc.) para depois filtrar por categoria. Essa ideia foi descartada em favor da pré-filtragem léxica. Os motivos:

- **Classificação é estática; pré-filtragem é dinâmica.** Um chunk rotulado "jurídico" some de uma busca filtrada por outra categoria, mesmo que ele seja relevante. A pré-filtragem léxica encontra todo chunk que tem as palavras da query, independente de domínio — não perde nada relevante.
- **Classificação pressupõe conhecer as categorias.** Num framework genérico, você não sabe que dados vão entrar. A pré-filtragem léxica é agnóstica ao dado: funciona em qualquer domínio sem configuração.
- **Custo.** Classificar exige rodar um modelo para cada chunk na ingestão (milhões de chamadas). A pré-filtragem só tokeniza o texto e salva num índice invertido — operação de texto, muito barata.
- **Precisão.** Classificação filtra por categoria ampla (ainda sobra 1 milhão de chunks "jurídicos"). A pré-filtragem filtra por relevância real à query (sobram ~50 mil que de fato podem ter a resposta).

Resumo: a pré-filtragem léxica faz o mesmo trabalho — reduzir o universo de busca — de forma mais barata, mais precisa e sem precisar conhecer os dados de antemão.

### Configuração no framework

```python
PRE_FILTERING = {
    "enabled": True,
    "strategy": "bm25",        # bm25, tfidf, inverted_index
    "top_n": 50000,            # quantos candidatos passam adiante
    "min_score": 0.0,          # descarta chunks sem palavra em comum
    "stopwords": {             # palavras ignoradas, por idioma
        "pt": ["o", "a", "de", "e", "que", "em"],
        "en": ["the", "a", "of", "and", "in"]
    }
}
```

---

## O fluxo de busca completo

Juntando todas as peças:

```
QUERY chega
      ↓
[1] pré-filtragem léxica (BM25)        milhões → dezenas de milhares
      ↓
[2] filtro de metadados (opcional)     só se o dev passar um filtro
      ↓
[3] busca híbrida (densa + esparsa + RRF)   → ~100 candidatos
      ↓
[4] reranker (opcional, condicional)        ~100 → top 5
      ↓
RESULTADO
```

O filtro de metadados (passo 2) é **opcional**: por padrão a busca varre tudo que sobrou da pré-filtragem. O filtro só entra se o desenvolvedor explicitamente quiser restringir (ex: buscar só numa fonte específica).

---

## Por que o BM25 aparece duas vezes no pipeline

Uma dúvida natural ao olhar o fluxo: o BM25 aparece na **pré-filtragem léxica** (passo 1) e de novo dentro da **busca híbrida** (passo 3, como o componente esparso). Por que rodar BM25 duas vezes?

Porque os dois usos têm **propósitos diferentes**, mesmo usando o mesmo algoritmo por baixo:

**Na pré-filtragem — papel de "porteiro".** Aqui o BM25 só precisa responder uma pergunta grosseira: "este chunk tem alguma chance de ser relevante?". Ele roda sobre os 10 milhões de chunks e a única coisa que importa é separar os ~50 mil que têm relação de termos com a query dos milhões que não têm nada a ver. É um corte rápido e generoso — é melhor deixar passar um chunk a mais do que cortar um relevante.

**Na busca híbrida — papel de "avaliador fino".** Aqui o BM25 roda só sobre os ~50 mil que passaram, e o objetivo é diferente: produzir um **ranking de qualidade** que será fundido (via RRF) com o ranking da busca densa. Não é mais "tem chance ou não" — é "quão bem este chunk casa com os termos da query, em comparação com os outros candidatos".

Uma analogia: a pré-filtragem é a triagem de currículos que descarta os que claramente não servem; a busca esparsa é a entrevista que classifica os finalistas. Mesma pessoa avaliando, perguntas e profundidade diferentes.

### Existe sobreposição? Sim, e é aceitável

É verdade que há trabalho repetido — o BM25 da pré-filtragem já calculou algo parecido com o que o BM25 da busca esparsa vai recalcular. Há duas formas de lidar com isso:

- **Aproveitar o score da pré-filtragem.** O framework pode guardar o score que o BM25 da pré-filtragem produziu e reutilizá-lo como o componente esparso da fusão RRF, em vez de recalcular. Isso elimina a repetição.
- **Recalcular mesmo assim.** Em escala de ~50 mil chunks, rodar BM25 de novo custa milissegundos. Para muitos casos, a simplicidade de tratar as duas etapas como independentes compensa o pequeno retrabalho.

A decisão entre as duas é de implementação. O importante para entender o conceito: **pré-filtragem e busca esparsa não são a mesma coisa rodando duas vezes por desperdício — são duas etapas com objetivos distintos**, e a sobreposição entre elas é pequena e gerenciável.

### E se o motor escolhido for o OpenSearch?

Vale notar que essa "dobra" do BM25 desaparece naturalmente se o projeto adotar OpenSearch/Elasticsearch em vez do Qdrant (decisão ainda em aberto — ver o arquivo de trade-offs). Nesses motores, a filtragem léxica e a busca já acontecem no mesmo sistema, no mesmo índice — não há uma etapa de pré-filtro separada de uma etapa de busca. Esse é, inclusive, um dos argumentos a favor do OpenSearch.
