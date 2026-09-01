"""
Fluxo:
    load PDF -> chunks -> metadados+ids -> embeddings (denso+esparso) -> Qdrant

Requisitos:
    pip install docling "docling-core[chunking]" qdrant-client fastembed litellm transformers
"""

import hashlib
from pathlib import Path
from uuid import uuid5, NAMESPACE_DNS
from datetime import datetime, timezone

from docling.document_converter import DocumentConverter
from docling_core.types.doc.document import DoclingDocument
from docling_core.transforms.chunker.hybrid_chunker import HybridChunker
from docling_core.transforms.chunker.hierarchical_chunker import (
    ChunkingDocSerializer,
    ChunkingSerializerProvider,
)
from docling_core.transforms.serializer.markdown import MarkdownTableSerializer

from litellm import embedding
from fastembed import SparseTextEmbedding
from qdrant_client import QdrantClient
from qdrant_client.models import (
    PointStruct, SparseVector, VectorParams, Distance, SparseVectorParams, models,
)


# ══════════════════════════════════════════════════════════════════════
#  CONFIG
# ══════════════════════════════════════════════════════════════════════
QDRANT_URL    = "http://localhost:6333"
COLECAO       = "papers"
DENSE_MODEL   = "ollama/bge-m3"
DENSE_API     = "http://localhost:11434"
DENSE_DIM     = 1024
SPARSE_MODEL  = "prithivida/Splade_PP_en_v1"


# tabela vira markdown limpo em vez da notação de tripletos
class MDTableSerializerProvider(ChunkingSerializerProvider):
    def get_serializer(self, doc):
        return ChunkingDocSerializer(doc=doc, table_serializer=MarkdownTableSerializer())


# ══════════════════════════════════════════════════════════════════════
#  1) LOAD — PDF vira DoclingDocument
# ══════════════════════════════════════════════════════════════════════
def load_pdf_to_document(file: str) -> DoclingDocument:
    path = Path(file)
    if not path.is_file():
        raise FileNotFoundError(f"Arquivo não encontrado: {path.resolve()}")
    converter = DocumentConverter()
    result = converter.convert(path)
    return result.document


def doc_id_do_arquivo(file: str) -> str:
    """SHA-256 do conteúdo do arquivo — identifica o documento de forma estável."""
    conteudo = Path(file).read_bytes()
    return hashlib.sha256(conteudo).hexdigest()


# ══════════════════════════════════════════════════════════════════════
#  2) CHUNK — HybridChunker
# ══════════════════════════════════════════════════════════════════════
def fazer_chunks(doc: DoclingDocument, max_tokens: int = 512):
    chunker = HybridChunker(
        max_tokens=max_tokens,
        merge_peers=True,
        serializer_provider=MDTableSerializerProvider(),
    )
    chunks = list(chunker.chunk(dl_doc=doc))
    return chunker, chunks


# ══════════════════════════════════════════════════════════════════════
#  3) METADADOS + IDS — monta o registro de cada chunk
# ══════════════════════════════════════════════════════════════════════
def construir_registros(chunker, chunks, *, filename, doc_id):
    """
    Devolve uma lista de dicts, cada um com:
        texto (contextualizado), id, e todos os metadados.
    Tudo pronto para virar payload no Qdrant, sem conversões intermediárias.
    """
    agora = datetime.now(timezone.utc).isoformat()
    registros = []

    for i, c in enumerate(chunks):
        texto = chunker.contextualize(chunk=c)

        # seção (headings)
        headings = getattr(c.meta, "headings", None)
        secao = " > ".join(headings) if headings else None

        # todas as páginas que o chunk toca
        paginas = sorted({
            prov.page_no
            for it in c.meta.doc_items
            for prov in getattr(it, "prov", [])
        })

        # chunk_id determinístico: doc_id + índice → reindexar não duplica
        chunk_id = str(uuid5(NAMESPACE_DNS, f"{doc_id}:{i}"))

        payload = {
            "page_content": texto,
            "filename": filename,
            "doc_id": doc_id,
            "chunk_id": chunk_id,
            "chunk_index": i,
            "headings": secao,
            "page_no": paginas[0] if paginas else None,
            "pages": paginas,
            "embedding_model_denso": DENSE_MODEL,
            "embedding_dimension_denso": DENSE_DIM,
            "sparse_model": SPARSE_MODEL,
            "indexed_at": agora,
        }
        payload = {k: v for k, v in payload.items() if v is not None}

        registros.append({"id": chunk_id, "texto": texto, "payload": payload})

    return registros


# ══════════════════════════════════════════════════════════════════════
#  4) EMBEDDINGS — denso (LiteLLM) + esparso (SPLADE), na mão
# ══════════════════════════════════════════════════════════════════════
def gerar_embeddings(textos):
    # denso via LiteLLM
    resp = embedding(model=DENSE_MODEL, input=textos, api_base=DENSE_API)
    densos = [item["embedding"] for item in resp["data"]]

    # esparso via SPLADE (FastEmbed)
    sparse_model = SparseTextEmbedding(model_name=SPARSE_MODEL)
    esparsos = list(sparse_model.embed(textos))

    return densos, esparsos


# ══════════════════════════════════════════════════════════════════════
#  5) INDEXAR — monta pontos com ambos os vetores e faz upsert
# ══════════════════════════════════════════════════════════════════════
def garantir_colecao(client):
    if client.collection_exists(COLECAO):
        return
    client.create_collection(
        collection_name=COLECAO,
        vectors_config={"dense": VectorParams(size=DENSE_DIM, distance=Distance.COSINE)},
        sparse_vectors_config={
            "sparse": SparseVectorParams(index=models.SparseIndexParams(on_disk=False))
        },
    )


def indexar(client, registros, densos, esparsos):
    pontos = []
    for i, reg in enumerate(registros):
        pontos.append(PointStruct(
            id=reg["id"],
            vector={
                "dense": densos[i],
                "sparse": SparseVector(
                    indices=esparsos[i].indices.tolist(),
                    values=esparsos[i].values.tolist(),
                ),
            },
            payload=reg["payload"],
        ))
    client.upsert(collection_name=COLECAO, points=pontos, wait=True)
    return len(pontos)


# ══════════════════════════════════════════════════════════════════════
#  ORQUESTRADOR — encadeia tudo, um atrás do outro
# ══════════════════════════════════════════════════════════════════════
def ingerir(file: str):
    filename = Path(file).name

    # 1) load
    print(f"[1/5] Load: {filename}")
    doc = load_pdf_to_document(file)
    doc_id = doc_id_do_arquivo(file)

    # 2) chunk
    print("[2/5] Chunking...")
    chunker, chunks = fazer_chunks(doc)
    print(f"      {len(chunks)} chunks")

    # 3) metadados + ids
    print("[3/5] Montando registros + metadados...")
    registros = construir_registros(chunker, chunks, filename=filename, doc_id=doc_id)

    # 4) embeddings
    print("[4/5] Gerando embeddings (denso + esparso)...")
    textos = [r["texto"] for r in registros]
    densos, esparsos = gerar_embeddings(textos)

    # 5) indexar
    print("[5/5] Indexando no Qdrant...")
    client = QdrantClient(url=QDRANT_URL)
    garantir_colecao(client)
    n = indexar(client, registros, densos, esparsos)
    print(f"✓ {n} chunks indexados na coleção '{COLECAO}'.")

    return doc_id


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Uso: python pipeline_ingestao.py caminho/do/arquivo.pdf")
        sys.exit(1)
    ingerir(sys.argv[1])