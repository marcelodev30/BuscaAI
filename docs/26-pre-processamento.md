# Pré-Processamento de Documentos — BuscaAI

O pré-processamento é a etapa que transforma documentos brutos (PDF, CSV, DOCX...)
em texto limpo, estruturado e enriquecido com metadados — pronto para ser
dividido em chunks e indexado no banco de busca.

Uma boa ingestão começa com um bom pré-processamento.
Texto sujo, hifenações quebradas ou cabeçalhos repetidos em todos os chunks
prejudicam diretamente a qualidade do retrieval.

---

## Sumário

1. [Visão geral do pipeline](#1-visão-geral-do-pipeline)
2. [Validação inicial](#2-validação-inicial)
3. [Hash e deduplicação](#3-hash-e-deduplicação)
4. [Extração de metadados](#4-extração-de-metadados)
5. [Detecção do tipo de conteúdo](#5-detecção-do-tipo-de-conteúdo)
6. [Extração de texto por tipo de arquivo](#6-extração-de-texto-por-tipo-de-arquivo)
7. [Docling — parser alternativo com estrutura](#7-docling--parser-alternativo-com-estrutura)
8. [Operações de limpeza de texto](#8-operações-de-limpeza-de-texto)
9. [Detecção de estrutura](#9-detecção-de-estrutura)
10. [Enriquecimento NLP](#10-enriquecimento-nlp)
11. [Validação do texto limpo](#11-validação-do-texto-limpo)
12. [Saída — documento normalizado](#12-saída--documento-normalizado)
13. [Configuração no BuscaAI](#13-configuração-no-buscaai)
14. [Referências](#14-referências)

---

## 1. Visão geral do pipeline

```
arquivo bruto (PDF, CSV, DOCX, MD, SQL...)
              ↓
    ┌─────────────────────┐
    │  1. VALIDAÇÃO       │  tamanho · mime-type · integridade
    └────────┬────────────┘
             ↓
    ┌─────────────────────┐
    │  2. HASH + DEDUP    │  SHA-256 · compara com SQLite
    └────────┬────────────┘
             ↓ (novo ou alterado)
    ┌─────────────────────┐
    │  3. METADADOS       │  cabeçalho XMP · estruturais · origem
    └────────┬────────────┘
             ↓
    ┌─────────────────────┐
    │  4. DETECÇÃO        │  tipo do arquivo · nativo vs escaneado
    └────────┬────────────┘
             ↓
    ┌─────────────────────┐
    │  5. EXTRAÇÃO        │  PyMuPDF · pandas · python-docx · BS4
    └────────┬────────────┘
             ↓
    ┌─────────────────────┐
    │  6. LIMPEZA         │  7 operações em sequência (ver seção 7)
    └────────┬────────────┘
             ↓
    ┌─────────────────────┐
    │  7. ESTRUTURA       │  títulos · tabelas · colunas · listas
    └────────┬────────────┘
             ↓
    ┌─────────────────────┐
    │  8. ENRIQUECIMENTO  │  NER · idioma · tipo de documento
    └────────┬────────────┘
             ↓
    ┌─────────────────────┐
    │  9. VALIDAÇÃO FINAL │  tokens úteis · idioma · status
    └────────┬────────────┘
             ↓
    documento normalizado → chunking → embedding → banco de busca
```

O pré-processamento opera **por documento**. Um job de ingestão de 100k documentos
processa cada um independentemente, com checkpoint a cada 1.000 para retomar
em caso de falha.

> **Dois caminhos de extração:** o pipeline acima descreve o parser padrão
> (PyMuPDF), onde as etapas 5–9 são feitas manualmente. Com o parser
> alternativo **Docling** (seção 7), as etapas de remoção de headers/footers,
> detecção de estrutura e detecção de tabelas são feitas nativamente pela
> extração — reduzindo o trabalho das etapas 6–8.

---

## 2. Validação inicial

Antes de abrir o arquivo, verifica:

```
VALIDAÇÃO                   CRITÉRIO                    FALHA
─────────────────────────────────────────────────────────────────
tamanho máximo              ≤ 100MB (configurável)      HTTP 413
mime-type                   deve corresponder à extensão HTTP 415
integridade (PDF)           arquivo não corrompido       erro descritivo
senha (PDF)                 não protegido por senha      aviso + skip
```

**Por que é importante:**
Arquivos corrompidos ou protegidos descobertos só na hora da extração geram
erros difíceis de rastrear. A validação inicial falha rápido com mensagem clara,
sem gastar tokens de embedding ou chamar APIs.

```python
def validar_arquivo(caminho: Path) -> None:
    if caminho.stat().st_size > LIMITS["max_file_size_mb"] * 1024 * 1024:
        raise ValueError(f"Arquivo muito grande: {caminho.name}")

    mime = mimetypes.guess_type(caminho)[0]
    if mime not in MIME_PERMITIDOS:
        raise ValueError(f"Tipo não suportado: {mime}")
```

---

## 3. Hash e deduplicação

```python
hash_sha256 = hashlib.sha256(caminho.read_bytes()).hexdigest()
```

O hash SHA-256 é gerado sobre o conteúdo **binário** do arquivo, antes de qualquer
processamento. Serve para três coisas:

```
1. DEDUPLICAÇÃO EXATA
   Hash já existe no SQLite?
     → sim: arquivo não mudou → skip completo (zero custo)
     → sim mas source_id diferente: mesmo arquivo, fonte diferente → skip
     → não: arquivo novo ou alterado → processa normalmente

2. ATUALIZAÇÃO INCREMENTAL
   Hash diferente para o mesmo source_id:
     → conteúdo mudou → remove chunks antigos do banco → reindexa

3. RASTREABILIDADE
   Hash salvo como doc_id no banco — permite localizar qualquer chunk
   no arquivo original, independente do nome do arquivo.
```

**O que o hash NÃO detecta:**
Dois arquivos com mesmo conteúdo mas metadados diferentes (autor, data) têm
hashes diferentes se os metadados estiverem embutidos no binário.
Para esses casos, o campo `source_id` (caminho relativo ou ID da fonte) desambigua.

---

## 4. Extração de metadados

### 4.1 Metadados do cabeçalho (XMP/Info — PDF)

Gravados por quem criou ou exportou o arquivo. Nem sempre presentes.

```
CAMPO           EXEMPLO                          DISPONIBILIDADE
──────────────────────────────────────────────────────────────────
title           "Contrato de Prestação nº 42"    ~60% dos PDFs
author          "João Silva"                      ~55%
subject         "Contratos Comerciais"            ~40%
keywords        "contrato, rescisão, prazo"       ~30%
creator         "Microsoft Word"                  ~80%
producer        "Adobe PDF Library 15.0"          ~85%
creationDate    "2024-03-15T10:32:00+03:00"       ~90%
modDate         "2024-11-20T08:00:00"             ~85%
lang            "pt-BR"                           ~25%
```

```python
doc = fitz.open(caminho)
meta = doc.metadata
titulo    = meta.get("title",        "")
autor     = meta.get("author",       "")
criado_em = meta.get("creationDate", "")
```

### 4.2 Metadados estruturais (sempre disponíveis)

```
CAMPO               COMO EXTRAIR
────────────────────────────────────────────────────
n_paginas           doc.page_count
tamanho_bytes       os.path.getsize()
versao_pdf          doc.pdf_version()
tem_senha           doc.needs_pass
esta_criptografado  doc.is_encrypted
n_imagens           sum(len(p.get_images()) for p in doc)
orientacao          [p.rotation for p in doc]
```

### 4.3 Metadados de origem

```
CAMPO               FONTE
────────────────────────────────────────────
filename            Path(caminho).name
source              settings SOURCES (nome da fonte configurada)
collection          chave no bloco SOURCES
ingestao_data       datetime.now()
modelo_embedding    EMBEDDINGS["dense"]["model"]
chunking_strategy   CHUNKING["strategy"]
```

---

## 5. Detecção do tipo de conteúdo

### Para PDF: nativo vs escaneado

```python
def detectar_tipo_pdf(doc: fitz.Document) -> str:
    nativas = escaneadas = 0
    for page in doc:
        n_chars = len(page.get_text("text").strip())
        n_imgs  = len(page.get_images())
        if n_chars < 50 and n_imgs > 0:
            escaneadas += 1
        elif n_chars >= 50:
            nativas += 1
        else:
            escaneadas += 1

    pct_nativo = nativas / doc.page_count
    if pct_nativo >= 0.85:   return "nativo"
    elif pct_nativo <= 0.15: return "escaneado"
    else:                    return "misto"
```

```
TIPO          TRATAMENTO
──────────────────────────────────────────────────────────────────
nativo        extração direta via PyMuPDF (texto já está no arquivo)
escaneado     aviso: texto pode estar vazio sem OCR habilitado
misto         processa por página — nativas extraem, escaneadas ficam vazias
```

> **Nota sobre OCR:** o BuscaAI não inclui OCR por padrão. PDFs escaneados
> recebem aviso no log e são processados com o texto que o PyMuPDF conseguir
> extrair. Para habilitar OCR, configure `CHUNKING["ocr"] = True` e instale
> `pytesseract + tesseract-ocr`.

### Para outros tipos: por extensão e mime-type

```
EXTENSÃO        LOADER              FALLBACK
──────────────────────────────────────────────────────────
.pdf            PyMuPDF             —
.docx           python-docx         —
.pptx           python-pptx         —
.csv            pandas              —
.xlsx           pandas (openpyxl)   —
.md             mistune             texto plano
.html           BeautifulSoup4      texto plano
.txt            leitura direta      —
.py .js .sql    tree-sitter         texto plano
sem extensão    magic bytes         texto plano
```

---

## 6. Extração de texto por tipo de arquivo

### PDF — extração nativa

```python
def extrair_texto_nativo(doc: fitz.Document) -> dict[int, str]:
    """Retorna {numero_pagina: texto} para cada página."""
    return {
        i + 1: page.get_text("text")
        for i, page in enumerate(doc)
    }
```

O método `get_text("text")` retorna texto na ordem de leitura (não de posição
no PDF). Para PDFs com layout complexo (múltiplas colunas, tabelas), use
`get_text("dict")` que retorna blocos com coordenadas.

### PDF — extração com layout (pdfplumber)

Para tabelas e PDFs com layout complexo:

```python
import pdfplumber

with pdfplumber.open(caminho) as pdf:
    for page in pdf.pages:
        tabelas = page.extract_tables()   # lista de tabelas como listas de listas
        texto   = page.extract_text()     # texto respeitando layout de colunas
```

### CSV / Excel

```python
import pandas as pd

df = pd.read_csv(caminho, encoding="utf-8")

# cada linha vira um documento
for _, row in df.iterrows():
    texto     = " ".join(str(v) for v in row[CHUNKING["text_columns"]])
    metadados = {col: row[col] for col in CHUNKING["metadata_columns"]}
```

### DOCX

```python
from docx import Document

doc = Document(caminho)
paragrafos = [p.text for p in doc.paragraphs if p.text.strip()]
texto = "\n\n".join(paragrafos)
```

### Markdown e HTML

```python
import mistune
from bs4 import BeautifulSoup

# Markdown → texto limpo
html = mistune.html(conteudo_md)
texto = BeautifulSoup(html, "html.parser").get_text(separator="\n")

# HTML direto → texto limpo
soup = BeautifulSoup(conteudo_html, "html.parser")
for tag in soup(["script", "style", "nav", "footer"]):
    tag.decompose()
texto = soup.get_text(separator="\n")
```

### Código-fonte

```python
# tree-sitter preserva funções e classes intactas
# fallback: extração como texto plano
texto = caminho.read_text(encoding="utf-8", errors="replace")
```

---

## 7. Docling — parser alternativo com estrutura

As seções 5 e 6 descrevem o pipeline padrão com PyMuPDF, que extrai
**texto bruto** — você limpa e estrutura depois (seções 8 e 9). O Docling
é um parser alternativo que extrai o texto **já estruturado**, fazendo
nativamente boa parte do trabalho das operações de limpeza e detecção
de estrutura.

```
PyMuPDF:  PDF → texto bruto → limpeza → detecção de estrutura → chunks
Docling:  PDF → texto estruturado (headers/footers removidos,
                tabelas detectadas, ordem de leitura correta) → chunks
```

O Docling é **opcional e configurável** via `CHUNKING["parser"]`. Não
substitui o PyMuPDF — os dois coexistem, e o desenvolvedor escolhe por
caso. PDFs simples continuam com PyMuPDF (rápido); PDFs complexos,
escaneados ou com tabelas usam Docling (preciso).

### 7.1 O que o Docling faz nativamente

```
OPERAÇÃO DO PIPELINE PADRÃO          DOCLING FAZ NATIVAMENTE?
──────────────────────────────────────────────────────────────────
OP 2 — remover headers/footers       ✓ sim (label PAGE_HEADER/FOOTER)
OP 3 — reconstruir hifenação         ✓ parcial (depende do PDF)
detecção de ordem de leitura          ✓ sim (mesmo multi-coluna)
detecção de tabelas (seção 8)        ✓ sim (estrutura preservada)
detecção de títulos (seção 8)        ✓ sim (label SECTION_HEADER)
OCR de escaneados                     ✓ sim (integrado)
OP 1 — encoding                       ⚠ ainda pode ser necessário
OP 6 — normalização textual           ⚠ ainda pode ser necessário
```

### 7.2 Extração básica com Docling

```python
from docling.document_converter import DocumentConverter

# instancia UMA vez (carrega modelos de ML — lento no startup)
converter = DocumentConverter()

resultado = converter.convert("contrato.pdf")
doc = resultado.document

# exporta como Markdown — preserva títulos, tabelas, listas
markdown = doc.export_to_markdown()
```

### 7.3 Por que salvar como JSON intermediário

O Docling é lento (roda modelos de ML). Salvar a estrutura extraída como
JSON permite **re-chunkar sem reprocessar o PDF**:

```
SEM JSON intermediário:
  muda chunk_size → reprocessa o PDF inteiro no Docling (lento)

COM JSON intermediário:
  processa o PDF uma vez → salva JSON
  muda chunk_size → recarrega JSON → re-chunka (rápido)
```

> **Importante:** JSON é apenas o *recipiente* onde a estrutura fica
> guardada. O que estrutura o conteúdo é a extração do Docling — não o
> formato JSON em si. Converter um PDF para JSON sem um parser que
> entende o documento não estrutura nada.

### 7.4 PDF → JSON → chunks

```python
from docling.document_converter import DocumentConverter
from docling_core.types.doc import DoclingDocument
from docling.chunking import HybridChunker
from pathlib import Path
import json

# ── Passo 1: PDF → JSON (roda o Docling uma vez) ──
converter = DocumentConverter()
resultado = converter.convert("contrato.pdf")
doc = resultado.document

Path("contrato.json").write_text(
    json.dumps(doc.export_to_dict(), ensure_ascii=False, indent=2),
    encoding="utf-8"
)

# ── Passo 2: JSON → DoclingDocument (rápido, sem reprocessar) ──
dados = json.loads(Path("contrato.json").read_text(encoding="utf-8"))
doc   = DoclingDocument.model_validate(dados)

# ── Passo 3: DoclingDocument → chunks ──
chunker = HybridChunker(tokenizer="BAAI/bge-m3", max_tokens=512)
chunks  = list(chunker.chunk(doc))

for i, chunk in enumerate(chunks):
    texto = chunker.serialize(chunk=chunk)
    print(f"[{i}] {len(texto.split())} palavras: {texto[:80]}...")
```

### 7.5 Cache de pré-processamento indexado por hash

No BuscaAI, o JSON intermediário vira um **cache de pré-processamento**
indexado pelo mesmo hash SHA-256 usado na deduplicação (seção 3). Se o
PDF não mudou, pula o Docling e usa o JSON do cache:

```python
import hashlib
import json
from pathlib import Path
from docling.document_converter import DocumentConverter
from docling_core.types.doc import DoclingDocument
from docling.chunking import HybridChunker

converter = DocumentConverter()

def processar_com_cache(caminho_pdf: str, pasta_cache: str = "./cache_docling"):
    pdf_bytes = Path(caminho_pdf).read_bytes()
    doc_hash  = hashlib.sha256(pdf_bytes).hexdigest()
    cache_json = Path(pasta_cache) / f"{doc_hash}.json"

    if cache_json.exists():
        # CACHE HIT — pula o Docling (lento)
        dados = json.loads(cache_json.read_text(encoding="utf-8"))
        doc   = DoclingDocument.model_validate(dados)
    else:
        # CACHE MISS — roda o Docling e salva o JSON
        resultado = converter.convert(caminho_pdf)
        doc = resultado.document
        cache_json.parent.mkdir(exist_ok=True)
        cache_json.write_text(
            json.dumps(doc.export_to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

    # chunking a partir do doc (do cache ou recém-processado)
    chunker = HybridChunker(tokenizer="BAAI/bge-m3", max_tokens=512)
    return list(chunker.chunk(doc))
```

```
FLUXO COM CACHE
───────────────────────────────────────────────────────────────
SOURCES → hash SHA-256 → cache JSON existe?
                              ├── sim → carrega JSON → chunking
                              └── não → Docling → salva JSON → chunking
                                              ↓
                                    chunking → embedding → Qdrant
```

Isso combina com a deduplicação por hash da seção 3: o hash do PDF é a
chave do cache. PDF inalterado = JSON já pronto = sem custo de Docling.

### 7.6 JSON vs Markdown como intermediário

```
JSON (export_to_dict):
  ✓ preserva TODA a estrutura (tabelas, labels, coordenadas, metadados)
  ✓ reconstrói o DoclingDocument exato via model_validate()
  ✓ melhor para re-chunkar com HybridChunker
  ✗ arquivo maior, menos legível

MARKDOWN (export_to_markdown):
  ✓ legível por humanos
  ✓ menor e mais simples
  ✓ bom para chunking por seção (#, ##) com MarkdownHeaderTextSplitter
  ✗ perde metadados estruturais (labels, coordenadas)
```

Regra prática: use **JSON** se for re-chunkar com o HybridChunker do
Docling; use **Markdown** se for chunkar por cabeçalho ou se quiser
inspecionar o texto extraído manualmente.

### 7.7 Quando usar Docling vs PyMuPDF

```
PyMuPDF (parser padrão):
  ✓ PDFs digitais simples (texto corrido sem tabelas)
  ✓ volume alto — precisa de velocidade
  ✓ hardware sem GPU
  ✓ POC e desenvolvimento

Docling (parser alternativo):
  ✓ PDFs com tabelas importantes (financeiros, científicos)
  ✓ PDFs multi-coluna (artigos, laudos, jornais)
  ✓ PDFs escaneados (OCR integrado)
  ✓ DOCX, PPTX, XLSX junto com PDFs (loader único)
  ✓ qualidade importa mais que velocidade
```

---

## 8. Operações de limpeza de texto

Aplicadas em sequência sobre o texto bruto extraído.
Cada operação é atômica — pode ser ativada/desativada individualmente.

---

### Operação 1 — Normalização de encoding

**O que faz:** força UTF-8 e substitui caracteres Unicode problemáticos.

```
SUBSTITUI                               POR
────────────────────────────────────────────────────────────
\u201c \u201d (aspas curvas duplas)     "   "
\u2018 \u2019 (aspas curvas simples)    '   '
\u2013        (en-dash)                 -
\u2014        (em-dash)                 -
\u00a0        (non-breaking space)      espaço normal
\u00ad        (soft hyphen)             (remove)
\u200b        (zero-width space)        (remove)
\ufeff        (BOM)                     (remove)
\t            (tab)                     espaço
\x00–\x1f    (controle, exceto \n)     (remove)
```

**Exemplo:**
```
antes: "cláusula\xa0nº\u00a03"
depois: "cláusula nº 3"
```

---

### Operação 2 — Remoção de cabeçalhos e rodapés

**O que faz:** detecta e remove linhas que aparecem em ≥ 70% das páginas.

**Algoritmo:**
```
1. Para cada página, extrai as 3 primeiras e 3 últimas linhas
2. Conta a frequência de cada linha normalizada no documento
3. Linhas com frequência ≥ 70% das páginas → candidatas a header/footer
4. Remove essas linhas de todas as páginas
```

**Exemplos do que é removido:**
```
"Confidencial — ACME S.A."          (header corporativo)
"Página 3 de 42"                    (numeração de página)
"www.empresa.com.br"                (rodapé com site)
"Documento gerado em 15/03/2024"    (data de geração)
```

**O que não é removido:**
- Títulos de seção únicos (aparecem em < 70% das páginas)
- Numeração sequencial diferente por página (1, 2, 3... — são diferentes)

```python
def remover_headers_footers(paginas, threshold=0.70):
    n = len(paginas)
    contador = Counter()
    for texto in paginas.values():
        linhas = texto.splitlines()
        candidatas = linhas[:3] + linhas[-3:]
        for linha in candidatas:
            norm = linha.strip().lower()
            if len(norm) > 3:
                contador[norm] += 1

    remover = {l for l, f in contador.items() if f / n >= threshold}
    # aplica remoção em todas as páginas
```

---

### Operação 3 — Reconstrução de hifenação

**O que faz:** une palavras quebradas com hífen no final de linha.

**Padrão detectado:** `(\w+)-\n([a-záàâãA-Z]\w*)`

**Exemplos:**
```
antes: "rescis-\não contratual"    → depois: "rescisão contratual"
antes: "dis-\nponível"             → depois: "disponível"
antes: "respon-\nsabilidade"       → depois: "responsabilidade"
```

**O que NÃO é modificado** (hífens legítimos):
```
"guarda-chuva"   → preservado (hífen composto)
"sub-item"       → preservado (prefixo)
"pré-natal"      → preservado (prefixo com acento)
```

**Critério de distinção:** o algoritmo verifica se a continuação começa
com letra minúscula (típico de quebra de linha) ou se a palavra antes do
hífen é um prefixo comum (sub, pré, ex, auto...).

---

### Operação 4 — Normalização de espaços e quebras

**O que faz:**

```
ANTES                           DEPOIS
──────────────────────────────────────────────────────────
"O   contrato  foi"             "O contrato foi"
"\n\n\n\n\n"                    "\n\n"
"  linha com espaço  "          "linha com espaço"
"O contrato\nfoi assinado"      "O contrato foi assinado"
  (quebra dentro de parágrafo)
```

**Lógica de quebra de linha dentro de parágrafo:**
```python
# se a linha termina sem ponto e a próxima começa com minúscula
# → é quebra de linha de PDF, não parágrafo novo → une
if not linha.endswith(('.', '!', '?', ':')) and proxima[0].islower():
    buffer += " " + proxima
else:
    paragrafos.append(buffer)
    buffer = proxima
```

---

### Operação 5 — Remoção de artefatos de extração

**O que faz:** remove lixo típico da extração de PDF.

**Artefatos tratados:**

```
TIPO                        EXEMPLO                  AÇÃO
──────────────────────────────────────────────────────────────────
Ligaduras tipográficas      ﬁ ﬀ ﬃ ﬄ                  fi ff ffi ffl
Coordenadas PostScript      "0 0 Td" "12.3 Tf"       remove
Linhas só de números        "3 . 5 . 2 . 1"           remove
Texto de marca d'água       "RASCUNHO" (baixa opac.)  remove se repetido
Caracteres NULL             \x00 embutidos em texto   remove
```

**Ligaduras tipográficas — tabela completa:**
```
\ufb00 → ff    \ufb01 → fi    \ufb02 → fl
\ufb03 → ffi   \ufb04 → ffl   \ufb05 → st
```

---

### Operação 6 — Normalização textual

**O que faz:** expande abreviações comuns e corrige formatação de números.

**Abreviações expandidas (PT-BR):**
```
Art.     → Artigo        arts.    → artigos
Par.     → Parágrafo     par.     → parágrafo
Cláus.   → Cláusula      cláus.   → cláusula
pg.      → página        pgs.     → páginas
nr.      → número        nº       → número
doc.     → documento
```

**Por que expandir:**
`"Art. 8º"` e `"Artigo 8"` têm embeddings diferentes.
Expandindo, o retrieval melhora para queries que usam a forma completa.

**Normalização de números:**
```
"1 . 000,00"  → "1.000,00"  (espaço antes do ponto de milhar)
"R$ 50 .000"  → "R$ 50.000" (espaço antes do ponto)
```

**O que NÃO é alterado:**
- Valores monetários: `"R$ 1.000,00"` — preservado exatamente
- Datas: `"15/03/2024"` — preservada, mas adicionada como metadado
- CPF/CNPJ: preservados (ou removidos se `LIMITS["strip_pii"] = True`)

---

### Operação 7 — Validação do texto limpo

**O que faz:** verifica se o texto resultante tem conteúdo útil.

```python
def validar(texto: str) -> tuple[bool, str]:
    # conta palavras com 2+ letras
    tokens_uteis = len(re.findall(r"\b[a-záàâãA-Z]{2,}\b", texto))

    if tokens_uteis < 20:
        return False, "?"   # texto vazio ou só pontuação

    idioma = detect_lang(texto[:500]) if HAS_LANGDETECT else "?"
    return True, idioma
```

**Resultados possíveis:**
```
valido=True,  idioma="pt"  → segue para chunking
valido=True,  idioma="en"  → segue para chunking com tokenização EN
valido=False, idioma="?"   → status "empty" no SQLite, sem chunking
```

**Por que o threshold de 20 tokens:**
Documentos com menos de 20 palavras úteis geralmente são:
- PDFs escaneados sem OCR (só imagem, sem texto)
- Arquivos de capa ou separador
- Metadados em formato não textual

Esses documentos são registrados como `status = "empty"` no SQLite
para não desperdiçar chamadas de embedding.

---

## 9. Detecção de estrutura

Feita **depois** da limpeza, para guiar o chunking.

### Títulos e seções

```python
# título detectado pelo tamanho de fonte relativo ao corpo do texto
for bloco in page.get_text("dict")["blocks"]:
    for linha in bloco["lines"]:
        tamanho_fonte = linha["spans"][0]["size"]
        if tamanho_fonte > tamanho_medio_corpo * 1.3:
            # é um título — marca como fronteira de chunk
```

### Tabelas

```python
# via pdfplumber
with pdfplumber.open(caminho) as pdf:
    for page in pdf.pages:
        tabelas = page.extract_tables()
        # cada tabela vira um chunk separado com cabeçalho preservado
```

### Múltiplas colunas

```python
# detectado pela distribuição de coordenadas X dos blocos
xs = [bloco["bbox"][0] for bloco in blocos_de_texto]
if max(xs) - min(xs) > largura_pagina * 0.4:
    # provavelmente layout de 2+ colunas → reordena por coluna
```

**Impacto no chunking:**
A estrutura detectada define onde o chunker pode e não pode cortar:
- Não corta no meio de um título
- Não corta no meio de uma tabela
- Não corta no meio de uma lista numerada

---

## 10. Enriquecimento NLP

Opcional. Extrai informações semânticas do texto para enriquecer o payload
de metadados — habilitando filtros mais ricos no banco de busca.

### Reconhecimento de entidades (NER)

```python
import spacy
nlp = spacy.load("pt_core_news_sm")

doc = nlp(texto[:10000])  # primeiros 10k chars (eficiência)

entidades = {
    "pessoas":        [e.text for e in doc.ents if e.label_ == "PER"],
    "organizacoes":   [e.text for e in doc.ents if e.label_ == "ORG"],
    "locais":         [e.text for e in doc.ents if e.label_ == "LOC"],
    "datas":          [e.text for e in doc.ents if e.label_ == "DATE"],
    "valores":        [e.text for e in doc.ents if e.label_ == "MONEY"],
}
```

### Detecção de idioma

```python
from langdetect import detect
idioma = detect(texto[:500])   # "pt", "en", "es"...
```

### Classificação de tipo de documento

```python
# classificador simples por palavras-chave
TIPOS_DOC = {
    "contrato":   ["cláusula", "rescisão", "partes", "obrigações"],
    "laudo":      ["diagnóstico", "exame", "resultado", "paciente"],
    "relatório":  ["relatório", "análise", "conclusão", "período"],
    "artigo":     ["abstract", "introdução", "metodologia", "referências"],
    "lei":        ["artigo", "parágrafo", "inciso", "lei nº"],
}

def classificar_tipo(texto: str) -> str:
    texto_lower = texto[:2000].lower()
    scores = {
        tipo: sum(1 for kw in keywords if kw in texto_lower)
        for tipo, keywords in TIPOS_DOC.items()
    }
    return max(scores, key=scores.get) if max(scores.values()) > 0 else "generico"
```

**Custo e configuração:**
```python
CHUNKING = {
    "nlp": {
        "enabled":  True,      # False para desligar enriquecimento
        "ner":      True,      # entidades nomeadas
        "classify": True,      # tipo de documento
        "language": True,      # detecção de idioma (já embutida na validação)
    }
}
```

---

## 11. Validação do texto limpo

A segunda validação (a primeira foi no passo 2) verifica a qualidade
do texto **após** todas as operações de limpeza:

```
VERIFICAÇÃO                  CRITÉRIO               AÇÃO EM FALHA
──────────────────────────────────────────────────────────────────────
tokens úteis                 ≥ 20 palavras          status "empty"
idioma detectável            langdetect funciona    idioma = "?"
redução excessiva            > 90% dos chars        aviso no log
encoding válido              UTF-8 válido           erro descritivo
```

### Estatísticas salvas no SQLite

```python
stats = {
    "chars_bruto":          len(texto_bruto),
    "chars_limpo":          len(texto_limpo),
    "reducao_pct":          (chars_bruto - chars_limpo) / chars_bruto * 100,
    "headers_removidos":    n_linhas_removidas,
    "palavras_dehifenadas": n_dehifenadas,
    "ligaduras_corrigidas": n_ligaduras,
    "ops_aplicadas":        ["encoding", "headers_footers", "hifenacao", ...],
    "avisos":               ["PDF escaneado detectado"] if escaneado else [],
}
```

Essas estatísticas ajudam a identificar documentos problemáticos e
calibrar os thresholds de limpeza.

---

## 12. Saída — documento normalizado

O resultado do pré-processamento é um objeto `Document` com texto limpo
e payload completo de metadados:

```python
@dataclass
class Document:
    # identidade
    doc_id:        str   # hash SHA-256
    source_id:     str   # "contratos/contrato_xyz.pdf"
    chunk_offset:  int   # índice na lista de docs (antes do chunking)

    # texto limpo
    text:          str

    # metadados do arquivo
    filename:      str
    source:        str   # nome da fonte configurada
    mime_type:     str
    tamanho_bytes: int
    n_paginas:     int   # só PDF/DOCX

    # metadados do cabeçalho (PDF)
    titulo:        str
    autor:         str
    criado_em:     str
    modificado_em: str
    criador_app:   str

    # metadados de conteúdo (NLP)
    idioma:        str   # "pt", "en"...
    tipo_documento:str   # "contrato", "laudo"...
    entidades:     dict  # {pessoas: [...], orgs: [...]}

    # metadados de ingestão
    ingestao_data:    str
    modelo_embedding: str
    chunking_strategy:str
    status:           str  # "pending" → chunking vai processar

    # estatísticas de limpeza
    stats:         LimpezaStats
```

Este objeto vai para o **chunking** — que divide o `text` em chunks,
replicando todos os metadados para cada chunk gerado, adicionando
`chunk_pos`, `n_tokens` e `pagina`.

---

## 13. Configuração no BuscaAI

```python
# rag_settings.py

CHUNKING = {
    # parser de PDF: pymupdf (padrão, rápido) | docling (preciso, lento)
    "parser":     "pymupdf",

    # cache de pré-processamento do Docling (JSON indexado por hash)
    # evita reprocessar o PDF ao re-chunkar; só usado com parser=docling
    "docling_cache": {
        "enabled": True,
        "path":    "./cache_docling",
        "format":  "json",     # json (estrutura completa) | markdown
    },

    # estratégia de chunking (aplicada após pré-processamento)
    "strategy":   "auto",    # recursive | semantic | markdown | auto
    "chunk_size": 512,
    "overlap":    50,

    # configuração de OCR (desabilitado por padrão)
    # com parser=docling, o OCR é integrado e ativa só em páginas escaneadas
    "ocr": {
        "enabled":  False,
        "lang":     "por+eng",  # idiomas do Tesseract (parser=pymupdf)
        "dpi":      300,
    },

    # colunas de texto e metadados para fontes tabulares (CSV/SQL)
    "text_columns":     ["titulo", "conteudo", "descricao"],
    "metadata_columns": ["id", "categoria", "data", "autor"],

    # enriquecimento NLP
    "nlp": {
        "enabled":  True,
        "ner":      True,      # spaCy NER — requer: pip install spacy
        "classify": True,      # classificação de tipo de documento
    },

    # limpeza — operações individuais
    "limpeza": {
        "encoding":        True,
        "headers_footers": True,
        "hifenacao":       True,
        "espacos":         True,
        "artefatos":       True,
        "normalizacao":    True,
        "header_threshold": 0.70,  # % de páginas para considerar header
    },

    # tipos de arquivo por extensão
    "per_type": {
        "pdf":      "recursive",
        "markdown": "markdown",
        "csv":      "recursive",
        "py":       "code",
    },
}

LIMITS = {
    "max_file_size_mb":  100,
    "max_chunks_per_doc": 10000,
    "strip_pii":          False,  # True remove CPF, emails, telefones
}
```

---

## 14. Referências

- **PyMuPDF (fitz):** extração de texto nativo, metadados XMP, layout — fitz.readthedocs.io
- **Docling (IBM):** parser estruturado com OCR, tabelas e ordem de leitura — github.com/docling-project/docling
- **docling-core:** tipos DoclingDocument e serialização JSON — github.com/docling-project/docling-core
- **pdfplumber:** extração de tabelas e texto com layout — github.com/jsvine/pdfplumber
- **python-docx:** leitura de arquivos DOCX — python-docx.readthedocs.io
- **BeautifulSoup4:** parsing de HTML — crummy.com/software/BeautifulSoup/
- **spaCy:** NER multilíngue — spacy.io
- **langdetect:** detecção de idioma — github.com/Mimino666/langdetect
- **FastEmbed (SPLADE):** embedding esparso local — github.com/qdrant/fastembed
- **Tesseract:** OCR (opcional) — github.com/tesseract-ocr/tesseract
