import uuid
from types import SimpleNamespace

from src.rag.chunking import chunk_document


def _raw_chunk(text: str, page: int | None = None, headings: list[str] | None = None):
    provenance = [SimpleNamespace(page_no=page)] if page is not None else []
    return SimpleNamespace(
        text=text,
        meta=SimpleNamespace(doc_items=[SimpleNamespace(prov=provenance)], headings=headings),
    )


class StubChunker:
    def __init__(self, chunks):
        self._chunks = chunks

    def chunk(self, document):
        return iter(self._chunks)

    def contextualize(self, chunk):
        return f"contexto: {chunk.text}"


def test_chunk_ids_are_derived_from_file_and_index():
    file_id = uuid.uuid4()
    chunker = StubChunker([_raw_chunk("primeiro"), _raw_chunk("segundo")])

    chunks = chunk_document(object(), file_id, chunker)

    assert [chunk.chunk_id for chunk in chunks] == [f"{file_id}:0", f"{file_id}:1"]


def test_chunking_is_deterministic():
    file_id = uuid.uuid4()
    document = object()

    first = chunk_document(document, file_id, StubChunker([_raw_chunk("a"), _raw_chunk("b")]))
    second = chunk_document(document, file_id, StubChunker([_raw_chunk("a"), _raw_chunk("b")]))

    assert [c.chunk_id for c in first] == [c.chunk_id for c in second]
    assert [c.text for c in first] == [c.text for c in second]


def test_extracts_page_and_section():
    chunker = StubChunker([_raw_chunk("conteudo", page=7, headings=["Capítulo 1", "Seção A"])])

    chunk = chunk_document(object(), uuid.uuid4(), chunker)[0]

    assert chunk.page == 7
    assert chunk.section == "Capítulo 1 > Seção A"


def test_page_and_section_are_optional():
    chunk = chunk_document(object(), uuid.uuid4(), StubChunker([_raw_chunk("sem metadados")]))[0]

    assert chunk.page is None
    assert chunk.section is None


def test_embed_text_carries_context_and_text_stays_raw():
    chunk = chunk_document(object(), uuid.uuid4(), StubChunker([_raw_chunk("texto puro")]))[0]

    assert chunk.text == "texto puro"
    assert chunk.embed_text == "contexto: texto puro"


def test_blank_chunks_are_skipped_without_shifting_ids():
    file_id = uuid.uuid4()
    chunker = StubChunker([_raw_chunk("   "), _raw_chunk("conteudo")])

    chunks = chunk_document(object(), file_id, chunker)

    assert len(chunks) == 1
    # o id segue o índice original do chunker, então continua estável mesmo
    # com chunks descartados no meio
    assert chunks[0].chunk_id == f"{file_id}:1"
