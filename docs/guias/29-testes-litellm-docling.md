# Testes práticos — LiteLLM e Docling
**Exemplos prontos para rodar — valide cada etapa antes de integrar ao BuscaAI**

---

## Instalação

```bash
# LiteLLM (modo biblioteca — sem Docker, sem proxy)
pip install litellm

# Docling
pip install docling

# Opcional mas recomendado para os testes
pip install python-dotenv rich
```

Crie um `.env` na raiz do projeto:

```bash
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GROQ_API_KEY=gsk_...
COHERE_API_KEY=...
```

---

## PARTE 1 — LiteLLM

### 1.1 Chamada básica — um provider

```python
import litellm
from dotenv import load_dotenv

load_dotenv()

resposta = litellm.completion(
    model="gpt-4o-mini",
    messages=[
        {"role": "system", "content": "Responda de forma concisa."},
        {"role": "user",   "content": "O que é RAG em uma frase?"}
    ],
    temperature=0.0,
    max_tokens=100,
)

print(resposta.choices[0].message.content)
# → "RAG é uma técnica que combina recuperação de documentos
#    com geração de texto para produzir respostas fundamentadas."
```

---

### 1.2 Trocar de provider — mesma interface

```python
# Só muda o nome do modelo — o código é idêntico

# OpenAI
resposta = litellm.completion(model="gpt-4o-mini", messages=msgs)

# Anthropic
resposta = litellm.completion(model="claude-haiku-4-5", messages=msgs)

# Groq (mais rápido e barato)
resposta = litellm.completion(model="groq/llama-3.1-8b-instant", messages=msgs)

# Gemini
resposta = litellm.completion(model="gemini/gemini-2.0-flash", messages=msgs)

# Ollama local (sem custo de API)
resposta = litellm.completion(
    model="ollama/llama3.2",
    messages=msgs,
    api_base="http://localhost:11434",
)

# A resposta TEM O MESMO FORMATO em todos os casos
print(resposta.choices[0].message.content)   # sempre funciona
print(resposta.usage.total_tokens)           # sempre funciona
```

---

### 1.3 Streaming — tokens aparecem em tempo real

```python
import litellm

stream = litellm.completion(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": "Explique o que é chunking em RAG."}],
    stream=True,
)

for chunk in stream:
    token = chunk.choices[0].delta.content
    if token:
        print(token, end="", flush=True)

print()  # quebra de linha final
```

---

### 1.4 Async — para usar com FastAPI

```python
import asyncio
import litellm

async def gerar_resposta(query: str, contexto: str) -> str:
    prompt = f"""Use apenas o contexto abaixo para responder.

Contexto:
{contexto}

Pergunta: {query}
"""
    resposta = await litellm.acompletion(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Responda com base no contexto fornecido."},
            {"role": "user",   "content": prompt},
        ],
        temperature=0.0,
        max_tokens=500,
    )
    return resposta.choices[0].message.content

# teste
async def main():
    contexto = "O prazo de rescisão contratual é de 30 dias conforme cláusula 8.2."
    resposta = await gerar_resposta("qual o prazo de rescisão?", contexto)
    print(resposta)

asyncio.run(main())
```

---

### 1.5 Fallback automático — degradação graciosa

```python
import litellm

# Se o primeiro falhar, tenta o próximo — automático
litellm.set_verbose = False  # silencia logs de retry

try:
    resposta = litellm.completion(
        model="gpt-4o",         # modelo primário (mais caro)
        messages=[{"role": "user", "content": "Olá!"}],
        fallbacks=[             # lista de fallbacks em ordem
            "gpt-4o-mini",
            "groq/llama-3.1-8b-instant",
            "claude-haiku-4-5",
        ],
        timeout=10,             # abandona se demorar > 10s
    )
    print(resposta.choices[0].message.content)
    print(f"Modelo usado: {resposta.model}")
except Exception as e:
    print(f"Todos os providers falharam: {e}")
```

---

### 1.6 Custo por chamada — alimenta o /metrics do BuscaAI

