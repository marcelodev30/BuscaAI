# Revisão de Python para o BuscaAI
**Conceitos essenciais com exemplos diretos do projeto**

Cada seção explica o conceito, por que ele existe, e mostra como aparece
no BuscaAI. Não é um tutorial de Python do zero — é uma revisão orientada
ao que você vai precisar escrever e ler durante o desenvolvimento.

---

## Mapa de conhecimentos necessários

```
NÍVEL FUNDAMENTAL (você precisa dominar antes de começar)
  ✓ Tipos básicos: str, int, float, bool, None
  ✓ Estruturas: list, dict, tuple, set
  ✓ Controle de fluxo: if/elif/else, for, while
  ✓ Funções: def, argumentos, return
  ✓ Classes: __init__, self, métodos
  ✓ Imports: import, from...import, pacotes

NÍVEL INTERMEDIÁRIO (vai usar todo dia no BuscaAI)
  ✓ Type hints e anotações de tipo
  ✓ Dataclasses
  ✓ Herança e classes abstratas (ABC)
  ✓ List/dict comprehensions
  ✓ Context managers (with)
  ✓ Exceções e tratamento de erros
  ✓ Variáveis de ambiente e configuração
  ✓ Leitura e escrita de arquivos (Pathlib)
  ✓ JSON
  ✓ Expressões regulares (re)

NÍVEL AVANÇADO (necessário para as partes específicas)
  ✓ Async/await e asyncio
  ✓ Generators e iteradores
  ✓ Decorators
  ✓ Protocols e duck typing
  ✓ Concorrência com asyncio.gather
  ✓ SQLite com aiosqlite
  ✓ Testes com pytest
```

---

## Sumário

