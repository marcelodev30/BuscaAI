# Guia Completo: LangChain e RAG

> Baseado no **LangChain 1.3.x** (agosto/2026). Requer Python 3.10+.
>
> ⚠️ **O LangChain 1.0 (out/2025) foi uma quebra grande.** Se você achar tutorial com `RetrievalQA`, `ConversationalRetrievalChain`, `load_qa_chain` ou `ConversationBufferMemory` importados de `langchain.chains`, é código de 2023–2024 que **não roda mais** sem instalar o pacote de compatibilidade. Este guia usa a API atual.

---

## 1. O que é RAG (e quando não usar)

**RAG = Retrieval-Augmented Generation.** Em vez de esperar que o LLM "saiba" a resposta, você busca os trechos relevantes na sua base e coloca no prompt.

O fluxo tem duas fases distintas:

```
INDEXAÇÃO (offline, roda uma vez ou periodicamente)
  documentos → carregar → dividir em chunks → gerar embeddings → salvar no vector store

CONSULTA (online, a cada pergunta)
  pergunta → embedding → buscar chunks similares → montar prompt → LLM → resposta
```

### Quando RAG resolve

- Base de conhecimento privada (documentação interna, contratos, tickets).
- Informação que muda com frequência (política de preços, catálogo).
- Necessidade de citar a fonte.
- Volume de texto grande demais para caber na janela de contexto.

### Quando RAG **não** é a resposta

| Situação | O que fazer em vez disso |
|---|---|
| A base inteira cabe no contexto (< ~100k tokens) e é estável | Mande tudo no prompt, com cache. Mais simples e mais preciso. |
| Você precisa mudar o *estilo* ou *comportamento* do modelo | Prompt melhor ou fine-tuning. RAG injeta fatos, não muda personalidade. |
| A pergunta exige agregação ("quantos contratos vencem em 2027?") | SQL / text-to-SQL. RAG busca por similaridade, não conta nem soma. |
| Os dados são estruturados e a query é precisa | Banco relacional. Não vetorize um CRM. |

Esse último ponto derruba muitos projetos. RAG é ótimo em "me explique X" e péssimo em "quantos X existem".

---

## 2. O ecossistema em 2026

O LangChain foi fatiado em vários pacotes. Saber qual é qual evita muita dor de cabeça:

| Pacote | O que tem | Status |
|---|---|---|
| `langchain-core` | Abstrações base: `Document`, `Runnable`, prompts, LCEL | Estável, base de tudo |
| `langchain` | Agentes, `init_chat_model`, orquestração de alto nível | Atual (1.3.x) |
| `langgraph` | Motor de grafos por baixo dos agentes | Atual |
| `langchain-text-splitters` | Divisão de texto em chunks | Atual |
| `langchain-openai`, `langchain-anthropic`, `langchain-qdrant`, ... | Integrações por provedor | Atual |
| `langchain-classic` | Chains e retrievers legados (`RetrievalQA`, `SelfQueryRetriever`, ...) | Compatibilidade |
| `langchain-community` | Integrações contribuídas pela comunidade | **Arquivado em jun/2026** |

**Regra prática:** integração relevante virou pacote próprio (`langchain-<provedor>`). Se você só acha algo em `langchain-community`, ou existe um pacote dedicado, ou o componente foi para `langchain-classic`.

### O que mudou de verdade na v1

1. **Chains prontas saíram do caminho principal.** `RetrievalQA` e companhia foram para `langchain-classic`. O jeito atual é montar o pipeline com LCEL (o operador `|`) ou usar um agente.
2. **Agentes agora rodam em cima do LangGraph.** `create_agent` substituiu `AgentExecutor` e `initialize_agent`.
3. **Memória mudou.** As classes `ConversationBufferMemory` saíram; o estado de conversa agora vive no checkpointer do LangGraph.

---

## 3. Instalação

```bash
pip install langchain langchain-core langchain-text-splitters

# provedor de LLM (escolha o seu)
pip install langchain-anthropic
pip install langchain-openai

# embeddings locais (sem custo por token)
pip install langchain-huggingface sentence-transformers

# vector store (escolha o seu)
pip install langchain-qdrant
pip install langchain-chroma
pip install langchain-postgres      # PGVector

# loaders de arquivos
pip install pypdf unstructured python-docx

# observabilidade (recomendado)
pip install langsmith
```

Variáveis de ambiente:

```bash
export ANTHROPIC_API_KEY="..."
export OPENAI_API_KEY="..."

# LangSmith — ver o que acontece dentro do pipeline
export LANGSMITH_TRACING=true
export LANGSMITH_API_KEY="..."
export LANGSMITH_PROJECT="meu-rag"
```

---

## 4. Blocos fundamentais

### `Document` — a unidade de trabalho

```python
from langchain_core.documents import Document

doc = Document(
    page_content="O prazo de garantia é de 12 meses a partir da emissão da nota.",
    metadata={
        "fonte": "manual_v3.pdf",
        "pagina": 14,
        "categoria": "garantia",
        "atualizado_em": "2026-05-10",
    },
)
```

`metadata` não é enfeite: é o que permite filtrar a busca e citar a fonte na resposta. Preencha bem desde o começo.

### Modelo de chat

```python
from langchain.chat_models import init_chat_model

# interface unificada — troca de provedor sem mexer no resto do código
llm = init_chat_model("claude-sonnet-4-5", model_provider="anthropic", temperature=0)
llm = init_chat_model("gpt-4o-mini", model_provider="openai", temperature=0)

resposta = llm.invoke("Explique RAG em uma frase.")
print(resposta.content)
```

