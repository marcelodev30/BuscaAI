import uuid

from src.rag import indexing as indexing_module
from src.rag.chunking import Chunk
from src.rag.indexing import Indexer


class FakeIndices:
    def __init__(self):
        self.existing: set[str] = set()
        self.created: list = []

    async def exists(self, index):
        return index in self.existing

    async def create(self, index, mappings):
        self.existing.add(index)
        self.created.append((index, mappings))


class FakeElasticsearch:
    def __init__(self):
        self.indices = FakeIndices()
        self.deleted: list = []

    async def delete_by_query(self, **kwargs):
        self.deleted.append(kwargs)


class FakeEmbedder:
    def embed(self, texts):
        return [[float(len(text))] * 3 for text in texts]


def _indexer(elasticsearch=None):
    return Indexer(elasticsearch or FakeElasticsearch(), FakeEmbedder(), "chunks-teste", dimensions=1024)


def _chunk(index: int, page: int | None = 3) -> Chunk:
    return Chunk(
        chunk_id=f"file:{index}",
        index=index,
        text=f"texto {index}",
        embed_text=f"contexto {index}",
        page=page,
        section="Seção A",
    )


async def test_ensure_index_creates_mapping_with_model_dimensions():
    elasticsearch = FakeElasticsearch()

    await _indexer(elasticsearch).ensure_index()

    index, mappings = elasticsearch.indices.created[0]
    assert index == "chunks-teste"
    embedding = mappings["properties"]["embedding"]
    assert embedding["dims"] == 1024
    assert embedding["similarity"] == "cosine"


async def test_ensure_index_does_not_recreate_existing_index():
    elasticsearch = FakeElasticsearch()
    elasticsearch.indices.existing.add("chunks-teste")

    await _indexer(elasticsearch).ensure_index()

    assert elasticsearch.indices.created == []


async def test_index_chunks_sends_ownership_metadata(monkeypatch):
    captured: list = []

    async def fake_bulk(client, actions, **kwargs):
        captured.extend(actions)
        return len(captured), []

    monkeypatch.setattr(indexing_module, "async_bulk", fake_bulk)

    user_id, notebook_id, file_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    indexer = _indexer()
    chunks = [_chunk(0), _chunk(1)]
    embeddings = await indexer.embed_chunks(chunks)

    indexed = await indexer.index_chunks(
        user_id=user_id,
        notebook_id=notebook_id,
        file_id=file_id,
        file_name="manual.pdf",
        chunks=chunks,
        embeddings=embeddings,
    )

    assert indexed == 2
    source = captured[0]["_source"]
    assert source["user_id"] == str(user_id)
    assert source["notebook_id"] == str(notebook_id)
    assert source["file_id"] == str(file_id)
    assert source["page"] == 3
    assert source["section"] == "Seção A"
    assert source["text"] == "texto 0"
    assert source["embedding"] == embeddings[0]
    # o _id é o chunk_id, então reprocessar sobrescreve em vez de duplicar
    assert captured[0]["_id"] == "file:0"


async def test_index_chunks_without_chunks_does_nothing(monkeypatch):
    async def fail_bulk(*args, **kwargs):
        raise AssertionError("não deveria chamar o bulk")

    monkeypatch.setattr(indexing_module, "async_bulk", fail_bulk)

    assert (
        await _indexer().index_chunks(
            user_id=uuid.uuid4(),
            notebook_id=uuid.uuid4(),
            file_id=uuid.uuid4(),
            file_name="vazio.pdf",
            chunks=[],
            embeddings=[],
        )
        == 0
    )


async def test_delete_by_notebook_filters_by_notebook():
    elasticsearch = FakeElasticsearch()
    notebook_id = uuid.uuid4()

    await _indexer(elasticsearch).delete_by_notebook(notebook_id)

    assert elasticsearch.deleted[0]["query"] == {"term": {"notebook_id": str(notebook_id)}}