1. [Type hints](#1-type-hints)
2. [Dataclasses](#2-dataclasses)
3. [Classes abstratas e interfaces](#3-classes-abstratas-e-interfaces-abc)
4. [List e dict comprehensions](#4-list-e-dict-comprehensions)
5. [Context managers](#5-context-managers-with)
6. [Tratamento de exceções](#6-tratamento-de-exceções)
7. [Variáveis de ambiente e configuração](#7-variáveis-de-ambiente-e-configuração)
8. [Pathlib — arquivos e pastas](#8-pathlib--arquivos-e-pastas)
9. [Async e await](#9-async-e-await)
10. [Generators](#10-generators)
11. [Decorators](#11-decorators)
12. [Expressões regulares](#12-expressões-regulares)
13. [Concorrência com asyncio](#13-concorrência-com-asyncio)
14. [SQLite com Python](#14-sqlite-com-python)
15. [Testes com pytest](#15-testes-com-pytest)
16. [Estrutura de pacote Python](#16-estrutura-de-pacote-python)

---

## 1. Type hints

### O que é e por que existe

Type hints são anotações que dizem qual tipo cada variável, parâmetro e
retorno deve ter. Python não as obriga — o código roda sem elas.
Mas elas existem por três razões práticas:

```
1. O editor (VSCode, PyCharm) consegue autocompletar e alertar sobre erros
2. Outros desenvolvedores (e você mesmo no futuro) entendem o código mais rápido
3. Ferramentas como mypy detectam bugs antes de rodar
```

### Sintaxe básica

```python
# sem type hints (funciona, mas é ambíguo)
def processar(texto, max_tokens):
    return texto[:max_tokens]

# com type hints (claro o que entra e o que sai)
def processar(texto: str, max_tokens: int) -> str:
    return texto[:max_tokens]
```

### Os tipos mais usados no BuscaAI

```python
from typing import Optional, Union, Any
from collections.abc import Generator, AsyncGenerator

# tipos simples
nome: str = "BuscaAI"
versao: int = 1
custo: float = 0.00042
ativo: bool = True
nulo: None = None

# coleções
chunks: list[str] = []
metadados: dict[str, Any] = {}
ids: tuple[str, ...] = ()
estrategias: set[str] = {"hybrid", "dense", "lexical"}

# opcional — pode ser o tipo ou None
titulo: Optional[str] = None       # equivale a: str | None (Python 3.10+)
score: Optional[float] = None

# union — pode ser um ou outro
resultado: Union[str, list[str]]   # equivale a: str | list[str]

# TypedDict — dict com campos fixos e tipos conhecidos
from typing import TypedDict

class ChunkPayload(TypedDict):
    chunk_id:   str
    doc_id:     str
    texto:      str
    score:      float
    pagina:     Optional[int]
```

### Por que TypedDict importa para o BuscaAI

O LangGraph usa um `TypedDict` para o **estado do grafo**. Cada nó do grafo
lê e escreve nesse estado. O TypedDict garante que todos os nós
concordam sobre o que o estado contém:

```python
from typing import TypedDict, Optional

# o estado compartilhado entre todos os nós do pipeline
class RAGState(TypedDict):
    query:        str
    query_embedding: Optional[list[float]]
    chunks:       list[dict]
    resposta:     Optional[str]
    session_id:   Optional[str]
    custo_total:  float
    cache_hit:    bool

# cada nó recebe e retorna esse mesmo TypedDict
def no_retrieval(state: RAGState) -> RAGState:
    chunks = buscar(state["query"], state["query_embedding"])
    return {**state, "chunks": chunks}   # **state copia tudo, sobrescreve chunks
```

### list, dict e set com tipos genéricos

```python
# Python 3.9+: usa list[], dict[], set[] diretamente
chunks:     list[str]
payload:    dict[str, float]
ids_vistos: set[str]

# Python 3.8: precisa importar de typing
from typing import List, Dict, Set
chunks: List[str]
```

---

## 2. Dataclasses

### O que é e por que existe

Uma dataclass é uma forma de criar classes que apenas **guardam dados**,
sem precisar escrever `__init__`, `__repr__` e `__eq__` manualmente.

```python
# sem dataclass — muito código boilerplate
class Chunk:
    def __init__(self, texto: str, doc_id: str, n_tokens: int):
        self.texto    = texto
        self.doc_id   = doc_id
        self.n_tokens = n_tokens

    def __repr__(self):
        return f"Chunk(doc_id={self.doc_id!r}, n_tokens={self.n_tokens})"

    def __eq__(self, other):
        return (self.texto, self.doc_id) == (other.texto, other.doc_id)


# com dataclass — menos código, mesmo resultado
from dataclasses import dataclass, field

@dataclass
class Chunk:
    texto:      str
    doc_id:     str
    n_tokens:   int
    pagina:     int   = 0           # valor padrão
    metadados:  dict  = field(default_factory=dict)  # padrão mutável
```

### Por que `field(default_factory=dict)` em vez de `= {}`

```python
# ERRADO — todos os objetos compartilham o mesmo dicionário
@dataclass
class Chunk:
    metadados: dict = {}     # bug: dict mutável como padrão


# CORRETO — cada objeto cria seu próprio dicionário
@dataclass
class Chunk:
    metadados: dict = field(default_factory=dict)
```

Regra: para valores padrão que são **listas, dicionários ou conjuntos**,
sempre use `field(default_factory=...)`.

### Dataclasses no BuscaAI

```python
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class Document:
    """Resultado do pré-processamento — entrada do chunking."""
    # identidade
    doc_id:     str              # hash SHA-256
    source_id:  str              # caminho relativo ou ID da fonte
    filename:   str

    # conteúdo
    text:       str

    # metadados do arquivo
    mime_type:  str  = "application/octet-stream"
    n_paginas:  int  = 0
    tamanho_bytes: int = 0

    # metadados do cabeçalho
    titulo:     str  = ""
    autor:      str  = ""
    idioma:     str  = "?"

    # metadados de ingestão
    source:     str  = "upload"
    collection: str  = "default"
    status:     str  = "pending"

    # NLP
    tipo_documento: str  = "generico"
    entidades:      dict = field(default_factory=dict)

    # limpeza
    chars_bruto:  int = 0
    chars_limpo:  int = 0

    def reducao_pct(self) -> float:
        if self.chars_bruto == 0:
            return 0.0
        return (self.chars_bruto - self.chars_limpo) / self.chars_bruto * 100


@dataclass
class Chunk:
    """Fragmento de texto pronto para embedding."""
    texto:      str
    doc_id:     str
    chunk_id:   str
    posicao:    int
    n_tokens:   int
    pagina:     int  = 0
    estrategia: str  = "recursive"
    metadados:  dict = field(default_factory=dict)
```

### `@dataclass(frozen=True)` — imutável

Quando você não quer que os dados sejam alterados após a criação:

```python
@dataclass(frozen=True)
class EmbeddingConfig:
    """Configuração que não pode ser alterada em runtime."""
    provider:  str
    model:     str
    dimension: int
    batch_size: int = 100

config = EmbeddingConfig(provider="openai", model="text-3-small", dimension=1536)
config.dimension = 768   # TypeError: cannot assign to field 'dimension'
```

---

## 3. Classes abstratas e interfaces (ABC)

### O que é e por que existe

O BuscaAI é **plugável** — você pode trocar o banco vetorial, o modelo de
embedding, o LLM e o loader sem alterar o core. Isso é possível porque
cada componente implementa uma **interface comum**.

Uma interface é um contrato: "qualquer coisa que queira ser um Loader
deve ter o método `load()`". Em Python, isso se faz com ABC
(Abstract Base Class):

```python
from abc import ABC, abstractmethod

class BaseLoader(ABC):
    """
    Interface que todo loader deve implementar.
    Se você criar uma classe que herda de BaseLoader mas não
    implementar load(), Python vai lançar TypeError na instanciação.
    """

    @abstractmethod
    def load(self, source: str) -> list[Document]:
        """Carrega documentos de uma fonte e retorna lista de Document."""
        ...

    @abstractmethod
    def validate_conn(self) -> bool:
        """Verifica se a conexão com a fonte está funcionando."""
        ...

    def close(self) -> None:
        """Fecha a conexão. Implementação padrão não faz nada."""
        pass
```

### Por que isso é melhor que duck typing puro

```python
# duck typing puro — nada impede esquecer um método
class MeuLoader:
    def load(self, source):
        return []
    # esqueceu validate_conn — só vai perceber quando usar

# com ABC — Python avisa imediatamente
class MeuLoader(BaseLoader):
    def load(self, source: str) -> list[Document]:
        return []
    # TypeError: Can't instantiate abstract class MeuLoader
    # with abstract method validate_conn
```

### Todas as interfaces do BuscaAI

```python
from abc import ABC, abstractmethod
from typing import AsyncGenerator


class BaseLoader(ABC):
    @abstractmethod
    def load(self, source: str) -> list[Document]: ...
    @abstractmethod
    def validate_conn(self) -> bool: ...


class BaseEmbedder(ABC):
    @abstractmethod
    async def embed_texts(self, textos: list[str]) -> list[list[float]]: ...
    @abstractmethod
    async def embed_query(self, query: str) -> list[float]: ...


class BaseVectorStore(ABC):
    @abstractmethod
    async def upsert(self, chunks: list[Chunk], vetores: list[list[float]]) -> None: ...
    @abstractmethod
    async def search(self, query_vector: list[float], top_k: int,
                     filters: dict | None = None) -> list[dict]: ...
    @abstractmethod
    async def delete(self, doc_id: str) -> int: ...


class BaseReranker(ABC):
    @abstractmethod
    async def rerank(self, query: str, chunks: list[dict],
                     top_n: int) -> list[dict]: ...


class BaseLLMProvider(ABC):
    @abstractmethod
    async def gerar(self, query: str, chunks: list[dict]) -> dict: ...
    @abstractmethod
    async def stream(self, query: str,
                     chunks: list[dict]) -> AsyncGenerator[str, None]: ...
```

### Implementação concreta

```python
class QdrantVectorStore(BaseVectorStore):
    """Implementação do banco vetorial usando Qdrant."""

    def __init__(self, config: dict):
        from qdrant_client import AsyncQdrantClient
        self.client     = AsyncQdrantClient(
            host=config["host"], port=config["port"]
        )
        self.collection = config["collection"]

    async def upsert(self, chunks, vetores):
        from qdrant_client.models import PointStruct
        pontos = [
            PointStruct(
                id      = i,
                vector  = vetores[i],
                payload = chunk.metadados,
            )
            for i, chunk in enumerate(chunks)
        ]
        await self.client.upsert(
            collection_name=self.collection, points=pontos
        )

    async def search(self, query_vector, top_k, filters=None):
        resultado = await self.client.search(
            collection_name=self.collection,
            query_vector=query_vector,
            limit=top_k,
            query_filter=filters,
        )
        return [
            {"chunk_id": r.id, "score": r.score, **r.payload}
            for r in resultado
        ]

    async def delete(self, doc_id: str) -> int:
        resultado = await self.client.delete(
            collection_name=self.collection,
            points_selector={"filter": {"must": [
                {"key": "doc_id", "match": {"value": doc_id}}
            ]}}
        )
        return resultado.deleted


# o pipeline não sabe qual banco está usando — só usa a interface
class RetrievalPipeline:
    def __init__(self, vectorstore: BaseVectorStore, reranker: BaseReranker):
        self.vectorstore = vectorstore
        self.reranker    = reranker

    async def buscar(self, query: str, embedding: list[float]) -> list[dict]:
        chunks = await self.vectorstore.search(embedding, top_k=50)
        return await self.reranker.rerank(query, chunks, top_n=5)
```

---

## 4. List e dict comprehensions

### O que são

Formas compactas de criar listas e dicionários a partir de iteráveis.
São mais rápidas que loops equivalentes e mais pythônicas.

```python
# loop tradicional
resultados = []
for chunk in chunks:
    if chunk["score"] > 0.7:
        resultados.append(chunk["texto"])

# equivalente com list comprehension
resultados = [c["texto"] for c in chunks if c["score"] > 0.7]
```

### Onde aparecem no BuscaAI

```python
# extrair textos de uma lista de chunks para embedding
textos = [chunk.texto for chunk in chunks]

# filtrar chunks por score mínimo
relevantes = [c for c in chunks if c["score"] >= min_score]

# extrair IDs para filtro do banco
ids = [c["chunk_id"] for c in candidatos_lexicais]

# formatar fontes para a resposta da API
fontes = [
    {
        "fonte":   c["filename"],
        "pagina":  c.get("pagina", 0),
        "score":   round(c["score"], 3),
        "trecho":  c["texto"][:200],
    }
    for c in chunks_rerankeados[:5]
]

# dict comprehension — inverter dicionário
modelo_por_provider = {v: k for k, v in PROVIDERS.items()}

# enumerar chunks com posição
chunks_com_pos = {
    f"chunk_{i}": chunk.texto
    for i, chunk in enumerate(chunks)
}
```

### Set comprehension — deduplicar

```python
# todos os sources únicos na lista de chunks
sources_unicos = {chunk["source"] for chunk in chunks}

# hashes já indexados — para deduplicação
hashes_existentes = {row["hash"] for row in await db.fetch_all("SELECT hash FROM documents")}
```

### Generator expression — lazy, economiza memória

```python
# lista: processa tudo de uma vez (usa memória)
textos = [chunk.texto for chunk in milhoes_de_chunks]

# generator: processa um por vez (econômico)
textos = (chunk.texto for chunk in milhoes_de_chunks)

# útil para passar para funções que iteram
total_chars = sum(len(c.texto) for c in chunks)
tem_longo   = any(len(c.texto) > 1000 for c in chunks)
```

---

## 5. Context managers (`with`)

### O que são e por que existem

Context managers garantem que **recursos sejam liberados** mesmo se
ocorrer um erro — conexões de banco, arquivos, locks. São a versão
Python de try/finally, mas mais limpa.

```python
# sem context manager — precisa lembrar de fechar
conn = sqlite3.connect("buscaai.db")
try:
    conn.execute("INSERT ...")
    conn.commit()
finally:
    conn.close()   # precisa estar aqui mesmo se der erro

# com context manager — fecha automaticamente
with sqlite3.connect("buscaai.db") as conn:
    conn.execute("INSERT ...")
    conn.commit()
# conn.close() chamado automaticamente aqui
```

### Como funciona por baixo

```python
# o que o with faz internamente
obj = gerenciador.__enter__()
try:
    # bloco do with
finally:
    gerenciador.__exit__(exc_type, exc_val, exc_tb)
```

### Context managers no BuscaAI

```python
import fitz  # PyMuPDF
from pathlib import Path
import aiofiles
import aiosqlite

# PDF com PyMuPDF
with fitz.open("contrato.pdf") as doc:
    for page in doc:
        texto = page.get_text("text")
# doc.close() automático

# arquivo com Pathlib (síncrono)
with open("log.txt", "a", encoding="utf-8") as f:
    f.write("job iniciado\n")

# arquivo async (dentro de função async)
async def salvar_log(mensagem: str):
    async with aiofiles.open("log.txt", "a") as f:
        await f.write(mensagem + "\n")

# SQLite async
async def buscar_job(job_id: str) -> dict:
    async with aiosqlite.connect("buscaai.db") as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM jobs WHERE job_id = ?", (job_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else {}
# db.close() e cursor.close() automáticos
```

### Criar seu próprio context manager

```python
from contextlib import asynccontextmanager
import time

@asynccontextmanager
async def medir_tempo(nome: str):
    """Mede o tempo de execução de um bloco."""
    inicio = time.perf_counter()
    try:
        yield
    finally:
        duracao = (time.perf_counter() - inicio) * 1000
        print(f"{nome}: {duracao:.1f}ms")

# uso
async def buscar(query: str):
    async with medir_tempo("retrieval"):
        resultado = await vectorstore.search(embedding, top_k=50)
    async with medir_tempo("reranker"):
        final = await reranker.rerank(query, resultado)
    return final
```

---

## 6. Tratamento de exceções

### A hierarquia de exceções

```
BaseException
  └── Exception
        ├── ValueError     — valor inválido (ex: token muito longo)
        ├── TypeError      — tipo errado
        ├── KeyError       — chave ausente no dict
        ├── FileNotFoundError — arquivo não existe
        ├── ConnectionError   — falha de rede
        ├── TimeoutError      — operação demorou demais
        └── ... (suas próprias exceções)
```

### Exceções customizadas do BuscaAI

```python
class BuscaAIError(Exception):
    """Exceção base do BuscaAI."""
    pass

class IngestaoError(BuscaAIError):
    def __init__(self, job_id: str, motivo: str):
        self.job_id = job_id
        self.motivo = motivo
        super().__init__(f"Falha na ingestão do job {job_id}: {motivo}")

class ArquivoMuitoGrandeError(IngestaoError):
    def __init__(self, filename: str, tamanho_mb: float, limite_mb: float):
        self.filename   = filename
        self.tamanho_mb = tamanho_mb
        job_id = "N/A"
        motivo = f"arquivo {filename} ({tamanho_mb:.1f}MB) excede {limite_mb}MB"
        super().__init__(job_id, motivo)

class BancoIndisponivelError(BuscaAIError):
    def __init__(self, backend: str, mensagem: str):
        super().__init__(f"Banco {backend} indisponível: {mensagem}")
```

### Padrões de tratamento usados no BuscaAI

```python
import asyncio

# 1. capturar, logar e reraise (propaga o erro mas registra)
async def processar_documento(caminho: str):
    try:
        doc = await extrair(caminho)
        return doc
    except Exception as e:
        logger.error(f"Falha ao processar {caminho}: {e}", exc_info=True)
        raise  # propaga o erro original

# 2. capturar e retornar None (falha silenciosa controlada)
async def buscar_cache(query_hash: str) -> dict | None:
    try:
        return await redis.get(query_hash)
    except ConnectionError:
        logger.warning("Redis indisponível — continuando sem cache")
        return None   # degradação graciosa

# 3. retry com backoff exponencial
async def embed_com_retry(textos: list[str], max_tentativas: int = 3) -> list:
    for tentativa in range(max_tentativas):
        try:
            return await embedder.embed_texts(textos)
        except (ConnectionError, TimeoutError) as e:
            if tentativa == max_tentativas - 1:
                raise   # última tentativa — propaga
            espera = 2 ** tentativa   # 1s, 2s, 4s
            logger.warning(f"Tentativa {tentativa+1} falhou, aguardando {espera}s")
            await asyncio.sleep(espera)

# 4. capturar múltiplos tipos
async def validar_arquivo(caminho: str):
    try:
        tamanho = caminho.stat().st_size
        if tamanho > 100 * 1024 * 1024:
            raise ArquivoMuitoGrandeError(caminho.name, tamanho/1e6, 100)
        return True
    except FileNotFoundError:
        raise IngestaoError("N/A", f"Arquivo não encontrado: {caminho}")
    except PermissionError:
        raise IngestaoError("N/A", f"Sem permissão para ler: {caminho}")

# 5. finally — sempre executa (limpa recursos)
async def ingerir(job_id: str, caminho: str):
    await db.update_status(job_id, "processing")
    try:
        resultado = await processar(caminho)
        await db.update_status(job_id, "completed")
        return resultado
    except Exception as e:
        await db.update_status(job_id, "failed", erro=str(e))
        raise
    finally:
        # sempre executa — mesmo se der erro
        logger.info(f"Job {job_id} finalizado")
```

---

## 7. Variáveis de ambiente e configuração

### Por que não hardcodar credenciais

```python
# NUNCA faça isso — fica no git e vaza
OPENAI_API_KEY = "sk-abc123..."
QDRANT_HOST    = "meu-servidor.com"

# SEMPRE via variável de ambiente
import os
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
```

### O padrão do BuscaAI com python-dotenv

```python
# .env (não vai no git — está no .gitignore)
OPENAI_API_KEY=sk-...
QDRANT_HOST=localhost
QDRANT_PORT=6333
SECRET_KEY=minha-chave-super-secreta

# carrega o .env para os.environ
from dotenv import load_dotenv
load_dotenv()

# acessa
api_key = os.environ.get("OPENAI_API_KEY")
host    = os.environ.get("QDRANT_HOST", "localhost")   # segundo arg = padrão
port    = int(os.environ.get("QDRANT_PORT", "6333"))   # converte o tipo
```

### O rag_settings.py — configuração centralizada

```python
# rag_settings.py — inspirado no Django settings.py
import os
from dotenv import load_dotenv

load_dotenv()

VECTOR_STORE = {
    "backend":    "qdrant",
    "host":       os.environ.get("QDRANT_HOST", "localhost"),
    "port":       int(os.environ.get("QDRANT_PORT", "6333")),
    "collection": "buscaai",
}

EMBEDDINGS = {
    "dense": {
        "provider":   "openai",
        "model":      "text-embedding-3-small",
        "dimension":  1536,
        "batch_size": 100,
    },
    "sparse": {"model": "splade"},
}

# carregar e validar
import importlib

def carregar_settings(modulo: str = "rag_settings") -> object:
    """Carrega o módulo de settings e valida campos obrigatórios."""
    settings = importlib.import_module(modulo)

    obrigatorios = ["VECTOR_STORE", "EMBEDDINGS", "CHUNKING"]
    for campo in obrigatorios:
        if not hasattr(settings, campo):
            raise ValueError(f"rag_settings.py não tem o campo '{campo}'")

    return settings
```

---

## 8. Pathlib — arquivos e pastas

### Por que Pathlib em vez de `os.path`

```python
# antigo — concatenação manual, diferente em Windows/Linux
import os
caminho = os.path.join("docs", "contratos", "arquivo.pdf")
nome    = os.path.basename(caminho)
pasta   = os.path.dirname(caminho)

# moderno — orientado a objeto, funciona em todos os SOs
from pathlib import Path
caminho = Path("docs") / "contratos" / "arquivo.pdf"  # usa /
nome    = caminho.name          # "arquivo.pdf"
stem    = caminho.stem          # "arquivo"
sufixo  = caminho.suffix        # ".pdf"
pasta   = caminho.parent        # Path("docs/contratos")
```

### Pathlib no BuscaAI

```python
from pathlib import Path

# listar todos os PDFs numa pasta (recursivo)
pasta = Path("./meus_documentos")
pdfs  = list(pasta.glob("**/*.pdf"))

# ler e escrever
texto = Path("documento.txt").read_text(encoding="utf-8")
Path("saida.md").write_text(markdown, encoding="utf-8")

# verificar e criar
if not pasta.exists():
    pasta.mkdir(parents=True, exist_ok=True)

# tamanho do arquivo
tamanho_bytes = Path("contrato.pdf").stat().st_size
tamanho_mb    = tamanho_bytes / (1024 * 1024)

# validar extensão
def extensao_suportada(caminho: Path) -> bool:
    EXTENSOES = {".pdf", ".docx", ".pptx", ".csv", ".txt", ".md", ".html"}
    return caminho.suffix.lower() in EXTENSOES

# processar pasta inteira
def listar_documentos(pasta: str) -> list[Path]:
    p = Path(pasta)
    return [
        arq for arq in p.rglob("*")
        if arq.is_file() and extensao_suportada(arq)
    ]
```

---

## 9. Async e await

### O problema que async resolve

```python
# SÍNCRONO — bloqueia enquanto espera
def buscar_sync():
    resultado1 = chamar_qdrant()    # espera 50ms aqui
    resultado2 = chamar_redis()     # espera 5ms aqui
    resultado3 = chamar_llm()       # espera 800ms aqui
    return resultado1, resultado2, resultado3
# total: 855ms — a thread ficou bloqueada esperando

# ASSÍNCRONO — libera a thread enquanto espera
async def buscar_async():
    resultado1 = await chamar_qdrant()   # suspende, faz outra coisa
    resultado2 = await chamar_redis()    # suspende, faz outra coisa
    resultado3 = await chamar_llm()      # suspende, faz outra coisa
    return resultado1, resultado2, resultado3
# total: ainda 855ms — mas a thread atendeu outras queries enquanto esperava
```

**A diferença crucial:** async não é mais rápido para uma única requisição.
É mais rápido quando tem **muitas requisições simultâneas** — porque o servidor
pode atender 50 queries ao mesmo tempo enquanto cada uma espera sua vez.

### Sintaxe essencial

```python
import asyncio

# função assíncrona — retorna uma coroutine quando chamada
async def minha_funcao():
    await asyncio.sleep(1)    # yield control for 1 second
    return "resultado"

# para rodar uma coroutine
asyncio.run(minha_funcao())

# dentro de uma função async, usa await
async def pipeline():
    embedding = await embedder.embed_query("minha query")
    chunks    = await vectorstore.search(embedding, top_k=50)
    resposta  = await llm.gerar("minha query", chunks)
    return resposta
```

### Await vs chamada normal — o que pode confundir

```python
# SEM await — retorna um objeto coroutine, não executa
coro = embedder.embed_query("query")   # ainda não rodou nada!
type(coro)  # <class 'coroutine'>

# COM await — executa e espera o resultado
embedding = await embedder.embed_query("query")   # agora executou
```

### Async no BuscaAI — exemplos reais

```python
# rota FastAPI async
from fastapi import FastAPI

app = FastAPI()

@app.post("/search")
async def search(request: SearchRequest) -> SearchResponse:
    # todo o pipeline roda de forma assíncrona
    embedding = await embedder.embed_query(request.query)
    chunks    = await vectorstore.search(embedding, top_k=50)
    chunks    = await reranker.rerank(request.query, chunks, top_n=5)
    resultado = await llm.gerar(request.query, chunks)
    return SearchResponse(**resultado)


# streaming com SSE
from fastapi.responses import StreamingResponse

@app.post("/search/stream")
async def search_stream(request: SearchRequest):
    async def gerador():
        async for token in llm.stream(request.query, chunks):
            yield f"data: {token}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(gerador(), media_type="text/event-stream")
```

---

## 10. Generators

### O que são

Generators são funções que **pausam e retomam** a execução, produzindo
valores um por vez em vez de computar tudo de uma vez.

```python
# função normal — cria toda a lista na memória
def chunks_de(texto: str, tamanho: int) -> list[str]:
    resultado = []
    for i in range(0, len(texto), tamanho):
        resultado.append(texto[i:i+tamanho])
    return resultado   # retorna a lista completa

# generator — produz um chunk por vez
def chunks_de(texto: str, tamanho: int):
    for i in range(0, len(texto), tamanho):
        yield texto[i:i+tamanho]   # yield: pausa e entrega um valor
```

### Por que importa para o BuscaAI

Quando você tem 100.000 documentos para ingerir, não quer carregar
tudo na memória de uma vez. Generators permitem processar um por vez:

```python
from pathlib import Path
from typing import Generator

def iterar_documentos(pasta: str) -> Generator[Document, None, None]:
    """Gera documentos um por vez — não carrega todos na memória."""
    for caminho in Path(pasta).rglob("*.pdf"):
        try:
            doc = processar_pdf(caminho)
            yield doc
        except Exception as e:
            logger.warning(f"Pulando {caminho.name}: {e}")
            continue   # próximo documento

# uso — processa um documento por vez
for doc in iterar_documentos("./meus_docs/"):
    chunks = chunkar(doc)
    vetores = embedder.embed_batch(chunks)
    vectorstore.upsert(chunks, vetores)
```

### Async generator — para streaming

```python
from typing import AsyncGenerator

async def stream_tokens(query: str, chunks: list[dict]) -> AsyncGenerator[str, None]:
    """Produz tokens conforme o LLM os gera."""
    async for chunk in await litellm.acompletion(
        model="gpt-4o-mini",
        messages=montar_prompt(query, chunks),
        stream=True,
    ):
        token = chunk.choices[0].delta.content
        if token:
            yield token   # entrega token por token ao cliente SSE

# uso no endpoint FastAPI
async def endpoint_stream():
    async for token in stream_tokens(query, chunks):
        yield f"data: {token}\n\n"
```

### Batch generator — processar em lotes

```python
def em_lotes(items: list, tamanho_lote: int):
    """Divide uma lista em sublistas de tamanho_lote."""
    for i in range(0, len(items), tamanho_lote):
        yield items[i : i + tamanho_lote]

# processar 10.000 chunks em lotes de 100 (limite da API OpenAI)
todos_chunks = [c.texto for c in meus_chunks]

for lote in em_lotes(todos_chunks, 100):
    vetores = await embedder.embed_texts(lote)
    # processa o lote...
```

---

## 11. Decorators

### O que são

Decorators são funções que **envolvem outra função** para adicionar
comportamento sem alterar o código original.

```python
# o @meu_decorator é equivalente a:
@meu_decorator
def minha_funcao():
    ...
# ... isso:
minha_funcao = meu_decorator(minha_funcao)
```

### Decorators que você vai usar no BuscaAI

```python
# 1. FastAPI routes — registrar endpoints
@app.post("/search")
async def buscar(request: SearchRequest): ...

# 2. dataclass
@dataclass
class Chunk: ...

# 3. abstractmethod (da ABC)
@abstractmethod
def load(self, source: str) -> list[Document]: ...

# 4. property — campo calculado na dataclass/classe
class Document:
    @property
    def reducao_pct(self) -> float:
        if self.chars_bruto == 0: return 0.0
        return (self.chars_bruto - self.chars_limpo) / self.chars_bruto * 100

doc = Document(...)
print(doc.reducao_pct)   # chama como atributo, não como método

# 5. lru_cache — cache de resultado de função
from functools import lru_cache

@lru_cache(maxsize=128)
def carregar_settings(modulo: str) -> object:
    """Carrega settings uma vez e cacheia."""
    return importlib.import_module(modulo)
```

### Criar um decorator de retry

```python
import asyncio
import functools
from typing import Callable, TypeVar

F = TypeVar("F", bound=Callable)

def com_retry(max_tentativas: int = 3, excecoes: tuple = (Exception,)):
    """
    Decorator que retentar uma função async em caso de falha.

    Uso:
        @com_retry(max_tentativas=3, excecoes=(ConnectionError, TimeoutError))
        async def chamar_api(): ...
    """
    def decorador(func: F) -> F:
        @functools.wraps(func)   # preserva nome e docstring
        async def wrapper(*args, **kwargs):
            for tentativa in range(max_tentativas):
                try:
                    return await func(*args, **kwargs)
                except excecoes as e:
                    if tentativa == max_tentativas - 1:
                        raise
                    espera = 2 ** tentativa
                    await asyncio.sleep(espera)
        return wrapper
    return decorador

# uso
@com_retry(max_tentativas=3, excecoes=(ConnectionError, TimeoutError))
async def chamar_qdrant(embedding: list[float]) -> list[dict]:
    return await vectorstore.search(embedding, top_k=50)
```

### Decorator de timing para observabilidade

```python
import time
import functools

def medir(nome_metrica: str):
    """Registra latência de cada chamada nas métricas."""
    def decorador(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            inicio = time.perf_counter()
            try:
                resultado = await func(*args, **kwargs)
                latencia_ms = (time.perf_counter() - inicio) * 1000
                metricas.registrar(nome_metrica, latencia_ms)
                return resultado
            except Exception as e:
                metricas.registrar_erro(nome_metrica)
                raise
        return wrapper
    return decorador

@medir("retrieval.vectorstore")
async def search(embedding: list[float]) -> list[dict]: ...

@medir("retrieval.reranker")
async def rerank(query: str, chunks: list[dict]) -> list[dict]: ...
```

---

## 12. Expressões regulares

### Por que aparecem no BuscaAI

As 7 operações de limpeza de texto do pré-processamento usam regex
extensivamente — normalizar espaços, detectar hifenação, remover artefatos.

```python
import re

# a função re.sub(padrão, substituto, texto) substitui todas as ocorrências
# a função re.findall(padrão, texto) retorna todas as correspondências
# a função re.search(padrão, texto) retorna a primeira ou None
# a função re.compile(padrão) pré-compila para reutilizar
```

### Padrões usados nas operações de limpeza

```python
import re

def limpar_texto(texto: str) -> str:

    # OP 4.1: múltiplos espaços → um espaço (exceto quebras de linha)
    texto = re.sub(r"[^\S\n]+", " ", texto)
    # [^\S\n] = "espaço que não é \n" = espaço, tab, etc.

    # OP 4.2: mais de 2 quebras consecutivas → 2
    texto = re.sub(r"\n{3,}", "\n\n", texto)
    # \n{3,} = "3 ou mais quebras de linha"

    # OP 3: reconstruir hifenação
    # (\w+)    = palavra antes do hífen
    # -\n      = hífen + quebra de linha
    # ([a-záA-ZÀ-ÿ]\w*) = palavra que começa com letra (continua a palavra)
    padrao_hifenacao = re.compile(
        r"(\w+)-\n([a-záàâãéêíóôõúüçA-ZÁÀÂÃÉÊÍÓÔÕÚÜÇ]\w*)"
    )
    texto = padrao_hifenacao.sub(r"\1\2", texto)
    # \1 = primeiro grupo, \2 = segundo grupo

    # OP 5: remover coordenadas PostScript (ex: "0 0 Td", "12.3 Tf")
    texto = re.sub(r"\b\d+\.?\d*\s+\d+\.?\d*\s+T[dfm]\b", "", texto)

    # OP 6: espaço antes de pontuação (artefato de extração)
    texto = re.sub(r"\s+([,\.;:!?])", r"\1", texto)

    # OP 6: espaçamento incorreto em números ("1 . 000" → "1.000")
    texto = re.sub(r"(\d)\s\.\s(\d)", r"\1.\2", texto)

    return texto.strip()


# contar tokens úteis para validação
def contar_tokens_uteis(texto: str) -> int:
    palavras = re.findall(r"\b[a-záàâãéêíóôõúüçA-ZÁÀÂÃÉÊÍÓÔÕÚÜÇ]{2,}\b", texto)
    return len(palavras)
    # \b = limite de palavra
    # [...]  = letras PT-BR com 2+ caracteres
```

### Principais símbolos de regex

```
.       qualquer caractere (exceto \n)
\d      dígito [0-9]
\w      palavra [a-zA-Z0-9_]
\s      espaço, \t, \n, \r
\n      quebra de linha
\b      limite de palavra

+       1 ou mais
*       0 ou mais
?       0 ou 1 (torna o anterior opcional)
{3}     exatamente 3
{2,5}   de 2 a 5
{3,}    3 ou mais

[abc]   a, b ou c
[^abc]  qualquer coisa exceto a, b, c
(abc)   grupo de captura
(?:abc) grupo sem captura

^       início da string
$       fim da string
```

---

## 13. Concorrência com asyncio

### O problema: embedding de 1.000 chunks

```python
# SEQUENCIAL — cada chunk espera o anterior
async def embed_sequencial(chunks: list[str]) -> list[list[float]]:
    vetores = []
    for chunk in chunks:
        vetor = await embedder.embed_single(chunk)   # ~50ms cada
        vetores.append(vetor)
    return vetores
# 1000 chunks × 50ms = 50.000ms = ~50 segundos
```

### asyncio.gather — executa em paralelo

```python
import asyncio

# PARALELO — todos os chunks ao mesmo tempo
async def embed_paralelo(chunks: list[str]) -> list[list[float]]:
    tarefas = [embedder.embed_single(chunk) for chunk in chunks]
    vetores = await asyncio.gather(*tarefas)
    return list(vetores)
# ~50ms (apenas o mais lento)
```

### Com limite de concorrência — Semaphore

```python
async def embed_com_limite(chunks: list[str], max_concorrente: int = 10):
    """
    Limite de 10 chamadas simultâneas — evita rate limit da API.
    """
    semaforo = asyncio.Semaphore(max_concorrente)

    async def embed_um(chunk: str) -> list[float]:
        async with semaforo:   # no máximo 10 dentro deste bloco ao mesmo tempo
            return await embedder.embed_single(chunk)

    tarefas = [embed_um(chunk) for chunk in chunks]
    return await asyncio.gather(*tarefas)
```

### Em lotes com asyncio — o padrão real do BuscaAI

```python
async def embed_em_lotes(
    chunks: list[str],
    tamanho_lote: int = 100,
) -> list[list[float]]:
    """
    Processa em lotes de 100 (limite da API OpenAI).
    Cada lote é uma chamada batch — mais eficiente que uma por chunk.
    """
    todos_vetores = []

    for i in range(0, len(chunks), tamanho_lote):
        lote = chunks[i : i + tamanho_lote]

        # uma chamada batch para o lote inteiro
        vetores_lote = await embedder.embed_texts(lote)
        todos_vetores.extend(vetores_lote)

        # pequena pausa para não esgotar rate limit
        if i + tamanho_lote < len(chunks):
            await asyncio.sleep(0.1)

    return todos_vetores
```

### asyncio.wait_for — timeout

```python
async def buscar_com_timeout(embedding: list[float]) -> list[dict]:
    try:
        return await asyncio.wait_for(
            vectorstore.search(embedding, top_k=50),
            timeout=5.0   # segundos
        )
    except asyncio.TimeoutError:
        raise TimeoutError("Qdrant não respondeu em 5 segundos")
```

---

## 14. SQLite com Python

### Por que SQLite no BuscaAI

SQLite é o **banco de controle interno** — guarda jobs de ingestão,
hashes de deduplicação, histórico de chat, logs e métricas.

Não é o banco vetorial (esse é o Qdrant/OpenSearch).
É um arquivo `.db` simples, sem servidor, sem configuração.

### Operações básicas com aiosqlite (async)

```python
import aiosqlite
from pathlib import Path

DB_PATH = "./buscaai.db"

# criar as tabelas (uma vez, na inicialização)
async def criar_tabelas():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                doc_id       TEXT PRIMARY KEY,
                filename     TEXT NOT NULL,
                source       TEXT,
                status       TEXT DEFAULT 'pending',
                n_chunks     INTEGER DEFAULT 0,
                custo_usd    REAL DEFAULT 0.0,
                indexed_at   TEXT
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                job_id       TEXT PRIMARY KEY,
                doc_id       TEXT REFERENCES documents(doc_id),
                status       TEXT DEFAULT 'queued',
                chunks_done  INTEGER DEFAULT 0,
                retry_count  INTEGER DEFAULT 0,
                erro         TEXT,
                created_at   TEXT DEFAULT (datetime('now')),
                updated_at   TEXT DEFAULT (datetime('now'))
            )
        """)
        await db.commit()


# INSERT
async def registrar_documento(doc_id: str, filename: str, source: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO documents (doc_id, filename, source) VALUES (?,?,?)",
            (doc_id, filename, source)
        )
        await db.commit()


# SELECT com Row factory (acessa por nome da coluna)
async def buscar_job(job_id: str) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM jobs WHERE job_id = ?", (job_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


# SELECT múltiplas linhas
async def listar_jobs(status: str = None) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        if status:
            async with db.execute(
                "SELECT * FROM jobs WHERE status = ? ORDER BY created_at DESC",
                (status,)
            ) as cursor:
                rows = await cursor.fetchall()
        else:
            async with db.execute(
                "SELECT * FROM jobs ORDER BY created_at DESC"
            ) as cursor:
                rows = await cursor.fetchall()
        return [dict(r) for r in rows]


# UPDATE
async def atualizar_status(job_id: str, status: str, erro: str = None):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """UPDATE jobs
               SET status = ?, erro = ?, updated_at = datetime('now')
               WHERE job_id = ?""",
            (status, erro, job_id)
        )
        await db.commit()


# verificar se hash já existe (deduplicação)
async def hash_existe(hash_sha256: str) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT 1 FROM documents WHERE doc_id = ?", (hash_sha256,)
        ) as cursor:
            return await cursor.fetchone() is not None
```

---

## 15. Testes com pytest

### Por que testar

No BuscaAI, um bug no chunking pode indexar texto duplicado em milhares
de chunks. Um bug no deduplicador pode fazer re-ingerir tudo toda vez.
Testes pegam esses bugs antes de ir para produção.

### Estrutura de testes

```
busca_ai/
├── ingestion/
│   └── chunking.py
└── tests/
    ├── __init__.py
    ├── unit/
    │   ├── test_chunking.py
    │   └── test_limpeza.py
    └── integration/
        └── test_pipeline.py
```

### Testes unitários — funções isoladas

```python
# tests/unit/test_limpeza.py
import pytest
from busca_ai.ingestion.limpeza import (
    op1_normalizar_encoding,
    op3_reconstruir_hifenacao,
    op4_normalizar_espacos,
)

def test_normalizar_encoding_remove_nbsp():
    texto = "cláusula\xa0nº\xa03"
    resultado = op1_normalizar_encoding(texto)
    assert resultado == "cláusula nº 3"
    assert "\xa0" not in resultado

def test_normalizar_encoding_substitui_aspas_curvas():
    texto = "\u201colá mundo\u201d"
    resultado = op1_normalizar_encoding(texto)
    assert resultado == '"olá mundo"'

def test_reconstruir_hifenacao_une_palavras():
    texto = "O prazo de rescis-\não contratual é de 30 dias."
    resultado = op3_reconstruir_hifenacao(texto)
    assert "rescisão" in resultado
    assert "rescis-" not in resultado

def test_reconstruir_hifenacao_preserva_hifen_legitimo():
    texto = "O guarda-chuva azul estava lá."
    resultado = op3_reconstruir_hifenacao(texto)
    assert "guarda-chuva" in resultado   # não deve ser alterado

def test_normalizar_espacos_multiple_spaces():
    texto = "O   contrato   foi   assinado"
    resultado = op4_normalizar_espacos(texto)
    assert resultado == "O contrato foi assinado"

def test_normalizar_espacos_linhas_em_branco():
    texto = "parágrafo 1\n\n\n\n\nparágrafo 2"
    resultado = op4_normalizar_espacos(texto)
    assert resultado.count("\n") == 2
```

### Testes com fixtures — compartilhar setup

```python
# tests/conftest.py (pytest carrega automaticamente)
import pytest
from pathlib import Path

@pytest.fixture
def pdf_simples(tmp_path: Path) -> Path:
    """Cria um PDF simples para testes."""
    import fitz
    doc  = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), "O prazo de rescisão é de 30 dias.")
    caminho = tmp_path / "teste.pdf"
    doc.save(str(caminho))
    doc.close()
    return caminho

@pytest.fixture
def chunks_exemplo() -> list[dict]:
    """Lista de chunks para testes de retrieval."""
    return [
        {"chunk_id": "c1", "texto": "O prazo de rescisão é de 30 dias.", "score": 0.97},
        {"chunk_id": "c2", "texto": "A multa por descumprimento é de 10%.", "score": 0.85},
        {"chunk_id": "c3", "texto": "O contrato entra em vigor na assinatura.", "score": 0.43},
    ]

# uso nos testes
def test_chunking_pdf(pdf_simples: Path):
    from busca_ai.ingestion.loaders.pdf import PDFLoader
    loader = PDFLoader(config={})
    docs   = loader.load(str(pdf_simples))
    assert len(docs) > 0
    assert "rescisão" in docs[0].text

def test_filtrar_por_score(chunks_exemplo: list[dict]):
    relevantes = [c for c in chunks_exemplo if c["score"] >= 0.7]
    assert len(relevantes) == 2
    assert all(c["score"] >= 0.7 for c in relevantes)
```

### Testes async com pytest-asyncio

```python
# pip install pytest-asyncio
import pytest
import pytest_asyncio

@pytest.mark.asyncio
async def test_embed_retorna_dimensao_correta():
    from busca_ai.ingestion.embeddings import OpenAIEmbedder
    embedder = OpenAIEmbedder(config={"model": "text-embedding-3-small"})
    vetores  = await embedder.embed_texts(["Olá mundo"])
    assert len(vetores) == 1
    assert len(vetores[0]) == 1536

@pytest.mark.asyncio
async def test_hash_deduplicacao(tmp_path):
    db_path = str(tmp_path / "test.db")
    from busca_ai.db import criar_tabelas, hash_existe, registrar_documento
    await criar_tabelas(db_path)

    hash_falso = "abc123"
    assert not await hash_existe(hash_falso, db_path)

    await registrar_documento(hash_falso, "teste.pdf", "upload", db_path)
    assert await hash_existe(hash_falso, db_path)
```

### Rodar os testes

```bash
# todos os testes
pytest

# com saída detalhada
pytest -v

# só testes unitários
pytest tests/unit/

# testes que contêm "chunking" no nome
pytest -k "chunking"

# com cobertura de código
pytest --cov=busca_ai --cov-report=html
```

---

## 16. Estrutura de pacote Python

### Por que a estrutura importa

Um pacote bem organizado permite importar de qualquer lugar do projeto
sem surpresas, e é necessário para publicar no PyPI (`pip install busca-ai`).

### Estrutura do BuscaAI

```
busca_ai/                      ← pacote raiz
│
├── __init__.py                ← torna a pasta um pacote; expõe API pública
│
├── api/
│   ├── __init__.py
│   ├── server.py              ← app = FastAPI()
│   └── routes/
│       ├── __init__.py
│       ├── search.py
│       └── ingest.py
│
├── ingestion/
│   ├── __init__.py
│   ├── loaders/
│   │   ├── __init__.py
│   │   ├── base.py            ← BaseLoader, Document
│   │   ├── pdf.py             ← PDFLoader
│   │   └── sql.py             ← SQLLoader
│   ├── chunking.py
│   └── limpeza.py
│
├── retrieval/
│   ├── __init__.py
│   ├── embeddings.py
│   ├── vectorstore/
│   │   ├── __init__.py
│   │   ├── base.py            ← BaseVectorStore
│   │   └── qdrant.py          ← QdrantVectorStore
│   └── reranker/
│       ├── __init__.py
│       └── cross_encoder.py
│
└── generation/
    ├── __init__.py
    └── llm.py                 ← LLMProvider (usa LiteLLM)
```

### O `__init__.py` — o que expor

```python
# busca_ai/__init__.py
"""
BuscaAI — Framework RAG híbrido e modular.
"""

from busca_ai.ingestion.loaders.base import BaseLoader, Document
from busca_ai.ingestion.loaders.pdf  import PDFLoader
from busca_ai.retrieval.vectorstore.qdrant import QdrantVectorStore
from busca_ai.generation.llm import LLMProvider

__version__ = "1.0.0"
__all__ = [
    "BaseLoader", "Document", "PDFLoader",
    "QdrantVectorStore", "LLMProvider",
]

# permite: from busca_ai import PDFLoader
# em vez de: from busca_ai.ingestion.loaders.pdf import PDFLoader
```

### Imports relativos vs absolutos

```python
# absoluto — funciona de qualquer lugar, mais claro
from busca_ai.ingestion.loaders.base import Document
from busca_ai.retrieval.embeddings import BaseEmbedder

# relativo — só funciona dentro do pacote
from .base import Document              # mesmo nível (loaders/)
from ..chunking import chunkar          # nível acima (ingestion/)
from ...retrieval.embeddings import ... # dois níveis acima
```

### pyproject.toml — o manifesto do pacote

```toml
[build-system]
requires      = ["setuptools>=68", "wheel"]
build-backend = "setuptools.backends.legacy:build"

[project]
name        = "busca-ai"
version     = "1.0.0"
description = "Framework RAG híbrido e modular"
readme      = "README.md"
requires-python = ">=3.11"

dependencies = [
    "fastapi>=0.111",
    "uvicorn>=0.29",
    "qdrant-client>=1.9",
    "litellm>=1.40",
    "aiosqlite>=0.20",
    "celery>=5.4",
    "redis>=5.0",
    "pymupdf>=1.24",
    "langdetect>=1.0",
    "python-dotenv>=1.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.23",
    "pytest-cov>=5.0",
]
docling = [
    "docling>=2.0",
]

[project.scripts]
rag = "busca_ai.cli:main"    # habilita o comando `rag` no terminal
```

---

## Resumo rápido — o que cada conceito resolve no BuscaAI

```
CONCEITO            ONDE APARECE NO BUSCAAI
────────────────────────────────────────────────────────────────────
Type hints          Estado do LangGraph (TypedDict), todas as funções
Dataclasses         Document, Chunk, LimpezaStats, EmbeddingConfig
ABC                 BaseLoader, BaseEmbedder, BaseVectorStore, BaseLLM
Comprehensions      Processar listas de chunks, extrair campos, filtrar
Context managers    Conexões SQLite, arquivos PDF (fitz.open), aiofiles
Exceções            Retry de API, degradação graciosa, status de jobs
Env vars            Credenciais de API, hosts, ports — nunca hardcoded
Pathlib             Listar PDFs, salvar outputs, validar extensões
Async/await         FastAPI, Qdrant, LiteLLM, aiosqlite — tudo é async
Generators          Streaming de tokens SSE, ingestão em lotes, chunking
Decorators          @app.post, @com_retry, @medir, @lru_cache
Regex               7 operações de limpeza de texto dos PDFs
asyncio.gather      Embedding de múltiplos chunks em paralelo
SQLite              Jobs de ingestão, hashes, histórico de chat, métricas
pytest              Testar limpeza, chunking, deduplicação, pipeline
Estrutura pacote    `pip install busca-ai`, imports entre módulos
```

---

## 17. Pydantic — validação de dados da API

### O que é e por que o FastAPI depende dele

O FastAPI usa Pydantic para validar automaticamente os dados que chegam
nos endpoints. Se o cliente mandar um campo do tipo errado ou esquecer
um campo obrigatório, o Pydantic retorna um erro 422 antes do seu código
ser executado — sem você escrever nenhuma validação manual.

```python
from pydantic import BaseModel, Field, field_validator
from typing import Optional

# modelo de request — o que o cliente manda
class SearchRequest(BaseModel):
    query:      str
    collection: str            = "default"
    top_k:      int            = Field(default=5, ge=1, le=20)
    strategy:   str            = "hybrid"
    reranker:   bool           = True
    session_id: Optional[str]  = None

    # validação customizada
    @field_validator("strategy")
    @classmethod
    def strategy_valida(cls, v: str) -> str:
        validas = {"hybrid", "dense", "lexical"}
        if v not in validas:
            raise ValueError(f"strategy deve ser uma de: {validas}")
        return v

    @field_validator("query")
    @classmethod
    def query_nao_vazia(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("query não pode ser vazia")
        if len(v) > 2000:
            return v[:2000]   # trunca silenciosamente
        return v


# modelo de response — o que a API retorna
class FonteResponse(BaseModel):
    chunk_id: str
    source:   str
    pagina:   Optional[int] = None
    score:    float
    trecho:   str

class SearchResponse(BaseModel):
    resposta:   str
    fontes:     list[FonteResponse]
    meta: dict  = Field(default_factory=dict)


# uso no endpoint — validação automática
@app.post("/search", response_model=SearchResponse)
async def buscar(request: SearchRequest) -> SearchResponse:
    # se chegou aqui, request já está válido e tipado
    embedding = await embedder.embed_query(request.query)
    chunks    = await vectorstore.search(embedding, top_k=request.top_k * 10)
    # ...
```

### Field — validações declarativas

```python
from pydantic import BaseModel, Field

class ChunkingConfig(BaseModel):
    strategy:   str   = Field(default="auto",
                              pattern="^(recursive|markdown|code|auto|semantic)$")
    chunk_size: int   = Field(default=512, ge=8, le=4096)
    overlap:    int   = Field(default=50, ge=0)
    language:   str   = Field(default="pt", min_length=2, max_length=10)

    # validação que depende de múltiplos campos
    def model_post_init(self, __context) -> None:
        if self.overlap >= self.chunk_size:
            raise ValueError("overlap deve ser menor que chunk_size")
```

### Diferença entre BaseModel e dataclass

```python
# dataclass — só guarda dados, sem validação
@dataclass
class Chunk:
    texto:    str
    n_tokens: int = 0
# Chunk(texto=123, n_tokens="abc")  → aceita sem reclamar

# Pydantic BaseModel — valida e converte tipos
class ChunkModel(BaseModel):
    texto:    str
    n_tokens: int = 0
# ChunkModel(texto=123, n_tokens="abc")
# → texto converte 123 para "123"
# → n_tokens converte "abc" → ValidationError

# Regra: use dataclass para dados internos (chunks, docs)
#         use BaseModel para dados da API (requests, responses)
```

---

## 18. Enum — constantes com significado

### O que é e por que usar

Enum evita strings mágicas espalhadas pelo código — quando você escreve
`status == "completed"` em 15 lugares e um dia muda para `"done"`, você
tem que encontrar todos os 15. Com Enum, há um único lugar de verdade.

```python
from enum import Enum, auto

class JobStatus(str, Enum):
    """Status de um job de ingestão.

    Herdar de str permite usar como string diretamente:
    JobStatus.COMPLETED == "completed"  → True
    """
    QUEUED     = "queued"
    PROCESSING = "processing"
    COMPLETED  = "completed"
    FAILED     = "failed"
    CANCELLED  = "cancelled"
    EMPTY      = "empty"


class SearchStrategy(str, Enum):
    HYBRID  = "hybrid"
    DENSE   = "dense"
    LEXICAL = "lexical"


class VectorBackend(str, Enum):
    QDRANT     = "qdrant"
    OPENSEARCH = "opensearch"
    PGVECTOR   = "pgvector"
    CHROMA     = "chroma"
```

### Usando Enum no BuscaAI

```python
# SQLite — status gravado como string, mas lido como Enum
async def atualizar_status(job_id: str, status: JobStatus):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE jobs SET status = ? WHERE job_id = ?",
            (status.value, job_id)    # .value pega a string "completed"
        )
        await db.commit()

# comparação sem string mágica
async def jobs_finalizados() -> list[dict]:
    status_finais = {JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED}
    todos = await listar_jobs()
    return [j for j in todos if j["status"] in {s.value for s in status_finais}]

# Pydantic entende Enum diretamente
class SearchRequest(BaseModel):
    strategy: SearchStrategy = SearchStrategy.HYBRID
    # aceita "hybrid", "dense", "lexical" e converte para o Enum
```

---

## 19. hashlib — SHA-256 para deduplicação

### O que é e como funciona

O hash SHA-256 transforma qualquer sequência de bytes em uma string
de 64 caracteres hexadecimais. A mesma entrada sempre gera a mesma saída.
Entradas diferentes (quase certamente) geram saídas diferentes.

```python
import hashlib

# a função básica
conteudo = b"O prazo de rescisão é de 30 dias."
hash_hex  = hashlib.sha256(conteudo).hexdigest()
print(hash_hex)
# → "a3f8c2d4e5b6..." (64 caracteres, sempre o mesmo para esse texto)
```

### Deduplicação no BuscaAI

```python
import hashlib
from pathlib import Path

def hash_arquivo(caminho: str | Path) -> str:
    """
    Gera SHA-256 do conteúdo binário do arquivo.
    Independe do nome do arquivo — detecta conteúdo duplicado
    mesmo com nomes diferentes.
    """
    conteudo = Path(caminho).read_bytes()
    return hashlib.sha256(conteudo).hexdigest()


def hash_texto(texto: str) -> str:
    """
    SHA-256 de um texto. Usado para cache de queries.
    """
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


# pipeline de deduplicação
async def ingerir_com_dedup(caminho: str) -> dict:
    hash_doc = hash_arquivo(caminho)

    # verificar se já existe no SQLite
    if await hash_existe(hash_doc):
        return {"status": "skip", "motivo": "conteúdo já indexado"}

    # prosseguir com ingestão
    doc = await processar(caminho, doc_id=hash_doc)
    await registrar_documento(doc_id=hash_doc, filename=Path(caminho).name)
    return {"status": "ok", "doc_id": hash_doc}


# cache de queries — mesmo hash para mesma query
def cache_key(query: str, collection: str, strategy: str) -> str:
    entrada = f"{query}|{collection}|{strategy}"
    return hashlib.sha256(entrada.encode()).hexdigest()
```

---

## 20. Logging — registro estruturado para produção

### Por que não usar print()

```python
# print — sem contexto, não filtrável, não vai para arquivo
print(f"job iniciado: {job_id}")

# logging — com nível, timestamp, módulo, linha — vai para onde você configurar
import logging
logger = logging.getLogger(__name__)
logger.info("job iniciado", extra={"job_id": job_id})
```

### Configuração do logging no BuscaAI

```python
# busca_ai/observability/logging.py
import logging
import json
import sys
from datetime import datetime, timezone

class JSONFormatter(logging.Formatter):
    """Formata logs como JSON — mais fácil de processar no Grafana/Loki."""

    def format(self, record: logging.LogRecord) -> str:
        log = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level":     record.levelname,
            "logger":    record.name,
            "message":   record.getMessage(),
        }
        # campos extras passados via extra={}
        for k, v in record.__dict__.items():
            if k not in {"msg", "args", "levelname", "name", "pathname",
                         "lineno", "funcName", "created", "msecs",
                         "relativeCreated", "thread", "processName",
                         "process", "exc_info", "exc_text", "stack_info",
                         "levelno", "filename", "module", "taskName"}:
                log[k] = v

        if record.exc_info:
            log["exception"] = self.formatException(record.exc_info)

        return json.dumps(log, ensure_ascii=False)


def configurar_logging(level: str = "INFO", formato: str = "json"):
    handler = logging.StreamHandler(sys.stdout)

    if formato == "json":
        handler.setFormatter(JSONFormatter())
    else:
        handler.setFormatter(logging.Formatter(
            "%(asctime)s %(levelname)s %(name)s — %(message)s"
        ))

    logging.basicConfig(
        level   = getattr(logging, level.upper()),
        handlers= [handler],
        force   = True,
    )
```

### Usando o logger no BuscaAI

```python
# em cada módulo — cria um logger com o nome do módulo
import logging
logger = logging.getLogger(__name__)
# __name__ é "busca_ai.ingestion.loaders.pdf" — facilita filtrar

# níveis de log
logger.debug("detalhe técnico — só em desenvolvimento")
logger.info("job iniciado", extra={"job_id": job_id})
logger.warning("Redis indisponível — continuando sem cache")
logger.error("falha ao embedar chunk", extra={"chunk_id": cid, "erro": str(e)})
logger.critical("banco vetorial inacessível — sistema fora do ar")

# com exc_info — inclui o traceback completo
try:
    resultado = await processar(caminho)
except Exception as e:
    logger.error("falha no processamento",
                 extra={"caminho": caminho},
                 exc_info=True)   # inclui traceback
    raise


# log de queries para observabilidade
async def logar_query(query: str, latencia_ms: float, custo_usd: float, cache_hit: bool):
    logger.info("query processada", extra={
        "evento":      "search.completed",
        "latencia_ms": round(latencia_ms, 1),
        "custo_usd":   round(custo_usd, 6),
        "cache_hit":   cache_hit,
        "query_hash":  hash_texto(query)[:8],  # não loga a query completa
    })
```

---

## 21. Dicionários — operações avançadas

### O que você usa todo dia no BuscaAI

```python
# .get() com padrão — nunca KeyError
chunk = {"texto": "...", "score": 0.97}
pagina = chunk.get("pagina", 0)      # 0 se não existir
titulo = chunk.get("titulo") or ""   # None vira ""

# .setdefault() — insere se não existir
metadados = {}
metadados.setdefault("entidades", []).append("ACME S.A.")

# merge de dicts (Python 3.9+)
base    = {"fonte": "contrato.pdf", "idioma": "pt"}
extra   = {"pagina": 3, "score": 0.97}
merged  = base | extra         # novo dict
base   |= extra                # atualiza base no lugar

# spread operator — copiar e sobrescrever campos
estado_novo = {**estado_atual, "chunks": novos_chunks, "cache_hit": False}

# dict comprehension com transformação
scores_normalizados = {
    chunk_id: round(score * 100, 1)
    for chunk_id, score in scores_brutos.items()
    if score > 0.5
}

# agrupar chunks por source
from collections import defaultdict
por_fonte: dict[str, list] = defaultdict(list)
for chunk in chunks:
    por_fonte[chunk["source"]].append(chunk)
# defaultdict cria automaticamente uma lista vazia se a chave não existe

# Counter — contar ocorrências
from collections import Counter
origens = Counter(chunk["source"] for chunk in chunks)
print(origens.most_common(3))
# → [("contrato.pdf", 12), ("laudo.pdf", 8), ("manual.pdf", 5)]
```

### Desempacotar dicionários

```python
# ** para passar campos de um dict como kwargs
config = {"model": "gpt-4o-mini", "temperature": 0.0, "max_tokens": 500}
resposta = await litellm.acompletion(
    messages=msgs,
    **config           # equivale a: model="gpt-4o-mini", temperature=0.0, ...
)

# desempacotar em variáveis
chunk = {"texto": "...", "score": 0.97, "fonte": "contrato.pdf"}
texto, score = chunk["texto"], chunk["score"]

# mais limpo — walrus operator (Python 3.8+) numa condição
chunks_alta_qualidade = [
    c for c in chunks
    if (score := c.get("score", 0)) >= 0.7
]
```

---

## 22. Built-ins essenciais

### enumerate — índice + valor

```python
# sem enumerate
for i in range(len(chunks)):
    chunk = chunks[i]
    print(f"[{i+1}] {chunk['texto'][:50]}")

# com enumerate — mais pythônico
for i, chunk in enumerate(chunks, start=1):
    print(f"[{i}] {chunk['texto'][:50]}")

# criar chunk_id com posição
for i, chunk in enumerate(chunks):
    chunk["chunk_id"] = f"{doc_id}_chunk_{i:04d}"   # "doc_abc_chunk_0007"
```

### zip — combinar listas

```python
chunks  = [c.texto for c in meus_chunks]
vetores = await embedder.embed_texts(chunks)

# zip combina as duas listas em pares
for chunk, vetor in zip(meus_chunks, vetores):
    await vectorstore.upsert_um(chunk, vetor)

# zip para criar dicts
campos = ["chunk_id", "score", "fonte"]
valores = ["c001", 0.97, "contrato.pdf"]
resultado = dict(zip(campos, valores))
# → {"chunk_id": "c001", "score": 0.97, "fonte": "contrato.pdf"}
```

### sorted — ordenar com chave customizada

```python
# ordenar chunks por score (maior primeiro)
chunks_ordenados = sorted(chunks, key=lambda c: c["score"], reverse=True)

# ordenar por múltiplos critérios
chunks_ordenados = sorted(
    chunks,
    key=lambda c: (-c["score"], c.get("pagina", 0))
    # primeiro por score desc, depois por página asc
)

# top-K sem ordenar tudo (mais eficiente)
import heapq
top5 = heapq.nlargest(5, chunks, key=lambda c: c["score"])
```

### any e all — verificar condições em coleções

```python
# any — pelo menos um satisfaz
tem_alta_confianca = any(c["score"] > 0.9 for c in chunks)

# all — todos satisfazem
todos_validos = all(len(c["texto"]) > 20 for c in chunks)

# combinar
if not any(c["score"] > 0.5 for c in chunks):
    return {"resposta": "Não encontrei informações suficientes."}
```

### map e filter — transformação funcional

```python
# map — aplica função a cada elemento
textos = list(map(lambda c: c["texto"], chunks))
# equivale a: textos = [c["texto"] for c in chunks]

# filter — mantém elementos que satisfazem condição
relevantes = list(filter(lambda c: c["score"] > 0.7, chunks))
# equivale a: relevantes = [c for c in chunks if c["score"] > 0.7]

# na prática: comprehensions são mais legíveis que map/filter
# use map/filter quando trabalhar com funções já prontas:
import re
linhas_com_conteudo = list(filter(None, map(str.strip, texto.splitlines())))
```

---

## 23. Strings — métodos que aparecem na limpeza

```python
texto = "  O prazo de rescisão é de 30 dias.  \n  "

# remover espaços nas bordas
texto.strip()        # remove dos dois lados
texto.lstrip()       # só da esquerda
texto.rstrip()       # só da direita

# dividir
texto.split()        # divide por qualquer whitespace
texto.split(".")     # divide pelo ponto
texto.splitlines()   # divide por \n, \r\n, \r

# juntar
"\n\n".join(paragrafos)          # une parágrafos com linha em branco
" ".join(palavras)               # une palavras com espaço

# verificar
texto.startswith("O prazo")      # True
texto.endswith("dias.")          # True
"rescisão" in texto              # True
texto.isdigit()                  # False

# transformar
texto.lower()                    # minúsculas
texto.upper()                    # maiúsculas
texto.replace("rescisão", "RESCISÃO")

# f-strings avançados
n = 1536
print(f"{n:,}")          # "1,536" — separador de milhar
print(f"{0.9742:.1%}")   # "97.4%" — porcentagem com 1 decimal
print(f"{42:04d}")       # "0042" — zero-padded
print(f"{'texto':>20}")  # "               texto" — alinha direita

# strings multilinha para prompts
system_prompt = (
    "Você é um assistente especializado.\n"
    "Responda apenas com base nos documentos fornecidos.\n"
    "Se não encontrar a informação, diga que não sabe."
)

# ou com triple quotes
system_prompt = """
Você é um assistente especializado.
Responda apenas com base nos documentos fornecidos.
Se não encontrar a informação, diga que não sabe.
""".strip()
```

---

## 24. datetime — timestamps e durações

```python
from datetime import datetime, timezone, timedelta

# agora em UTC (sempre use UTC internamente)
agora = datetime.now(timezone.utc)

# formato ISO 8601 — padrão da API do BuscaAI
agora_iso = agora.isoformat()
# → "2026-05-30T14:32:00.123456+00:00"

# só a data
data = agora.date().isoformat()   # "2026-05-30"

# parse de string para datetime
criado = datetime.fromisoformat("2026-05-30T14:32:00+00:00")

# comparar
expirado = criado + timedelta(hours=1)
if datetime.now(timezone.utc) > expirado:
    print("sessão expirada")

# duração de uma operação
inicio = datetime.now(timezone.utc)
await processar_documento(caminho)
duracao = (datetime.now(timezone.utc) - inicio).total_seconds()
print(f"Processado em {duracao:.2f}s")

# para SQLite — armazena como string ISO
created_at = datetime.now(timezone.utc).isoformat()
await db.execute(
    "INSERT INTO jobs (job_id, created_at) VALUES (?, ?)",
    (job_id, created_at)
)
```

---

## 25. Protocol — duck typing estrutural

### ABC vs Protocol

```python
# ABC — herança explícita obrigatória
class BaseLoader(ABC):
    @abstractmethod
    def load(self): ...

class MeuLoader(BaseLoader):   # tem que herdar
    def load(self): ...


# Protocol — baseado em estrutura (Python 3.8+)
from typing import Protocol, runtime_checkable

@runtime_checkable
class Loader(Protocol):
    def load(self, source: str) -> list: ...

class MeuLoader:              # NÃO precisa herdar
    def load(self, source: str) -> list:
        return []

def processar(loader: Loader):   # aceita qualquer objeto com .load()
    return loader.load("fonte")

processar(MeuLoader())   # funciona
isinstance(MeuLoader(), Loader)   # True (runtime_checkable)
```

### Quando usar cada um

```python
# Use ABC quando:
# - você quer garantir que subclasses implementem os métodos
# - você tem implementação parcial para herdar
# - é código interno do BuscaAI

# Use Protocol quando:
# - você quer aceitar objetos de terceiros (LiteLLM, Docling)
#   sem exigir que herdem da sua classe
# - você quer testar com mocks simples

# Exemplo prático: aceitar qualquer embedder que tenha embed_texts
class Embedder(Protocol):
    async def embed_texts(self, textos: list[str]) -> list[list[float]]: ...

# tanto seu EmbedderOpenAI quanto o LiteLLM e o SentenceTransformer
# funcionam — nenhum precisa herdar de nada
```

---

## Padrões de código recorrentes no BuscaAI

Padrões que aparecem em múltiplos lugares — vale reconhecer e reutilizar.

### Padrão 1 — Carregar componente pelo nome (settings)

```python
import importlib

def carregar_vectorstore(config: dict) -> BaseVectorStore:
    """
    Carrega o banco vetorial configurado no settings.
    Permite trocar de banco sem alterar o core.
    """
    backends = {
        "qdrant":      "busca_ai.retrieval.vectorstore.qdrant.QdrantVectorStore",
        "opensearch":  "busca_ai.retrieval.vectorstore.opensearch.OpenSearchVectorStore",
        "pgvector":    "busca_ai.retrieval.vectorstore.pgvector.PgVectorStore",
        "chroma":      "busca_ai.retrieval.vectorstore.chroma.ChromaVectorStore",
    }
    backend = config.get("backend", "qdrant")
    if backend not in backends:
        raise ValueError(f"Backend '{backend}' não suportado. Opções: {list(backends)}")

    caminho_classe = backends[backend]
    modulo_nome, classe_nome = caminho_classe.rsplit(".", 1)
    modulo  = importlib.import_module(modulo_nome)
    Classe  = getattr(modulo, classe_nome)
    return Classe(config)
```

### Padrão 2 — Resultado com sucesso/falha

```python
from dataclasses import dataclass
from typing import TypeVar, Generic, Optional

T = TypeVar("T")

@dataclass
class Resultado(Generic[T]):
    """Encapsula sucesso ou falha sem lançar exceções."""
    ok:    bool
    valor: Optional[T]   = None
    erro:  Optional[str] = None

    @classmethod
    def sucesso(cls, valor: T) -> "Resultado[T]":
        return cls(ok=True, valor=valor)

    @classmethod
    def falha(cls, erro: str) -> "Resultado[T]":
        return cls(ok=False, erro=erro)


async def processar_seguro(caminho: str) -> Resultado[Document]:
    try:
        doc = await processar(caminho)
        return Resultado.sucesso(doc)
    except Exception as e:
        return Resultado.falha(str(e))

# uso — sem try/except no chamador
resultado = await processar_seguro("contrato.pdf")
if resultado.ok:
    chunks = chunkar(resultado.valor)
else:
    logger.warning(f"Falha: {resultado.erro}")
```

### Padrão 3 — Singleton para conexão de banco

```python
# evita abrir uma nova conexão a cada request
_qdrant_client = None

async def get_qdrant() -> AsyncQdrantClient:
    global _qdrant_client
    if _qdrant_client is None:
        settings = carregar_settings()
        _qdrant_client = AsyncQdrantClient(
            host=settings.VECTOR_STORE["host"],
            port=settings.VECTOR_STORE["port"],
        )
    return _qdrant_client

# no FastAPI — lifespan para inicializar e fechar
from contextlib import asynccontextmanager
from fastapi import FastAPI

@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup
    await get_qdrant()
    await criar_tabelas()
    yield
    # shutdown
    client = await get_qdrant()
    await client.close()

app = FastAPI(lifespan=lifespan)
```

### Padrão 4 — Pipeline com nós LangGraph

```python
from langgraph.graph import StateGraph, END
from typing import TypedDict

class RAGState(TypedDict):
    query:       str
    embedding:   list[float]
    chunks:      list[dict]
    resposta:    str
    cache_hit:   bool
    custo_total: float

def criar_pipeline() -> StateGraph:
    grafo = StateGraph(RAGState)

    # registra os nós
    grafo.add_node("verificar_cache", no_verificar_cache)
    grafo.add_node("embedar_query",   no_embedar_query)
    grafo.add_node("retrieval",       no_retrieval)
    grafo.add_node("reranker",        no_reranker)
    grafo.add_node("geracao",         no_geracao)
    grafo.add_node("salvar_cache",    no_salvar_cache)

    # aresta condicional — bifurcação
    grafo.add_conditional_edges(
        "verificar_cache",
        lambda state: "fim" if state["cache_hit"] else "continua",
        {"fim": END, "continua": "embedar_query"},
    )

    # fluxo linear para o resto
    grafo.add_edge("embedar_query", "retrieval")
    grafo.add_edge("retrieval",     "reranker")
    grafo.add_edge("reranker",      "geracao")
    grafo.add_edge("geracao",       "salvar_cache")
    grafo.add_edge("salvar_cache",  END)

    grafo.set_entry_point("verificar_cache")
    return grafo.compile()

# cada nó é uma função pura — recebe estado, retorna estado
async def no_retrieval(state: RAGState) -> RAGState:
    chunks = await vectorstore.search(state["embedding"], top_k=50)
    return {**state, "chunks": chunks}
```

---

## Checklist de boas práticas

```
ANTES DE ESCREVER CÓDIGO
  [ ] Tenho type hints em todos os parâmetros e retornos?
  [ ] O nome da função descreve o que ela faz (verbo + substantivo)?
  [ ] A função faz uma coisa só? (se tem "e" no nome, talvez sejam duas)
  [ ] Credenciais vêm de variáveis de ambiente?

DURANTE O CÓDIGO
  [ ] Usei dataclass em vez de dict para dados estruturados?
  [ ] Usei ABC/Protocol para interfaces plugáveis?
  [ ] Conexões de banco estão em context managers (with)?
  [ ] Tenho tratamento de exceções nos pontos críticos?
  [ ] Funções async chamam outras async com await?
  [ ] Listas grandes usam generators em vez de criar tudo na memória?

ANTES DE COMMITAR
  [ ] pytest roda sem erros?
  [ ] Sem print() esquecido (use logger)?
  [ ] Sem credenciais no código?
  [ ] Sem import não utilizado?
  [ ] Docstring nas classes e funções públicas?
```

---

## 26. Docling — extração e estruturação de documentos

### O que é e por que substitui o PyMuPDF no BuscaAI

O Docling é uma biblioteca da IBM Research que faz duas coisas que o
PyMuPDF não faz: entende o **layout** do documento (colunas, tabelas,
hierarquia de títulos, ordem de leitura) e exporta em **formatos prontos
para RAG** (Markdown com estrutura preservada).

```
PyMuPDF:  extrai texto bruto — você limpa e estrutura depois
Docling:  extrai texto JÁ estruturado — menos código de limpeza
```

O Docling não substitui toda a etapa de pré-processamento. Ele resolve
a parte mais difícil: a extração com estrutura. Limpeza de encoding,
hifenação e normalização ainda podem ser necessárias dependendo do PDF.

---

### 26.1 A classe central — `DocumentConverter`

```python
from docling.document_converter import DocumentConverter

# instancia uma vez, reutiliza para múltiplos documentos
converter = DocumentConverter()

# converte — retorna um ConversionResult
resultado = converter.convert("contrato.pdf")

# o que está no resultado
print(type(resultado))           # ConversionResult
print(type(resultado.document))  # DoclingDocument
print(len(resultado.pages))      # número de páginas processadas
```

**Por que instanciar uma vez e reutilizar:**
O `DocumentConverter` carrega modelos de ML internamente (layout analysis,
table structure recognition). Isso leva alguns segundos. Instanciar dentro
de um loop processa cada PDF com custo de startup — instanciar fora do
loop carrega uma vez e reutiliza.

```python
# ERRADO — carrega os modelos a cada PDF
for caminho in lista_de_pdfs:
    converter = DocumentConverter()   # lento!
    resultado = converter.convert(caminho)

# CORRETO — carrega uma vez
converter = DocumentConverter()
for caminho in lista_de_pdfs:
    resultado = converter.convert(caminho)   # rápido
```

---

### 26.2 O objeto `DoclingDocument`

O `DoclingDocument` é uma representação hierárquica do documento —
não é texto plano, é uma estrutura de dados com componentes tipados.

```python
resultado = converter.convert("relatorio.pdf")
doc = resultado.document

# componentes disponíveis
print(dir(doc))

# textos (parágrafos, títulos, listas)
for item in doc.texts:
    print(f"[{item.label}] {item.text[:60]}")

# tabelas
for tabela in doc.tables:
    print(f"Tabela: {tabela.num_rows} linhas × {tabela.num_cols} colunas")

# imagens
for figura in doc.pictures:
    print(f"Figura na página {figura.prov[0].page_no if figura.prov else '?'}")

# exporta tudo como markdown
markdown = doc.export_to_markdown()

# exporta como dict (acesso programático)
dados = doc.export_to_dict()
```

---

### 26.3 Labels — tipos de conteúdo detectados

O Docling classifica cada bloco de texto com um `label`:

```python
from docling.datamodel.base_models import DocItemLabel

# labels disponíveis
DocItemLabel.TITLE          # título do documento
DocItemLabel.SECTION_HEADER # cabeçalho de seção (H1, H2, H3)
DocItemLabel.TEXT           # parágrafo normal
DocItemLabel.TABLE          # tabela
DocItemLabel.FIGURE         # imagem/gráfico
DocItemLabel.LIST_ITEM      # item de lista
DocItemLabel.FORMULA        # equação matemática
DocItemLabel.CODE           # bloco de código
DocItemLabel.CAPTION        # legenda de figura/tabela
DocItemLabel.FOOTNOTE       # nota de rodapé
DocItemLabel.PAGE_HEADER    # cabeçalho de página (removido na exportação)
DocItemLabel.PAGE_FOOTER    # rodapé de página (removido na exportação)

# filtrar só os títulos de seção
titulos = [
    item.text
    for item in doc.texts
    if item.label in {DocItemLabel.TITLE, DocItemLabel.SECTION_HEADER}
]
print("\n".join(titulos))
```

---

### 26.4 Exportar em diferentes formatos

```python
# Markdown — melhor para chunking por seção
markdown = doc.export_to_markdown()
# preserva: # Título, ## Seção, tabelas em formato MD, listas com -

# texto plano — sem marcação
texto = doc.export_to_text()
# remove toda marcação, só o conteúdo

# dict — acesso programático à estrutura
dados = doc.export_to_dict()
# útil para extrair metadados específicos

# DocTags — formato interno IBM (para fine-tuning)
doctags = doc.export_to_doctags()

# salvar
from pathlib import Path
Path("saida.md").write_text(markdown, encoding="utf-8")
Path("saida.txt").write_text(texto,   encoding="utf-8")
```

**Por que o Markdown é preferido para o BuscaAI:**
O chunker do BuscaAI com `strategy: "markdown"` divide o texto nos
cabeçalhos `#` e `##` — mantendo cada seção como um chunk coeso.
Se você exportar como texto plano, perde essa estrutura e o chunking
fica por tamanho de token sem respeitar seções.

---

### 26.5 Tabelas — onde o Docling realmente se destaca

```python
resultado = converter.convert("relatorio_financeiro.pdf")
doc = resultado.document

tabelas = list(doc.tables)
print(f"Tabelas detectadas: {len(tabelas)}")

for i, tabela in enumerate(tabelas):
    print(f"\n── Tabela {i+1} ({tabela.num_rows}×{tabela.num_cols}) ──")

    # exporta como markdown com estrutura de células
    md = tabela.export_to_markdown()
    print(md)

    # acesso às células individuais
    for row in tabela.data.grid:
        for cell in row:
            if cell.text:
                print(f"  [{cell.row_span}×{cell.col_span}] {cell.text}")
```

**O que PyMuPDF retornaria para uma tabela:**
```
Receita 2024 2025 Variação Produtos 1.200.000 1.450.000 +20,8%
Serviços 800.000 920.000 +15,0% Total 2.000.000 2.370.000 +18,5%
```

**O que Docling retorna:**
```markdown
| Receita   | 2024      | 2025      | Variação |
|-----------|-----------|-----------|----------|
| Produtos  | 1.200.000 | 1.450.000 | +20,8%   |
| Serviços  | 800.000   | 920.000   | +15,0%   |
| Total     | 2.000.000 | 2.370.000 | +18,5%   |
```

---

### 26.6 Metadados do documento

```python
resultado = converter.convert("artigo.pdf")
doc = resultado.document

# metadados do cabeçalho (XMP/PDF Info)
if doc.description:
    d = doc.description
    print(f"Título:   {d.title}")
    print(f"Autores:  {d.authors}")
    print(f"Data:     {d.date_created}")
    print(f"Idioma:   {d.language}")
    print(f"Keywords: {d.keywords}")

# informações das páginas
for i, pagina in enumerate(resultado.pages):
    print(f"Página {i+1}: {pagina.size.width:.0f}×{pagina.size.height:.0f} pts")
```

---

### 26.7 HybridChunker — chunking semântico

O `HybridChunker` é o chunker nativo do Docling. Ele conhece a estrutura
do `DoclingDocument` e divide respeitando fronteiras naturais do documento
(não corta no meio de uma tabela, não separa legenda da figura).

```python
from docling.document_converter import DocumentConverter
from docling.chunking import HybridChunker

converter = DocumentConverter()
resultado = converter.convert("contrato.pdf")
doc       = resultado.document

# instancia o chunker
chunker = HybridChunker(
    tokenizer    = "BAAI/bge-m3",   # modelo para contar tokens
    max_tokens   = 512,
    merge_peers  = True,             # une chunks pequenos consecutivos
)

# chunka o documento
chunks = list(chunker.chunk(doc))

print(f"Total de chunks: {len(chunks)}")

for i, chunk in enumerate(chunks[:5]):
    # serializa o chunk para string (inclui contexto de cabeçalho)
    texto = chunker.serialize(chunk=chunk)
    print(f"\n[{i}] {len(texto.split())} palavras")
    print(texto[:200] + "...")
```

**O que `merge_peers=True` faz:**
Se um parágrafo tem 50 tokens e o seguinte tem 40, sem merge seriam
dois chunks pequenos. Com merge, são unidos em um chunk de 90 tokens —
mais contexto por chunk, menos fragmentação.

**Por que passar o modelo de embedding:**
O `HybridChunker` usa o tokenizador do modelo para contar tokens
com precisão. `max_tokens=512` com o tokenizador do BGE-M3 garante
que nenhum chunk ultrapasse o limite do modelo de embedding.

---

### 26.8 Configuração do pipeline — controlar o que roda

```python
from docling.document_converter import DocumentConverter
from docling.pipeline.standard_pdf_pipeline import StandardPdfPipeline
from docling.datamodel.pipeline_options import PipelineOptions

# opções do pipeline
opcoes = PipelineOptions()
opcoes.do_ocr           = False   # desliga OCR (padrão: True)
opcoes.do_table_structure= True   # detecta estrutura de tabelas
opcoes.do_code_enrichment= False  # não detecta código (mais rápido)

# cria converter com opções
converter = DocumentConverter(
    pipeline_cls     = StandardPdfPipeline,
    pipeline_options = opcoes,
)

resultado = converter.convert("contrato.pdf")
```

**Quando desligar OCR:**
OCR é lento. Se sua base só tem PDFs digitais (não escaneados), desligar
OCR reduz o tempo de processamento significativamente. Se tiver PDFs
mistos, mantenha OCR ligado — ele só ativa nas páginas sem texto nativo.

---

### 26.9 Tratar erros de conversão

```python
from docling.document_converter import DocumentConverter, ConversionStatus

converter = DocumentConverter()

resultado = converter.convert("documento.pdf")

# verificar status da conversão
if resultado.status == ConversionStatus.SUCCESS:
    doc = resultado.document
    markdown = doc.export_to_markdown()

elif resultado.status == ConversionStatus.PARTIAL_SUCCESS:
    # algumas páginas falharam — conteúdo parcial disponível
    doc = resultado.document
    markdown = doc.export_to_markdown()
    print(f"Aviso: conversão parcial — {len(resultado.errors)} erros")
    for erro in resultado.errors:
        print(f"  Página {erro.page_no}: {erro.error_message}")

elif resultado.status == ConversionStatus.FAILURE:
    raise ValueError(f"Falha na conversão: {resultado.errors}")


# versão robusta para batch
def converter_seguro(caminho: str, converter: DocumentConverter) -> dict:
    try:
        resultado = converter.convert(caminho)
        if resultado.status == ConversionStatus.FAILURE:
            return {"status": "erro", "arquivo": caminho,
                    "motivo": str(resultado.errors)}
        return {
            "status":    "ok",
            "arquivo":   caminho,
            "documento": resultado.document,
            "parcial":   resultado.status == ConversionStatus.PARTIAL_SUCCESS,
        }
    except Exception as e:
        return {"status": "erro", "arquivo": caminho, "motivo": str(e)}
```

---

### 26.10 Como vai ficar no BuscaAI — DoclingPDFLoader completo

```python
# busca_ai/ingestion/loaders/pdf_docling.py

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from docling.document_converter import DocumentConverter, ConversionStatus
from docling.chunking import HybridChunker
from docling.pipeline.standard_pdf_pipeline import StandardPdfPipeline
from docling.datamodel.pipeline_options import PipelineOptions

from busca_ai.ingestion.loaders.base import BaseLoader, Document, Chunk

logger = logging.getLogger(__name__)


class DoclingPDFLoader(BaseLoader):
    """
    Loader de PDF usando Docling como parser.
    Ativado via CHUNKING['parser'] = 'docling' no rag_settings.py.
    """

    def __init__(self, config: dict):
        opcoes = PipelineOptions()
        opcoes.do_ocr             = config.get("ocr", True)
        opcoes.do_table_structure = config.get("table_structure", True)

        self._converter = DocumentConverter(
            pipeline_cls     = StandardPdfPipeline,
            pipeline_options = opcoes,
        )
        self._chunker = HybridChunker(
            tokenizer  = config.get("embedding_model", "BAAI/bge-m3"),
            max_tokens = config.get("chunk_size", 512),
            merge_peers= config.get("merge_peers", True),
        )
        self._config = config

    def validate_conn(self) -> bool:
        return True   # sem conexão externa

    def load(self, source: str) -> list[Document]:
        caminho = Path(source)
        if not caminho.exists():
            raise FileNotFoundError(f"Arquivo não encontrado: {source}")

        logger.info("iniciando conversão Docling", extra={"arquivo": caminho.name})

        resultado = self._converter.convert(str(caminho))

        if resultado.status == ConversionStatus.FAILURE:
            raise ValueError(f"Docling falhou ao converter {caminho.name}: {resultado.errors}")

        doc = resultado.document

        # metadados
        meta = {
            "filename":  caminho.name,
            "n_paginas": len(resultado.pages),
            "n_tabelas": len(list(doc.tables)),
            "n_figuras": len(list(doc.pictures)),
            "parcial":   resultado.status == ConversionStatus.PARTIAL_SUCCESS,
        }
        if doc.description:
            d = doc.description
            meta["titulo"]  = d.title or ""
            meta["idioma"]  = str(d.language) if d.language else "?"

        # exporta como markdown para o chunking
        markdown = doc.export_to_markdown()
        chars_markdown = len(markdown)

        # cria o Document
        import hashlib
        doc_id = hashlib.sha256(caminho.read_bytes()).hexdigest()

        documento = Document(
            doc_id        = doc_id,
            source_id     = str(caminho),
            filename      = caminho.name,
            text          = markdown,
            mime_type     = "application/pdf",
            n_paginas     = meta["n_paginas"],
            tamanho_bytes = caminho.stat().st_size,
            titulo        = meta.get("titulo", ""),
            idioma        = meta.get("idioma", "?"),
            chars_bruto   = chars_markdown,
            chars_limpo   = chars_markdown,
        )

        logger.info("Docling concluído", extra={
            "arquivo":   caminho.name,
            "paginas":   meta["n_paginas"],
            "tabelas":   meta["n_tabelas"],
            "chars":     chars_markdown,
        })

        return [documento]

    def load_chunks(self, source: str) -> list[Chunk]:
        """
        Alternativa a load() que retorna chunks diretamente
        usando o HybridChunker do Docling.
        """
        caminho  = Path(source)
        resultado = self._converter.convert(str(caminho))
        doc       = resultado.document

        import hashlib
        doc_id = hashlib.sha256(caminho.read_bytes()).hexdigest()

        chunks_docling = list(self._chunker.chunk(doc))
        chunks_saida   = []

        for i, chunk in enumerate(chunks_docling):
            texto = self._chunker.serialize(chunk=chunk)
            if len(texto.split()) < 10:
                continue   # descarta chunks muito pequenos

            chunks_saida.append(Chunk(
                texto      = texto,
                doc_id     = doc_id,
                chunk_id   = f"{doc_id}_{i:04d}",
                posicao    = i,
                n_tokens   = len(texto.split()),
                estrategia = "docling_hybrid",
                metadados  = {
                    "filename": caminho.name,
                    "chunk_pos": i,
                },
            ))

        return chunks_saida
```

---

### 26.11 Escolher entre PyMuPDF e Docling

```python
# busca_ai/ingestion/loaders/factory.py

def criar_pdf_loader(config: dict):
    """
    Retorna o loader correto baseado na configuração.

    CHUNKING = {
        "parser": "pymupdf"  ← padrão, mais rápido
        "parser": "docling"  ← mais preciso, mais lento
    }
    """
    parser = config.get("parser", "pymupdf")

    if parser == "docling":
        from busca_ai.ingestion.loaders.pdf_docling import DoclingPDFLoader
        return DoclingPDFLoader(config)
    else:
        from busca_ai.ingestion.loaders.pdf import PDFLoader
        return PDFLoader(config)
```

**Regra prática para escolher:**

```
pymupdf (padrão):
  ✓ PDFs digitais simples (texto corrido sem tabelas)
  ✓ Volume alto — precisa de velocidade
  ✓ Hardware sem GPU
  ✓ POC e desenvolvimento

docling:
  ✓ PDFs com tabelas importantes (financeiros, científicos)
  ✓ PDFs com layout multi-coluna (artigos, jornais)
  ✓ PDFs escaneados (tem OCR integrado)
  ✓ DOCX, PPTX, XLSX junto com PDFs (loader único)
  ✓ Qualidade importa mais que velocidade
```