### LCEL — o operador `|`

É o que substituiu as chains prontas. Você compõe as peças:

```python
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

prompt = ChatPromptTemplate.from_template("Explique {assunto} para uma criança.")
chain = prompt | llm | StrOutputParser()

print(chain.invoke({"assunto": "embeddings"}))
```

Todo objeto LCEL ganha `.invoke()`, `.batch()`, `.stream()`, `.ainvoke()`, `.abatch()` e `.astream()` de graça.

---

## 5. Carregando documentos

```python
from langchain_community.document_loaders import PyPDFLoader   # ver nota abaixo

docs = PyPDFLoader("manual.pdf").load()
print(len(docs), docs[0].metadata)
```

> Como `langchain-community` foi arquivado, muitos loaders migraram ou foram substituídos. Na dúvida, **escreva o loader você mesmo** — é quase sempre uma função de 10 linhas e você fica livre de dependência abandonada:

```python
from pathlib import Path
from pypdf import PdfReader
from langchain_core.documents import Document

def carregar_pdf(caminho: str) -> list[Document]:
    leitor = PdfReader(caminho)
    return [
        Document(
            page_content=pagina.extract_text() or "",
            metadata={"fonte": Path(caminho).name, "pagina": i + 1},
        )
        for i, pagina in enumerate(leitor.pages)
    ]

def carregar_pasta(pasta: str) -> list[Document]:
    docs = []
    for arquivo in Path(pasta).rglob("*"):
        if arquivo.suffix.lower() == ".pdf":
            docs.extend(carregar_pdf(str(arquivo)))
        elif arquivo.suffix.lower() in {".md", ".txt"}:
            docs.append(Document(
                page_content=arquivo.read_text(encoding="utf-8"),
                metadata={"fonte": arquivo.name},
            ))
    return docs
```

Carregando de um banco:

```python
import psycopg
from langchain_core.documents import Document

def carregar_do_banco(dsn: str) -> list[Document]:
    with psycopg.connect(dsn) as conn, conn.cursor() as cur:
        cur.execute("SELECT id, titulo, corpo, categoria, atualizado_em FROM artigos")
        return [
            Document(
                page_content=f"{titulo}\n\n{corpo}",
                metadata={"id": id_, "categoria": cat, "atualizado_em": str(dt)},
            )
            for id_, titulo, corpo, cat, dt in cur.fetchall()
        ]
```

---

## 6. Chunking — onde a maioria dos RAGs é ganha ou perdida

Chunk grande demais dilui o embedding e enche o contexto de ruído. Pequeno demais perde o sentido. Essa escolha afeta a qualidade final mais do que a troca de modelo de embedding.

### Recursivo — o padrão para texto corrido

```python
from langchain_text_splitters import RecursiveCharacterTextSplitter

splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=150,
    separators=["\n\n", "\n", ". ", " ", ""],   # tenta quebrar no ponto mais natural
    length_function=len,
    add_start_index=True,        # guarda a posição no doc original
)

chunks = splitter.split_documents(docs)
print(f"{len(docs)} documentos → {len(chunks)} chunks")
```

**Ponto de partida razoável:** `chunk_size=1000`, `chunk_overlap=150`. O overlap evita cortar uma ideia no meio.

### Contando tokens em vez de caracteres

Mais preciso, porque o que enche o contexto é token, não caractere:

```python
splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
    encoding_name="cl100k_base",
    chunk_size=400,        # tokens
    chunk_overlap=60,
)
```

### Markdown — respeitando a estrutura

```python
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter

cabecalhos = [("#", "h1"), ("##", "h2"), ("###", "h3")]

md_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=cabecalhos)
partes = md_splitter.split_text(texto_markdown)   # os títulos viram metadata

# depois quebra as partes que ficaram grandes
chunks = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150) \
    .split_documents(partes)
```

Isso é muito bom para documentação: cada chunk carrega no metadata a seção a que pertence.

### Código-fonte

```python
from langchain_text_splitters import RecursiveCharacterTextSplitter, Language

splitter = RecursiveCharacterTextSplitter.from_language(
    language=Language.PYTHON, chunk_size=800, chunk_overlap=100
)
```

Quebra em `class` e `def` em vez de no meio de uma função. Suporta Python, JS, Go, Java, Rust, entre outras.

### Chunking semântico

Quebra onde o assunto muda, não a cada N caracteres:

```python
from langchain_experimental.text_splitter import SemanticChunker

splitter = SemanticChunker(embeddings, breakpoint_threshold_type="percentile")
chunks = splitter.create_documents([texto])
```

Custa embeddings a mais na indexação. Vale para textos longos e sem estrutura clara.

### Enriquecer o chunk antes de indexar

Truque simples com retorno alto — dar contexto ao chunk isolado:

```python
def enriquecer(chunks: list[Document]) -> list[Document]:
    for c in chunks:
        cabecalho = f"[Documento: {c.metadata.get('fonte')}"
        if secao := c.metadata.get("h2"):
            cabecalho += f" | Seção: {secao}"
        cabecalho += "]\n\n"
        c.page_content = cabecalho + c.page_content
    return chunks
```

Um chunk que diz "o prazo é de 12 meses" sem dizer *prazo de quê* é inútil. Com o cabeçalho, o embedding fica muito melhor.

---

## 7. Embeddings