```python
import litellm

msgs = [{"role": "user", "content": "Qual o prazo de rescisão?"}]

resposta = litellm.completion(
    model="gpt-4o-mini",
    messages=msgs,
)

# custo calculado automaticamente contra tabela de preços embutida
custo = litellm.completion_cost(completion_response=resposta)

print(f"Tokens input:  {resposta.usage.prompt_tokens}")
print(f"Tokens output: {resposta.usage.completion_tokens}")
print(f"Tokens total:  {resposta.usage.total_tokens}")
print(f"Custo USD:     ${custo:.6f}")

# → Tokens input:  312
# → Tokens output: 48
# → Tokens total:  360
# → Custo USD:     $0.000173
```

---

### 1.7 Contar tokens antes de enviar — token budget

```python
import litellm

msgs = [
    {"role": "system", "content": "Você é um assistente."},
    {"role": "user",   "content": "Qual o prazo de rescisão contratual?"},
]

# conta tokens SEM fazer a chamada
n_tokens = litellm.token_counter(model="gpt-4o-mini", messages=msgs)
print(f"Tokens que serão enviados: {n_tokens}")

# limite do modelo
limite = litellm.get_max_tokens("gpt-4o-mini")
print(f"Limite do modelo: {limite}")       # → 128000

# verificar se cabe
if n_tokens < limite * 0.8:               # usa 80% do context window
    print("OK — pode enviar")
else:
    print("AVISO — contexto muito longo, reduza os chunks")
```

---

### 1.8 Embedding — substitui o adaptador manual

```python
import litellm

textos = [
    "O prazo de rescisão é de 30 dias.",
    "A multa por descumprimento é de 10% do valor total.",
    "O contrato entra em vigor na data de assinatura.",
]

# API — OpenAI
resposta = litellm.embedding(
    model="text-embedding-3-small",
    input=textos,
)

vetores = [item["embedding"] for item in resposta.data]
print(f"Dimensão dos vetores: {len(vetores[0])}")   # → 1536
print(f"Custo USD: ${litellm.embedding_cost(resposta):.6f}")

# API — Cohere multilíngue
resposta = litellm.embedding(
    model="cohere/embed-multilingual-v3.0",
    input=textos,
    input_type="search_document",   # cohere precisa desse parâmetro
)

# Local — sem custo de API (requer sentence-transformers)
resposta = litellm.embedding(
    model="huggingface/BAAI/bge-m3",
    input=textos,
)
```

---

### 1.9 Rerank — substitui o adaptador de API de reranker

```python
import litellm

query = "qual o prazo de rescisão contratual?"
chunks = [
    "O contrato entra em vigor na data de assinatura.",
    "O prazo de rescisão contratual é de 30 dias mediante aviso prévio.",
    "A multa por descumprimento é de 10% do valor total.",
    "As partes elegem o foro da comarca de São Paulo.",
]

# Cohere
resultado = litellm.rerank(
    model="cohere/rerank-v3.5",
    query=query,
    documents=chunks,
    top_n=3,
)

for item in resultado.results:
    print(f"[{item.relevance_score:.3f}] {chunks[item.index][:60]}...")

# → [0.974] O prazo de rescisão contratual é de 30 dias...
# → [0.412] A multa por descumprimento é de 10%...
# → [0.088] O contrato entra em vigor...
```

---

### 1.10 Como vai ficar no BuscaAI — função de geração

