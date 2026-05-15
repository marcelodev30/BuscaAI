# Chunking — Dividindo Documentos em Pedaços

Chunking é a etapa de dividir um documento em pedaços menores (chunks) antes de gerar embeddings. Parece um detalhe, mas é uma das decisões que mais afeta a qualidade de todo o sistema.

---

## Por que o chunking importa tanto

Chunking ruim destrói o RAG, independentemente de qualquer outra coisa estar bem feita. Se o chunk corta no meio de uma ideia, a busca nunca vai recuperar o contexto certo.

```
Texto original:
"O contrato pode ser rescindido em 30 dias.
 O aviso prévio deve ser dado por escrito."

Chunk ruim (cortou no meio):
chunk A: "O contrato pode ser rescindido em 30"
chunk B: "dias. O aviso prévio deve ser dado por escrito."

Chunk bom (respeitou a ideia):
chunk A: "O contrato pode ser rescindido em 30 dias.
          O aviso prévio deve ser dado por escrito."
```

---

## O conceito de overlap

**Overlap** (sobreposição) é uma técnica onde os últimos tokens de um chunk são repetidos no início do próximo. Isso evita perder contexto exatamente no ponto de divisão.

```
chunk 1: [---------------------------][overlap]
chunk 2:                         [overlap][---------------------------]
```

Um overlap típico é de 50 a 100 tokens.

---

## As estratégias de chunking

### 1. Fixed Size (tamanho fixo)

Corta a cada N caracteres ou tokens, sem olhar o conteúdo.

- Custo: zero.
- Problema: corta no meio de ideias.
- Quando usar: praticamente nunca como primeira opção.

### 2. Recursive Character (recursivo)

É o padrão do LangChain. Tenta dividir respeitando uma hierarquia de separadores:

```
Tenta primeiro por:  \n\n   (parágrafo)
Se ainda grande:     \n     (linha)
Se ainda grande:     .      (frase)
Se ainda grande:     espaço (palavra)
```

Respeita a estrutura natural do texto muito melhor que o tamanho fixo.

- Custo: zero.
- Precisão: boa para texto geral.
- Quando usar: é o **default seguro** para a maioria dos casos.

### 3. Markdown / Code Splitter

Divide respeitando a estrutura do tipo de documento:

```
Markdown → divide pelos títulos (#, ##, ###)
Código   → divide por funções, classes, métodos
```

- Custo: zero.
- Precisão: excelente, para o tipo certo de documento.
- Quando usar: quando se sabe que o dado é markdown ou código.

### 4. Semantic Chunking (semântico)

Em vez de dividir por tamanho ou estrutura, divide por **mudança de significado**. Compara o embedding de cada frase com o da próxima; quando o significado muda bruscamente, faz a divisão ali.

```
frase 1: "O contrato é rescindido em 30 dias"
frase 2: "O aviso deve ser por escrito"          ← mesmo assunto, não divide
frase 3: "A empresa foi fundada em 1990"         ← assunto mudou, divide aqui
```

- Custo: médio — precisa gerar embedding de cada frase.
- Precisão: excelente.
- Quando usar: quando qualidade importa mais que velocidade de ingestão.

### 5. Document Structure (estrutura do arquivo)

Divide conforme a estrutura natural do formato:

```
PDF  → por página ou seção
CSV  → por linha ou grupo de linhas
HTML → por tag semântica (article, section, p)
Word → por heading
```

- Custo: baixo.
- Precisão: muito boa para documentos estruturados.

---

## Como o BuscaAI decide a estratégia

Como o framework é genérico, ele usa **camadas de fallback**:

```
1. O dev especificou uma estratégia na config?  → usa essa.
2. Não especificou? Detecta pelo tipo do arquivo:
     markdown → Markdown Splitter
     código   → Code Splitter
     csv      → Structure Splitter
3. Não deu para detectar?  → usa Recursive (fallback seguro).
```

E o dev sempre pode sobrescrever na configuração:

```python
CHUNKING = {
    "strategy": "recursive",   # recursive, semantic, markdown, code
    "chunk_size": 512,
    "overlap": 50
}
```

---

## O tamanho ideal do chunk

O tamanho do chunk afeta diretamente a qualidade da busca:

```
Chunk muito pequeno (< 256 tokens):
  perde contexto, a resposta fica fragmentada

Chunk muito grande (> 1024 tokens):
  o vetor fica "genérico demais", a busca perde precisão
  (o embedding tenta representar assuntos demais de uma vez)

Ponto de equilíbrio geral:
  ~512 tokens, com 50–100 de overlap
```

Para bases gigantescas, o conselho é ficar no ponto de equilíbrio e caprichar no overlap, em vez de partir para estratégias caras de chunking.