```python
# API paga, alta qualidade
from langchain_openai import OpenAIEmbeddings
embeddings = OpenAIEmbeddings(model="text-embedding-3-small")   # 1536 dims

# local, grátis, roda em CPU — bom para português
from langchain_huggingface import HuggingFaceEmbeddings
embeddings = HuggingFaceEmbeddings(
    model_name="intfloat/multilingual-e5-large",
    model_kwargs={"device": "cpu"},
    encode_kwargs={"normalize_embeddings": True},
)

vetor = embeddings.embed_query("como funciona a garantia?")
vetores = embeddings.embed_documents(["texto 1", "texto 2"])
```

### Escolhendo para português

| Modelo | Dims | Observação |
|---|---|---|
| `intfloat/multilingual-e5-large` | 1024 | Muito bom em PT. Exige prefixos `query:` e `passage:` |
| `BAAI/bge-m3` | 1024 | Multilíngue, aguenta textos longos |
| `paraphrase-multilingual-MiniLM-L12-v2` | 384 | Leve e rápido, qualidade menor |
| `text-embedding-3-small` (OpenAI) | 1536 | Ótimo custo-benefício, funciona bem em PT |

> Os modelos E5 esperam prefixos: `"query: ..."` na pergunta e `"passage: ..."` no documento. Sem isso, a qualidade cai bastante e sem aviso nenhum.

### Cache de embeddings

Evita pagar duas vezes pelo mesmo texto:

```python
from langchain.embeddings import CacheBackedEmbeddings
from langchain_core.stores import LocalFileStore

store = LocalFileStore("./cache_embeddings/")

embeddings_cache = CacheBackedEmbeddings.from_bytes_store(
    embeddings, store, namespace=embeddings.model,
)
```

---

## 8. Vector stores

### Em memória (para testar)

```python
from langchain_core.vectorstores import InMemoryVectorStore

vs = InMemoryVectorStore.from_documents(chunks, embeddings)
```

### Qdrant

```python
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient

client = QdrantClient(url="http://localhost:6333")

# primeira carga
vs = QdrantVectorStore.from_documents(
    documents=chunks,
    embedding=embeddings,
    url="http://localhost:6333",
    collection_name="base_conhecimento",
)

# conectar em coleção existente
vs = QdrantVectorStore.from_existing_collection(
    embedding=embeddings,
    collection_name="base_conhecimento",
    url="http://localhost:6333",
)
```

### Chroma (arquivo local, zero configuração)

```python
from langchain_chroma import Chroma

vs = Chroma.from_documents(
    documents=chunks,
    embedding=embeddings,
    persist_directory="./chroma_db",
    collection_name="base",
)
```

### PGVector (se você já tem Postgres)

```python
from langchain_postgres import PGVector

vs = PGVector(
    embeddings=embeddings,
    collection_name="base",
    connection="postgresql+psycopg://user:senha@localhost:5432/meudb",
    use_jsonb=True,
)
vs.add_documents(chunks)
```

### Operações comuns (a interface é a mesma em todos)

```python
ids = vs.add_documents(chunks)
vs.add_texts(["texto solto"], metadatas=[{"fonte": "manual"}])

resultados = vs.similarity_search("garantia do produto", k=5)
com_score = vs.similarity_search_with_score("garantia", k=5)
por_vetor = vs.similarity_search_by_vector(vetor, k=5)
diversos = vs.max_marginal_relevance_search("garantia", k=5, fetch_k=30, lambda_mult=0.5)

vs.delete(ids=["id1", "id2"])
```

### Qual escolher

| Vector store | Use quando |
|---|---|
| `InMemoryVectorStore` | Testes, notebooks, CI |
| Chroma | Protótipo, app local, até ~1M chunks |
| Qdrant | Produção, filtros complexos, busca híbrida |
| PGVector | Já tem Postgres e não quer mais um serviço |
| FAISS | Offline, altíssima performance, sem filtros ricos |

---

## 9. Retrievers

Retriever é qualquer coisa que recebe uma string e devolve documentos. É a peça que você pluga no pipeline.

### Do vector store

```python
retriever = vs.as_retriever(search_kwargs={"k": 5})

# MMR — evita 5 chunks quase idênticos
retriever = vs.as_retriever(
    search_type="mmr",
    search_kwargs={"k": 5, "fetch_k": 30, "lambda_mult": 0.5},
)

# corte por score
retriever = vs.as_retriever(
    search_type="similarity_score_threshold",
    search_kwargs={"k": 10, "score_threshold": 0.6},
)

# com filtro de metadata
retriever = vs.as_retriever(
    search_kwargs={"k": 5, "filter": {"categoria": "garantia"}}
)

docs = retriever.invoke("qual o prazo de garantia?")
```

> A sintaxe do `filter` **muda conforme o vector store**. Chroma usa `{"campo": {"$eq": valor}}`; Qdrant aceita um objeto `models.Filter`. Consulte a doc do pacote específico.

### Busca híbrida — BM25 + vetorial

O ponto cego da busca vetorial é termo exato: código de produto, sigla, nome próprio. BM25 cobre isso.

```python
from langchain_community.retrievers import BM25Retriever
from langchain.retrievers import EnsembleRetriever

bm25 = BM25Retriever.from_documents(chunks)
bm25.k = 5

denso = vs.as_retriever(search_kwargs={"k": 5})

hibrido = EnsembleRetriever(retrievers=[bm25, denso], weights=[0.4, 0.6])
docs = hibrido.invoke("erro XR-4471 na inicialização")
```

Se o `EnsembleRetriever` não estiver no seu `langchain`, ele está em `langchain_classic.retrievers`. Ou implemente a fusão você mesmo — é curto e você entende o que está acontecendo:

```python
from langchain_core.documents import Document
from langchain_core.runnables import RunnableLambda

def rrf(listas: list[list[Document]], k: int = 60, top: int = 5) -> list[Document]:
    """Reciprocal Rank Fusion: combina rankings pela posição, não pelo score."""
    pontos, vistos = {}, {}
    for lista in listas:
        for posicao, doc in enumerate(lista):
            chave = doc.page_content[:200]
            pontos[chave] = pontos.get(chave, 0) + 1 / (k + posicao + 1)
            vistos[chave] = doc
    melhores = sorted(pontos.items(), key=lambda x: x[1], reverse=True)[:top]
    return [vistos[chave] for chave, _ in melhores]

hibrido = RunnableLambda(
    lambda q: rrf([bm25.invoke(q), denso.invoke(q)])
)
```

### Multi-query — reformula a pergunta

Uma pergunta mal formulada acha os chunks errados. Essa técnica gera variações e junta os resultados:

```python
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableLambda

prompt_variacoes = ChatPromptTemplate.from_template(
    """Gere 3 formulações alternativas da pergunta abaixo, para melhorar a busca
em uma base de documentos. Uma por linha, sem numeração e sem comentários.

Pergunta: {pergunta}"""
)

gerar_variacoes = (
    prompt_variacoes | llm | StrOutputParser()
    | RunnableLambda(lambda t: [l.strip() for l in t.split("\n") if l.strip()])
)

def buscar_multi(pergunta: str) -> list[Document]:
    consultas = [pergunta] + gerar_variacoes.invoke({"pergunta": pergunta})
    listas = [retriever.invoke(c) for c in consultas]
    return rrf(listas, top=6)

multi_retriever = RunnableLambda(buscar_multi)
```

Custa uma chamada de LLM a mais por pergunta. Costuma valer quando os usuários escrevem de forma vaga.

### Reranking — o maior ganho de qualidade por linha de código

Busca 30 candidatos rápido, reordena com um modelo caro e preciso, devolve os 5 melhores:

```python
from langchain.retrievers import ContextualCompressionRetriever
from langchain_cohere import CohereRerank

reranker = CohereRerank(model="rerank-multilingual-v3.0", top_n=5)

retriever_com_rerank = ContextualCompressionRetriever(
    base_compressor=reranker,
    base_retriever=vs.as_retriever(search_kwargs={"k": 30}),
)
```

Versão local, sem API externa:

```python
from sentence_transformers import CrossEncoder
from langchain_core.runnables import RunnableLambda

cross = CrossEncoder("BAAI/bge-reranker-v2-m3")

def rerankear(pergunta: str, top: int = 5) -> list[Document]:
    candidatos = vs.as_retriever(search_kwargs={"k": 30}).invoke(pergunta)
    pares = [(pergunta, d.page_content) for d in candidatos]
    notas = cross.predict(pares)
    ordenados = sorted(zip(candidatos, notas), key=lambda x: x[1], reverse=True)
    return [doc for doc, _ in ordenados[:top]]

retriever_rerank = RunnableLambda(rerankear)
```

**Se você só puder fazer uma melhoria no seu RAG, faça essa.** O ganho de precisão costuma ser maior que trocar o modelo de embedding ou ajustar chunk size.

### Parent Document — busca no pequeno, entrega o grande

Chunks pequenos têm embedding preciso, mas contexto pobre. Essa técnica resolve os dois lados: indexa chunks pequenos e devolve o trecho grande em volta.

```python
from langchain_core.stores import InMemoryStore
from langchain_core.documents import Document
from langchain_core.runnables import RunnableLambda
import uuid

pai_splitter   = RecursiveCharacterTextSplitter(chunk_size=2000, chunk_overlap=0)
filho_splitter = RecursiveCharacterTextSplitter(chunk_size=400, chunk_overlap=50)

docstore = InMemoryStore()   # em produção: Redis, Postgres, S3

def indexar_pai_filho(docs: list[Document]):
    filhos_para_indexar = []
    pais_para_guardar = []

    for pai in pai_splitter.split_documents(docs):
        pai_id = str(uuid.uuid4())
        pais_para_guardar.append((pai_id, pai))
        for filho in filho_splitter.split_documents([pai]):
            filho.metadata["pai_id"] = pai_id
            filhos_para_indexar.append(filho)

    docstore.mset(pais_para_guardar)
    vs.add_documents(filhos_para_indexar)

def buscar_pais(pergunta: str, k: int = 8) -> list[Document]:
    filhos = vs.similarity_search(pergunta, k=k)
    ids = list(dict.fromkeys(f.metadata["pai_id"] for f in filhos))  # únicos, na ordem
    return [p for p in docstore.mget(ids) if p is not None]

retriever_pai = RunnableLambda(buscar_pais)
```

---

## 10. RAG básico com LCEL

O pipeline completo, sem chain pronta:

```python
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_core.documents import Document

def formatar(docs: list[Document]) -> str:
    return "\n\n---\n\n".join(
        f"[Fonte: {d.metadata.get('fonte', '?')} | Página: {d.metadata.get('pagina', '?')}]\n"
        f"{d.page_content}"
        for d in docs
    )

prompt = ChatPromptTemplate.from_messages([
    ("system",
     "Você responde perguntas usando APENAS o contexto fornecido.\n"
     "Se a resposta não estiver no contexto, diga que não encontrou a informação.\n"
     "Cite a fonte de cada afirmação no formato [fonte, página].\n"
     "Responda em português do Brasil.\n\n"
     "Contexto:\n{contexto}"),
    ("human", "{pergunta}"),
])

rag = (
    {"contexto": retriever | formatar, "pergunta": RunnablePassthrough()}
    | prompt
    | llm
    | StrOutputParser()
)

print(rag.invoke("Qual o prazo de garantia?"))
```