```python
# busca_ai/generation/llm.py

import litellm
from typing import AsyncGenerator

class LLMProvider:
    """
    Adaptador único para todos os providers via LiteLLM.
    Substitui os adaptadores manuais por provider.
    """

    def __init__(self, config: dict):
        self.config = config

    def _montar_prompt(self, query: str, chunks: list[dict]) -> list[dict]:
        contexto = "\n\n---\n\n".join(
            f"[{i+1}] {c['texto']}" for i, c in enumerate(chunks)
        )
        return [
            {"role": "system", "content": self.config.get("system_prompt",
                "Responda apenas com base nos documentos fornecidos.")},
            {"role": "user", "content": f"Documentos:\n{contexto}\n\nPergunta: {query}"},
        ]

    async def gerar(self, query: str, chunks: list[dict]) -> dict:
        msgs = self._montar_prompt(query, chunks)

        resposta = await litellm.acompletion(
            model    = self.config["model"],
            messages = msgs,
            temperature = self.config.get("temperature", 0.0),
            max_tokens  = self.config.get("max_tokens", 1000),
            fallbacks   = self.config.get("fallbacks", []),
        )

        texto = resposta.choices[0].message.content
        custo = litellm.completion_cost(completion_response=resposta)

        return {
            "resposta": texto,
            "modelo":   resposta.model,
            "tokens":   resposta.usage.total_tokens,
            "custo_usd": custo,
        }

    async def stream(self, query: str, chunks: list[dict]) -> AsyncGenerator:
        msgs = self._montar_prompt(query, chunks)

        async for chunk in await litellm.acompletion(
            model    = self.config["model"],
            messages = msgs,
            stream   = True,
        ):
            token = chunk.choices[0].delta.content
            if token:
                yield token
```

---

## PARTE 2 — Docling

### 2.1 Conversão básica de PDF

```python
from docling.document_converter import DocumentConverter

converter = DocumentConverter()

# converte o PDF
resultado = converter.convert("contrato.pdf")

# acessa o documento estruturado
doc = resultado.document

# exporta como texto plano
print(doc.export_to_text())

# exporta como Markdown (preserva títulos, tabelas, listas)
markdown = doc.export_to_markdown()
print(markdown[:500])
```

---

### 2.2 Exportar em diferentes formatos

```python
from docling.document_converter import DocumentConverter
from pathlib import Path

converter = DocumentConverter()
resultado = converter.convert("relatorio.pdf")
doc = resultado.document

# Markdown — melhor para chunking
markdown = doc.export_to_markdown()
Path("relatorio.md").write_text(markdown, encoding="utf-8")

# JSON — acesso programático à estrutura
import json
dados = doc.export_to_dict()
Path("relatorio.json").write_text(
    json.dumps(dados, ensure_ascii=False, indent=2),
    encoding="utf-8"
)

# texto plano simples
texto = doc.export_to_text()
Path("relatorio.txt").write_text(texto, encoding="utf-8")

print(f"Páginas: {len(resultado.pages)}")
print(f"Chars exportados: {len(markdown)}")
```

---

### 2.3 Extrair metadados do documento

```python
from docling.document_converter import DocumentConverter

converter = DocumentConverter()
resultado = converter.convert("contrato.pdf")
doc = resultado.document

# metadados do cabeçalho
if doc.description:
    d = doc.description
    print(f"Título:   {d.title}")
    print(f"Autores:  {d.authors}")
    print(f"Data:     {d.date_created}")
    print(f"Idioma:   {d.language}")

# estrutura detectada
print(f"\nSeções detectadas:")
for item in doc.texts:
    if hasattr(item, 'label') and 'heading' in str(item.label).lower():
        print(f"  - {item.text[:60]}")

# tabelas detectadas
tabelas = list(doc.tables)
print(f"\nTabelas detectadas: {len(tabelas)}")
for i, tabela in enumerate(tabelas):
    md_tabela = tabela.export_to_markdown()
    print(f"\nTabela {i+1}:\n{md_tabela[:200]}")
```

---

### 2.4 Múltiplos formatos — um único loader

```python
from docling.document_converter import DocumentConverter
from pathlib import Path

# Docling suporta PDF, DOCX, PPTX, XLSX, HTML, imagens, LaTeX
# com a mesma interface

arquivos = [
    "contrato.pdf",
    "relatorio.docx",
    "apresentacao.pptx",
    "dados.xlsx",
    "artigo.html",
]

converter = DocumentConverter()

for caminho in arquivos:
    if not Path(caminho).exists():
        print(f"(arquivo não encontrado: {caminho})")
        continue

    resultado = converter.convert(caminho)
    doc = resultado.document
    markdown = doc.export_to_markdown()

    print(f"\n{'='*50}")
    print(f"Arquivo: {caminho}")
    print(f"Chars:   {len(markdown)}")
    print(f"Prévia:  {markdown[:150].strip()}...")
```

