import uuid
from types import SimpleNamespace

import pytest

from src.db.models import File
from src.domain.file_state import FileStatus
from src.files.repository import FileRepository
from src.notebooks.repository import NotebookRepository
from src.processing.pipeline import ProcessingPipeline
from src.storage.local import LocalStorage, source_key_for
from src.users.repository import UserRepository
from tests.conftest import FakeIndexer


class FakeDocument:
    def model_dump_json(self) -> str:
        return '{"documento": "estruturado"}'


class FakeConverter:
    def __init__(self, error: Exception | None = None):
        self.error = error

    def convert(self, source):
        if self.error is not None:
            raise self.error
        return SimpleNamespace(document=FakeDocument())


class FakeChunker:
    def __init__(self, texts: list[str]):
        self.texts = texts

    def chunk(self, document):
        for text in self.texts:
            yield SimpleNamespace(
                text=text,
                meta=SimpleNamespace(doc_items=[SimpleNamespace(prov=[SimpleNamespace(page_no=1)])], headings=None),
            )

    def contextualize(self, chunk):
        return chunk.text


@pytest.fixture
def storage(tmp_path):
    return LocalStorage(tmp_path / "storage")


async def _pending_file(db_sessionmaker, storage) -> File:
    async with db_sessionmaker() as session:
        user = await UserRepository(session).create(email="dono@example.com", name="Dono")
        notebook = await NotebookRepository(session).create(user_id=user.id, name="Notebook")
        file_id = uuid.uuid4()
        source_key = source_key_for(user.id, notebook.id, file_id)
        file = await FileRepository(session).create(
            file_id=file_id,
            user_id=user.id,
            notebook_id=notebook.id,
            original_name="manual.pdf",
            mime_type="application/pdf",
            size_bytes=10,
            checksum_sha256="a" * 64,
            page_count=2,
            source_key=source_key,
        )
        await session.commit()

    storage.save(source_key, b"%PDF-1.7 conteudo")
    return file


def _pipeline(db_sessionmaker, storage, indexer, *, converter=None, texts=None):
    return ProcessingPipeline(
        sessionmaker=db_sessionmaker,
        storage=storage,
        indexer=indexer,
        converter_factory=lambda: converter or FakeConverter(),
        chunker_factory=lambda: FakeChunker(texts if texts is not None else ["trecho um", "trecho dois"]),
    )


async def _reload(db_sessionmaker, file_id) -> File:
    async with db_sessionmaker() as session:
        return await FileRepository(session).get_for_processing(file_id)


async def test_processing_indexes_chunks_and_marks_ready(db_sessionmaker, storage):
    file = await _pending_file(db_sessionmaker, storage)
    indexer = FakeIndexer()

    await _pipeline(db_sessionmaker, storage, indexer).process(file.id)

    processed = await _reload(db_sessionmaker, file.id)
    assert processed.status == FileStatus.ready
    assert processed.chunk_count == 2
    assert processed.progress == 100
    assert processed.stage is None
    assert processed.indexed_at is not None
    assert processed.storage_key.endswith(".docling.json")
    assert storage.read(processed.storage_key) == b'{"documento": "estruturado"}'


async def test_indexed_chunks_carry_owner_and_notebook(db_sessionmaker, storage):
    file = await _pending_file(db_sessionmaker, storage)
    indexer = FakeIndexer()

    await _pipeline(db_sessionmaker, storage, indexer).process(file.id)

    indexed = indexer.indexed[0]
    assert indexed["user_id"] == file.user_id
    assert indexed["notebook_id"] == file.notebook_id
    assert indexed["file_id"] == file.id
    assert indexed["file_name"] == "manual.pdf"
    assert [chunk.text for chunk in indexed["chunks"]] == ["trecho um", "trecho dois"]


async def test_pdf_without_text_becomes_empty(db_sessionmaker, storage):
    file = await _pending_file(db_sessionmaker, storage)
    indexer = FakeIndexer()

    await _pipeline(db_sessionmaker, storage, indexer, texts=[]).process(file.id)

    processed = await _reload(db_sessionmaker, file.id)
    assert processed.status == FileStatus.empty
    assert processed.chunk_count == 0
    assert processed.storage_key is not None
    assert indexer.indexed == []


async def test_extraction_error_marks_file_failed(db_sessionmaker, storage):
    file = await _pending_file(db_sessionmaker, storage)
    converter = FakeConverter(error=RuntimeError("pdfium quebrou"))

    await _pipeline(db_sessionmaker, storage, FakeIndexer(), converter=converter).process(file.id)

    processed = await _reload(db_sessionmaker, file.id)
    assert processed.status == FileStatus.failed
    assert processed.error_code == "processing_failed"
    assert "pdfium quebrou" in processed.error_message
    assert processed.stage is None


async def test_file_that_is_not_pending_is_ignored(db_sessionmaker, storage):
    file = await _pending_file(db_sessionmaker, storage)
    async with db_sessionmaker() as session:
        repository = FileRepository(session)
        stored = await repository.get_for_processing(file.id)
        await repository.mark_processing(stored)
        await session.commit()

    indexer = FakeIndexer()
    await _pipeline(db_sessionmaker, storage, indexer).process(file.id)

    assert indexer.indexed == []


async def test_unknown_file_is_ignored(db_sessionmaker, storage):
    indexer = FakeIndexer()

    await _pipeline(db_sessionmaker, storage, indexer).process(uuid.uuid4())

    assert indexer.indexed == []