Lendo de baixo para cima: a pergunta entra, vai simultaneamente para o retriever (que busca e formata) e para o campo `pergunta`; os dois alimentam o prompt; o prompt vai para o LLM; a saída vira string.

### Retornando também os documentos usados

Quase sempre você quer mostrar as fontes na interface:

```python
from langchain_core.runnables import RunnableParallel, RunnablePassthrough

gerar = prompt | llm | StrOutputParser()

rag_com_fontes = RunnableParallel(
    {"documentos": retriever, "pergunta": RunnablePassthrough()}
).assign(
    resposta=lambda x: gerar.invoke({
        "contexto": formatar(x["documentos"]),
        "pergunta": x["pergunta"],
    })
)

r = rag_com_fontes.invoke("Qual o prazo de garantia?")
print(r["resposta"])
for d in r["documentos"]:
    print("-", d.metadata["fonte"], d.metadata.get("pagina"))
```

### Citações estruturadas

Em vez de confiar que o modelo formatará as citações direito, force um schema:

```python
from pydantic import BaseModel, Field

class Citacao(BaseModel):
    fonte: str = Field(description="Nome do arquivo de origem")
    trecho: str = Field(description="Trecho exato que sustenta a afirmação")

class RespostaComFontes(BaseModel):
    resposta: str = Field(description="Resposta à pergunta, em português")
    citacoes: list[Citacao] = Field(description="Fontes que sustentam a resposta")
    confianca: float = Field(description="Confiança de 0 a 1")

llm_estruturado = llm.with_structured_output(RespostaComFontes)

rag_estruturado = (
    {"contexto": retriever | formatar, "pergunta": RunnablePassthrough()}
    | prompt
    | llm_estruturado
)

r = rag_estruturado.invoke("Qual o prazo de garantia?")
print(r.resposta, r.confianca)
for c in r.citacoes:
    print(f"  {c.fonte}: {c.trecho[:80]}")
```

---

## 11. RAG conversacional

O problema: o usuário pergunta "e para produtos importados?". Isolada, essa frase não busca nada. Precisa ser reescrita como pergunta autônoma antes de ir ao retriever.

```python
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnableBranch, RunnablePassthrough
from langchain_core.messages import HumanMessage, AIMessage

# 1) reescrever a pergunta usando o histórico
prompt_reescrita = ChatPromptTemplate.from_messages([
    ("system",
     "Dada a conversa e a última pergunta do usuário, reescreva-a como uma "
     "pergunta autônoma, compreensível sem o histórico. Não responda, apenas reescreva."),
    MessagesPlaceholder("historico"),
    ("human", "{pergunta}"),
])

reescrever = prompt_reescrita | llm | StrOutputParser()

# só reescreve se houver histórico
pergunta_autonoma = RunnableBranch(
    (lambda x: not x.get("historico"), lambda x: x["pergunta"]),
    reescrever,
)

# 2) responder com o contexto recuperado
prompt_resposta = ChatPromptTemplate.from_messages([
    ("system", "Responda usando apenas o contexto. Cite as fontes.\n\nContexto:\n{contexto}"),
    MessagesPlaceholder("historico"),
    ("human", "{pergunta}"),
])

rag_conversacional = (
    RunnablePassthrough.assign(pergunta_reescrita=pergunta_autonoma)
    | RunnablePassthrough.assign(
        contexto=lambda x: formatar(retriever.invoke(x["pergunta_reescrita"]))
    )
    | prompt_resposta
    | llm
    | StrOutputParser()
)

historico = []
for pergunta in ["Qual o prazo de garantia?", "E para produtos importados?"]:
    resposta = rag_conversacional.invoke({"pergunta": pergunta, "historico": historico})
    print(f"P: {pergunta}\nR: {resposta}\n")
    historico += [HumanMessage(content=pergunta), AIMessage(content=resposta)]
```

---

## 12. RAG agêntico

Em vez de sempre buscar, o modelo **decide** se e quando buscar — e pode buscar várias vezes, refinando a consulta. É o padrão atual no LangChain 1.x.

```python
from langchain.agents import create_agent
from langchain_core.tools import tool

@tool
def buscar_documentos(consulta: str) -> str:
    """Busca na base de conhecimento interna da empresa.
    Use para perguntas sobre produtos, garantia, políticas e procedimentos."""
    docs = retriever.invoke(consulta)
    if not docs:
        return "Nenhum documento encontrado."
    return "\n\n---\n\n".join(
        f"[{d.metadata.get('fonte', '?')}] {d.page_content}" for d in docs
    )

@tool
def buscar_por_categoria(consulta: str, categoria: str) -> str:
    """Busca restrita a uma categoria específica.
    Categorias válidas: garantia, instalacao, precos, suporte."""
    docs = vs.similarity_search(consulta, k=5, filter={"categoria": categoria})
    return "\n\n".join(d.page_content for d in docs)

agente = create_agent(
    model=llm,
    tools=[buscar_documentos, buscar_por_categoria],
    system_prompt=(
        "Você é um assistente de suporte técnico.\n"
        "Sempre consulte a base antes de responder sobre produtos ou políticas.\n"
        "Se a primeira busca não trouxer o suficiente, reformule e busque de novo.\n"
        "Cite as fontes. Se não encontrar, diga claramente que não encontrou.\n"
        "Responda em português do Brasil."
    ),
)

resultado = agente.invoke({
    "messages": [{"role": "user", "content": "O notebook X220 tem garantia estendida?"}]
})
print(resultado["messages"][-1].content)
```