---

### 2.5 Chunking semântico nativo — HybridChunker

```python
from docling.document_converter import DocumentConverter
from docling.chunking import HybridChunker

converter = DocumentConverter()
resultado = converter.convert("contrato.pdf")
doc = resultado.document

# HybridChunker respeita a estrutura do documento
# não corta no meio de títulos, tabelas ou listas
chunker = HybridChunker(
    tokenizer    = "BAAI/bge-m3",   # conta tokens pelo modelo de embedding
    max_tokens   = 512,
    merge_peers  = True,            # une chunks pequenos consecutivos
)

chunks = list(chunker.chunk(doc))

print(f"Total de chunks: {len(chunks)}")

for i, chunk in enumerate(chunks[:5]):
    texto = chunker.serialize(chunk=chunk)
    print(f"\n[Chunk {i+1}] {len(texto.split())} palavras")
    print(f"{texto[:200]}...")
```

---

### 2.6 Comparação com PyMuPDF — test rápido

```python
"""
Rode esse script num PDF problemático (multi-coluna, tabelas, escaneado)
e compare os dois resultados.
"""

from pathlib import Path
import time

ARQUIVO = "seu_pdf_aqui.pdf"   # troque pelo seu arquivo

# ── PyMuPDF ──────────────────────────────────────
import fitz

t0 = time.time()
doc_fitz = fitz.open(ARQUIVO)
texto_pymupdf = "\n\n".join(
    page.get_text("text") for page in doc_fitz
)
doc_fitz.close()
t_pymupdf = time.time() - t0

# ── Docling ───────────────────────────────────────
from docling.document_converter import DocumentConverter

t0 = time.time()
converter = DocumentConverter()
resultado = converter.convert(ARQUIVO)
texto_docling = resultado.document.export_to_markdown()
t_docling = time.time() - t0

# ── Comparação ────────────────────────────────────
print("=" * 60)
print(f"Arquivo: {ARQUIVO}")
print(f"Páginas: {len(resultado.pages)}")
print()
print(f"PyMuPDF  → {len(texto_pymupdf):,} chars em {t_pymupdf:.2f}s")
print(f"Docling  → {len(texto_docling):,} chars em {t_docling:.2f}s")
print()
print("── PyMuPDF (primeiros 400 chars) ──")
print(texto_pymupdf[:400])
print()
print("── Docling (primeiros 400 chars) ──")
print(texto_docling[:400])

# salva ambos para comparar visualmente
Path("output_pymupdf.txt").write_text(texto_pymupdf, encoding="utf-8")
Path("output_docling.md").write_text(texto_docling, encoding="utf-8")
print("\nArquivos salvos: output_pymupdf.txt e output_docling.md")
```

---

### 2.7 PDF com tabelas — onde o Docling se destaca

```python
from docling.document_converter import DocumentConverter

converter = DocumentConverter()
resultado = converter.convert("relatorio_financeiro.pdf")
doc = resultado.document

# tabelas extraídas com estrutura preservada
tabelas = list(doc.tables)
print(f"Tabelas encontradas: {len(tabelas)}")

for i, tabela in enumerate(tabelas):
    print(f"\n── Tabela {i+1} ──")
    # Docling preserva cabeçalhos multi-nível e células mescladas
    print(tabela.export_to_markdown())

# PyMuPDF extrairia isso como "salada de texto" sem estrutura
# Docling mantém linhas, colunas e cabeçalhos intactos
```

---

### 2.8 Múltiplos PDFs em batch