### Vantagens e custo

| | RAG com LCEL | RAG agêntico |
|---|---|---|
| Latência | Baixa e previsível | Maior, variável |
| Custo | 1 chamada de LLM | N chamadas |
| Perguntas simples | Ótimo | Desperdício |
| Perguntas multi-etapa | Ruim | Muito melhor |
| Depuração | Fácil | Mais difícil |

Comece com LCEL. Migre para agente quando aparecerem perguntas que exigem várias buscas encadeadas.

### Memória entre turnos

```python
from langgraph.checkpoint.memory import InMemorySaver

agente = create_agent(model=llm, tools=[buscar_documentos], checkpointer=InMemorySaver())

config = {"configurable": {"thread_id": "usuario-123"}}

agente.invoke({"messages": [{"role": "user", "content": "Qual a garantia?"}]}, config)
agente.invoke({"messages": [{"role": "user", "content": "E para importados?"}]}, config)
```

O `thread_id` mantém a conversa. Em produção, troque `InMemorySaver` por um checkpointer com Postgres ou Redis.

---

## 13. Streaming

Diferença enorme na percepção de velocidade pelo usuário:

```python
for pedaco in rag.stream("Qual o prazo de garantia?"):
    print(pedaco, end="", flush=True)
```

Streaming de eventos (mostra "buscando..." antes da resposta começar):

```python
async for evento in rag.astream_events("Qual a garantia?", version="v2"):
    tipo = evento["event"]
    if tipo == "on_retriever_end":
        docs = evento["data"]["output"]
        print(f"\n[{len(docs)} documentos encontrados]\n")
    elif tipo == "on_chat_model_stream":
        print(evento["data"]["chunk"].content, end="", flush=True)
```

Com agente:

```python
for pedaco, _ in agente.stream(
    {"messages": [{"role": "user", "content": "Qual a garantia?"}]},
    stream_mode="messages",
):
    if pedaco.content:
        print(pedaco.content, end="", flush=True)
```

---

## 14. Atualização incremental do índice

Reindexar tudo a cada mudança é caro e lento. A API de indexação controla o que já foi processado:

```python
from langchain.indexes import SQLRecordManager, index

namespace = "qdrant/base_conhecimento"
gerenciador = SQLRecordManager(namespace, db_url="sqlite:///registro_index.db")
gerenciador.create_schema()

resultado = index(
    chunks,
    gerenciador,
    vs,
    cleanup="incremental",      # remove versões antigas dos mesmos documentos
    source_id_key="fonte",      # campo do metadata que identifica a origem
)

print(resultado)
# {'num_added': 12, 'num_updated': 0, 'num_skipped': 340, 'num_deleted': 3}
```

Modos de `cleanup`:

- `None` — só adiciona, nunca remove.
- `"incremental"` — ao reprocessar uma `fonte`, apaga os chunks antigos dela. **É o que você quer na maioria dos casos.**
- `"full"` — apaga tudo que não estiver no lote atual. Use só quando o lote é a base inteira.

> Dependendo da versão, `index` e `SQLRecordManager` podem estar em `langchain_classic.indexes`. Se o import acima falhar, tente de lá.

---

## 15. Avaliação

Sem medição, você está ajustando parâmetros no escuro. RAG tem duas coisas separadas a medir: se a **busca** trouxe o certo, e se a **geração** usou o que veio.

### Conjunto de teste mínimo

```python
casos = [
    {
        "pergunta": "Qual o prazo de garantia?",
        "resposta_esperada": "12 meses a partir da emissão da nota fiscal.",
        "fontes_esperadas": ["manual_v3.pdf"],
    },
    # 30–50 casos escritos à mão já dizem muito
]
```

### Métricas de retrieval

```python
def avaliar_retrieval(casos, retriever, k=5):
    acertos_top1 = acertos_topk = 0

    for caso in casos:
        docs = retriever.invoke(caso["pergunta"])[:k]
        fontes = [d.metadata.get("fonte") for d in docs]
        esperadas = set(caso["fontes_esperadas"])

        if fontes and fontes[0] in esperadas:
            acertos_top1 += 1
        if esperadas & set(fontes):
            acertos_topk += 1

    n = len(casos)
    print(f"Acerto no top-1:  {acertos_top1 / n:.1%}")
    print(f"Acerto no top-{k}: {acertos_topk / n:.1%}")
```

Se o acerto no top-k está baixo, o problema é chunking, embedding ou busca. **Não adianta mexer no prompt.**

### Métricas de geração (LLM como juiz)

```python
from pydantic import BaseModel, Field

class Julgamento(BaseModel):
    fundamentada: bool = Field(description="A resposta se apoia apenas no contexto?")
    completa: bool = Field(description="Responde totalmente à pergunta?")
    nota: int = Field(description="Nota de 1 a 5")
    justificativa: str

juiz = init_chat_model("claude-sonnet-4-5", model_provider="anthropic", temperature=0) \
    .with_structured_output(Julgamento)

prompt_juiz = ChatPromptTemplate.from_template(
    """Avalie a resposta de um sistema de RAG.

Pergunta: {pergunta}
Contexto fornecido: {contexto}
Resposta gerada: {resposta}
Resposta de referência: {referencia}

Verifique se a resposta se apoia no contexto (sem inventar) e se está completa."""
)

avaliador = prompt_juiz | juiz
```