```python
from docling.document_converter import DocumentConverter
from pathlib import Path
import json

def processar_pasta(pasta: str, saida: str = "chunks_output"):
    converter  = DocumentConverter()
    pasta_path = Path(pasta)
    saida_path = Path(saida)
    saida_path.mkdir(exist_ok=True)

    resultados = []

    for pdf in pasta_path.glob("**/*.pdf"):
        print(f"Processando: {pdf.name}")

        try:
            resultado = converter.convert(str(pdf))
            doc       = resultado.document
            markdown  = doc.export_to_markdown()

            # salva markdown
            (saida_path / f"{pdf.stem}.md").write_text(markdown, encoding="utf-8")

            resultados.append({
                "filename":  pdf.name,
                "n_paginas": len(resultado.pages),
                "n_chars":   len(markdown),
                "n_tabelas": len(list(doc.tables)),
                "status":    "ok",
            })

        except Exception as e:
            resultados.append({
                "filename": pdf.name,
                "status":   "erro",
                "erro":     str(e),
            })

    # relatório
    (saida_path / "relatorio.json").write_text(
        json.dumps(resultados, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    ok    = sum(1 for r in resultados if r["status"] == "ok")
    erros = sum(1 for r in resultados if r["status"] == "erro")
    print(f"\nConcluído: {ok} ok, {erros} erros")
    return resultados

# uso
processar_pasta("./meus_pdfs/", "./output/")
```

---

### 2.9 Integração com o pipeline do BuscaAI

```python
# busca_ai/ingestion/loaders/pdf_docling.py

from dataclasses import dataclass
from pathlib import Path
from docling.document_converter import DocumentConverter
from docling.chunking import HybridChunker


@dataclass
class Chunk:
    texto:      str
    doc_id:     str
    filename:   str
    n_tokens:   int
    metadados:  dict


class DoclingPDFLoader:
    """
    Loader de PDF usando Docling como parser.
    Substitui PyMuPDF quando parser='docling' no settings.
    """

    def __init__(self, config: dict):
        self.converter = DocumentConverter()
        self.chunker   = HybridChunker(
            tokenizer  = config.get("embedding_model", "BAAI/bge-m3"),
            max_tokens = config.get("chunk_size", 512),
            merge_peers= True,
        )

    def load(self, caminho: str) -> list[Chunk]:
        path  = Path(caminho)
        doc_id = f"{path.stem}"

        # 1. converte
        resultado = self.converter.convert(caminho)
        doc       = resultado.document

        # 2. metadados do cabeçalho
        meta = {
            "filename":  path.name,
            "n_paginas": len(resultado.pages),
            "n_tabelas": len(list(doc.tables)),
        }
        if doc.description:
            d = doc.description
            meta["titulo"] = d.title or ""
            meta["idioma"] = str(d.language) if d.language else ""

        # 3. chunking semântico
        chunks_doc = list(self.chunker.chunk(doc))
        chunks_out = []

        for i, chunk in enumerate(chunks_doc):
            texto = self.chunker.serialize(chunk=chunk)
            if len(texto.split()) < 10:
                continue   # descarta chunks muito pequenos

            chunks_out.append(Chunk(
                texto     = texto,
                doc_id    = doc_id,
                filename  = path.name,
                n_tokens  = len(texto.split()),
                metadados = {**meta, "chunk_pos": i},
            ))

        return chunks_out


# teste direto
if __name__ == "__main__":
    loader = DoclingPDFLoader(config={"chunk_size": 512})
    chunks = loader.load("contrato.pdf")
    print(f"Chunks gerados: {len(chunks)}")
    for c in chunks[:3]:
        print(f"\n[pos={c.metadados['chunk_pos']}] {c.n_tokens} tokens")
        print(c.texto[:200] + "...")
```

---

## PARTE 3 — LiteLLM + Docling juntos

### 3.1 Pipeline completo de teste — ingerir e perguntar