### RAGAS

```bash
pip install ragas
```

```python
from ragas import evaluate
from ragas.metrics import faithfulness, answer_relevancy, context_precision, context_recall
from datasets import Dataset

dados = Dataset.from_dict({
    "question": [c["pergunta"] for c in casos],
    "answer": respostas_geradas,
    "contexts": contextos_recuperados,      # list[list[str]]
    "ground_truth": [c["resposta_esperada"] for c in casos],
})

placar = evaluate(dados, metrics=[faithfulness, answer_relevancy,
                                 context_precision, context_recall])
print(placar)
```

- `faithfulness` — a resposta inventou algo fora do contexto?
- `answer_relevancy` — respondeu ao que foi perguntado?
- `context_precision` — o contexto trazido era relevante?
- `context_recall` — trouxe tudo que era necessário?

---

## 16. Produção com FastAPI

```python
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from langchain.chat_models import init_chat_model
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_qdrant import QdrantVectorStore
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

estado = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    embeddings = HuggingFaceEmbeddings(
        model_name="intfloat/multilingual-e5-large",
        encode_kwargs={"normalize_embeddings": True},
    )
    vs = QdrantVectorStore.from_existing_collection(
        embedding=embeddings,
        collection_name="base_conhecimento",
        url=os.environ["QDRANT_URL"],
        api_key=os.environ.get("QDRANT_API_KEY"),
    )
    llm = init_chat_model("claude-sonnet-4-5", model_provider="anthropic", temperature=0)

    prompt = ChatPromptTemplate.from_messages([
        ("system", "Responda apenas com base no contexto. Cite as fontes.\n\n{contexto}"),
        ("human", "{pergunta}"),
    ])

    estado["retriever"] = vs.as_retriever(
        search_type="mmr", search_kwargs={"k": 5, "fetch_k": 30}
    )
    estado["rag"] = (
        {"contexto": estado["retriever"] | formatar, "pergunta": RunnablePassthrough()}
        | prompt | llm | StrOutputParser()
    )
    yield
    estado.clear()

app = FastAPI(lifespan=lifespan)

class Pergunta(BaseModel):
    texto: str
    stream: bool = False

@app.post("/perguntar")
async def perguntar(p: Pergunta):
    if not p.texto.strip():
        raise HTTPException(400, "Pergunta vazia")

    if p.stream:
        async def gerar():
            async for pedaco in estado["rag"].astream(p.texto):
                yield pedaco
        return StreamingResponse(gerar(), media_type="text/plain")

    docs = await estado["retriever"].ainvoke(p.texto)
    resposta = await estado["rag"].ainvoke(p.texto)
    return {
        "resposta": resposta,
        "fontes": [
            {"arquivo": d.metadata.get("fonte"), "pagina": d.metadata.get("pagina")}
            for d in docs
        ],
    }

@app.get("/saude")
async def saude():
    return {"ok": "rag" in estado}
```

### Observabilidade com LangSmith

Com as variáveis de ambiente configuradas, todo `invoke` é rastreado automaticamente. Para adicionar metadados:

```python
resposta = rag.invoke(
    "Qual a garantia?",
    config={
        "run_name": "rag_producao",
        "tags": ["v2", "reranking"],
        "metadata": {"usuario_id": "123", "canal": "web"},
    },
)
```

No painel você vê a árvore completa: quais chunks foram recuperados, o prompt exato, tokens gastos e latência de cada etapa. Depurar RAG sem isso é sofrimento desnecessário.

---

## 17. Diagnóstico: por onde começar quando está ruim

Isole a camada antes de mexer em qualquer coisa:

```python
# 1) O retriever traz o chunk certo?
docs = retriever.invoke("qual o prazo de garantia?")
for d in docs:
    print(d.metadata.get("fonte"), "|", d.page_content[:150])
```

**Se a informação certa não aparece aqui, o problema é de indexação — mexer no prompt não vai adiantar nada.**

```python
# 2) O chunk certo existe na base?
docs = vs.similarity_search("garantia 12 meses nota fiscal", k=20)
```

Se nem com k=20 aparece, o chunk está mal formado ou não foi indexado.

### Tabela de sintomas

| Sintoma | Causa provável | O que fazer |
|---|---|---|
| Não acha o que existe | Chunk mal formado, sem contexto | Enriquecer chunk com cabeçalho; ajustar `chunk_size` |
| Acha o documento errado | Embedding fraco para o domínio | Trocar de modelo; usar busca híbrida |
| Falha em siglas e códigos | Vetorial não pega termo exato | Adicionar BM25 (híbrida) |
| Traz o certo mas em 8º lugar | Ordenação ruim | **Reranking** |
| 5 resultados quase idênticos | Redundância na base | MMR ou Parent Document |
| Resposta inventa dados | Prompt permissivo | Instruir a recusar; validar com structured output |
| Resposta ignora o contexto | Contexto grande demais ou mal formatado | Menos chunks, melhor formatados |
| Pergunta de follow-up falha | Falta reescrita | RAG conversacional (seção 11) |
| Lento demais | Multi-query ou agente desnecessário | Simplificar; usar cache |

---

## 18. Boas práticas

### Indexação

- **Enriqueça o chunk com contexto** (documento, seção). Ganho grande, custo quase zero.
- Metadata rica desde o começo: fonte, data, categoria, versão. Adicionar depois exige reindexar.
- Use `index()` com `cleanup="incremental"` em vez de recriar a base.
- Guarde a versão do modelo de embedding no metadata. Trocar de modelo exige reindexar tudo.

### Busca

- Comece com `k=5` e MMR.
- **Adicione reranking cedo.** É a melhoria de melhor custo-benefício.
- Busca híbrida se o domínio tem códigos, siglas ou nomes próprios.
- Filtro de metadata quando o usuário já sabe a categoria — reduz espaço de busca e melhora precisão.

### Geração

- Instrua explicitamente a recusar quando não souber. Sem isso, o modelo preenche a lacuna com invenção.
- Peça citações e, se possível, valide programaticamente que o trecho citado existe no contexto.
- `temperature=0` para RAG factual.
- Formate o contexto com separadores claros entre documentos.

### Operação

- LangSmith ligado desde o dia 1.
- Conjunto de avaliação com 30–50 casos antes de otimizar qualquer coisa.
- Cache de embeddings para não pagar duas vezes pelo mesmo texto.
- Meça retrieval e geração separadamente.

### Armadilhas frequentes

| Armadilha | Consequência |
|---|---|
| Chunk sem contexto ("o prazo é de 12 meses") | Embedding inútil, nunca é recuperado |
| Metadata pobre | Impossível filtrar ou citar depois |
| Modelo E5 sem os prefixos `query:`/`passage:` | Qualidade cai sem nenhum aviso |
| Trocar embedding sem reindexar | Vetores incompatíveis, resultados aleatórios |
| Otimizar prompt quando o problema é retrieval | Semanas perdidas |
| Agente para tudo | Custo e latência multiplicados sem ganho |
| Vetorizar dados estruturados | Use SQL |
| Nenhuma avaliação | Você não sabe se as mudanças melhoram ou pioram |

---

## 19. Cheat sheet

```python
# MODELO
from langchain.chat_models import init_chat_model
llm = init_chat_model("claude-sonnet-4-5", model_provider="anthropic", temperature=0)

# DOCUMENTO
from langchain_core.documents import Document
Document(page_content="...", metadata={"fonte": "..."})

# CHUNKING
from langchain_text_splitters import (
    RecursiveCharacterTextSplitter, MarkdownHeaderTextSplitter, Language
)
RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)
RecursiveCharacterTextSplitter.from_tiktoken_encoder(chunk_size=400)
RecursiveCharacterTextSplitter.from_language(language=Language.PYTHON)

# EMBEDDINGS
from langchain_openai import OpenAIEmbeddings
from langchain_huggingface import HuggingFaceEmbeddings
embeddings.embed_query(texto)
embeddings.embed_documents(lista)

# VECTOR STORE
vs = QdrantVectorStore.from_documents(chunks, embeddings, url=..., collection_name=...)
vs.add_documents(chunks)
vs.similarity_search(q, k=5)
vs.similarity_search_with_score(q, k=5)
vs.max_marginal_relevance_search(q, k=5, fetch_k=30)
vs.delete(ids=[...])

# RETRIEVER
vs.as_retriever(search_kwargs={"k": 5})
vs.as_retriever(search_type="mmr", search_kwargs={"k": 5, "fetch_k": 30})
vs.as_retriever(search_type="similarity_score_threshold",
                search_kwargs={"score_threshold": 0.6})
retriever.invoke("pergunta")

# LCEL
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import (
    RunnablePassthrough, RunnableParallel, RunnableLambda, RunnableBranch
)
chain = prompt | llm | StrOutputParser()
chain.invoke(x); chain.batch([...]); chain.stream(x)
await chain.ainvoke(x); chain.astream_events(x, version="v2")

# STRUCTURED OUTPUT
llm.with_structured_output(MeuSchemaPydantic)

# AGENTE
from langchain.agents import create_agent
from langchain_core.tools import tool
agente = create_agent(model=llm, tools=[...], system_prompt="...")
agente.invoke({"messages": [{"role": "user", "content": "..."}]})

# INDEXAÇÃO INCREMENTAL
from langchain.indexes import SQLRecordManager, index
index(docs, gerenciador, vs, cleanup="incremental", source_id_key="fonte")
```

### Ordem de otimização (do maior para o menor retorno)

1. **Reranking** — quase sempre o maior ganho isolado
2. **Enriquecer chunks com contexto** — barato e muito eficaz
3. **Busca híbrida** (BM25 + vetorial) — essencial se há códigos e siglas
4. **Ajustar chunk size e overlap** — teste 500, 1000, 1500
5. **Trocar modelo de embedding** — só depois dos anteriores
6. **Multi-query** — quando as perguntas são vagas
7. **RAG agêntico** — quando as perguntas exigem várias buscas

---

## 20. Links

- Documentação: https://docs.langchain.com/oss/python/langchain/overview
- Referência da API: https://reference.langchain.com/python/langchain/langchain/
- LangGraph: https://docs.langchain.com/oss/python/langgraph/overview
- Política de versões: https://docs.langchain.com/oss/python/versioning
- LangChain Academy (cursos gratuitos): https://academy.langchain.com/
- Repositório: https://github.com/langchain-ai/langchain

> **Nota sobre imports:** o LangChain reorganiza pacotes com frequência. Se um import deste guia falhar, procure o componente em `langchain_classic` (legados) ou no pacote da integração específica (`langchain_<provedor>`). A referência da API acima é a fonte definitiva de onde cada coisa mora hoje.