```python
"""
Pipeline mínimo de teste:
1. Docling extrai e chunka o PDF
2. LiteLLM gera a resposta com os chunks como contexto

Não usa banco vetorial — apenas testa a qualidade
da extração e da geração.
"""

import litellm
from docling.document_converter import DocumentConverter
from docling.chunking import HybridChunker
from dotenv import load_dotenv

load_dotenv()


def extrair_chunks(caminho_pdf: str, max_tokens: int = 512) -> list[str]:
    converter = DocumentConverter()
    resultado = converter.convert(caminho_pdf)
    doc       = resultado.document

    chunker = HybridChunker(
        tokenizer  = "BAAI/bge-m3",
        max_tokens = max_tokens,
    )
    chunks = list(chunker.chunk(doc))
    return [chunker.serialize(c) for c in chunks]


def recuperar_chunks_simples(query: str, chunks: list[str], top_k: int = 5) -> list[str]:
    """
    Recuperação ingênua por overlap de palavras.
    Substitua por busca vetorial real depois.
    """
    query_words = set(query.lower().split())
    scored = []
    for chunk in chunks:
        chunk_words = set(chunk.lower().split())
        score = len(query_words & chunk_words)
        scored.append((score, chunk))
    scored.sort(reverse=True)
    return [c for _, c in scored[:top_k]]


def perguntar(query: str, chunks_relevantes: list[str]) -> dict:
    contexto = "\n\n---\n\n".join(chunks_relevantes)
    msgs = [
        {"role": "system", "content":
            "Responda APENAS com base nos documentos fornecidos. "
            "Se não encontrar a informação, diga 'não encontrado nos documentos'."},
        {"role": "user", "content":
            f"Documentos:\n{contexto}\n\nPergunta: {query}"},
    ]

    resposta = litellm.completion(
        model       = "gpt-4o-mini",
        messages    = msgs,
        temperature = 0.0,
        max_tokens  = 500,
    )

    custo = litellm.completion_cost(completion_response=resposta)

    return {
        "resposta":  resposta.choices[0].message.content,
        "modelo":    resposta.model,
        "tokens":    resposta.usage.total_tokens,
        "custo_usd": custo,
        "chunks_usados": len(chunks_relevantes),
    }


# ── TESTE ──────────────────────────────────────────────────────────
PDF = "contrato.pdf"   # troque pelo seu arquivo

print("1. Extraindo chunks com Docling...")
todos_chunks = extrair_chunks(PDF)
print(f"   {len(todos_chunks)} chunks gerados")

perguntas = [
    "qual o prazo de rescisão contratual?",
    "qual a multa por descumprimento?",
    "quem são as partes do contrato?",
    "qual o foro de eleição?",
]

for pergunta in perguntas:
    print(f"\n{'─'*50}")
    print(f"Pergunta: {pergunta}")

    chunks_rel = recuperar_chunks_simples(pergunta, todos_chunks, top_k=3)

    resultado = perguntar(pergunta, chunks_rel)
    print(f"Resposta: {resultado['resposta']}")
    print(f"Modelo:   {resultado['modelo']}")
    print(f"Tokens:   {resultado['tokens']} (${resultado['custo_usd']:.5f})")
```

---

## Checklist de testes

```
LITELLM
  [ ] 1.1 Chamada básica responde sem erro
  [ ] 1.2 Troca de provider funciona (OpenAI → Groq → Ollama)
  [ ] 1.3 Streaming imprime tokens progressivamente
  [ ] 1.4 Async funciona com asyncio.run()
  [ ] 1.5 Fallback ativa quando primeiro provider falha
  [ ] 1.6 Custo calculado e não é zero
  [ ] 1.7 Token counter retorna número razoável
  [ ] 1.8 Embedding retorna vetor com dimensão correta (1536 para text-3-small)
  [ ] 1.9 Rerank ordena chunks por relevância corretamente

DOCLING
  [ ] 2.1 PDF converte sem erro
  [ ] 2.2 Markdown exportado tem títulos # preservados
  [ ] 2.3 Metadados extraídos (título, idioma)
  [ ] 2.4 DOCX/PPTX converte com a mesma interface
  [ ] 2.5 HybridChunker não corta no meio de frases
  [ ] 2.6 Docling > PyMuPDF em PDF com tabelas (checar visualmente)
  [ ] 2.7 Tabelas exportam com estrutura de linhas e colunas
  [ ] 2.8 Batch de PDFs processa sem crash

INTEGRADO
  [ ] 3.1 Pipeline completo: PDF → chunks → pergunta → resposta coerente
  [ ] 3.1 Resposta não alucina (está nos chunks)
  [ ] 3.1 Custo por pergunta está dentro do esperado
```
