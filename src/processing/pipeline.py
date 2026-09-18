import logging
import uuid
from collections.abc import Callable
from typing import Any

from fastapi import Request

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from starlette.concurrency import run_in_threadpool

from src.db.models import File
from src.domain.file_state import FileStatus
from src.files.repository import FileRepository
from src.rag.chunking import chunk_document
from src.rag.indexing import Indexer
from src.storage.local import LocalStorage

logger = logging.getLogger("buscaai.processing")


class ProcessingPipeline:
    """PDF → extração → representação estruturada → chunking → embedding →
    indexação (PRD §9).

    Não há retomada nem retry: o disparo é único, logo após o upload. Se o
    processo morrer no meio, o arquivo fica em `processing` até alguém
    reprocessar."""

    def __init__(
        self,
        sessionmaker: async_sessionmaker[AsyncSession],
        storage: LocalStorage,
        indexer: Indexer,
        converter_factory: Callable[[], Any],
        chunker_factory: Callable[[], Any],
    ):
        self.sessionmaker = sessionmaker
        self.storage = storage
        self.indexer = indexer
        # Construir o conversor e o chunker do Docling custa ~1s e carrega
        # tokenizer; só vale a pena quando há de fato um arquivo para processar.
        self._converter_factory = converter_factory
        self._chunker_factory = chunker_factory
        self._converter: Any = None
        self._chunker: Any = None

    @property
    def converter(self) -> Any:
        if self._converter is None:
            self._converter = self._converter_factory()
        return self._converter

    @property
    def chunker(self) -> Any:
        if self._chunker is None:
            self._chunker = self._chunker_factory()
        return self._chunker

    async def process(self, file_id: uuid.UUID) -> None:
        async with self.sessionmaker() as session:
            repository = FileRepository(session)
            file = await repository.get_for_processing(file_id)

            if file is None or file.status != FileStatus.pending:
                logger.warning("Arquivo %s não está pendente de processamento", file_id)
                return

            await repository.mark_processing(file)
            await session.commit()

            try:
                await self._run(repository, session, file)
            except Exception as exc:
                logger.exception("Falha ao processar arquivo %s", file_id)
                await repository.mark_failed(
                    file, error_code="processing_failed", error_message=f"{type(exc).__name__}: {exc}"
                )
                await session.commit()

    async def _run(self, repository: FileRepository, session: AsyncSession, file: File) -> None:
        await repository.mark_stage(file, "extracting", 10)
        await session.commit()

        data = await run_in_threadpool(self.storage.read, file.source_key)
        document = await run_in_threadpool(self._extract, data, file.original_name)

        storage_key = f"{file.source_key.removesuffix('.pdf')}.docling.json"
        await run_in_threadpool(self.storage.save, storage_key, self._serialize(document))

        await repository.mark_stage(file, "chunking", 40)
        await session.commit()

        chunks = await run_in_threadpool(chunk_document, document, file.id, self.chunker)

        if not chunks:
            # PDF sem texto extraível: não é falha, é um estado próprio (PRD §9).
            await repository.mark_empty(file, storage_key=storage_key)
            await session.commit()
            return

        await repository.mark_stage(file, "embedding", 60)
        await session.commit()

        embeddings = await self.indexer.embed_chunks(chunks)

        await repository.mark_stage(file, "indexing", 80)
        await session.commit()

        indexed = await self.indexer.index_chunks(
            user_id=file.user_id,
            notebook_id=file.notebook_id,
            file_id=file.id,
            file_name=file.original_name,
            chunks=chunks,
            embeddings=embeddings,
        )

        await repository.mark_ready(file, chunk_count=indexed, storage_key=storage_key)
        await session.commit()

    def _extract(self, data: bytes, name: str) -> Any:
        import io

        from docling_core.types.io import DocumentStream

        result = self.converter.convert(DocumentStream(name=name, stream=io.BytesIO(data)))
        return result.document

    def _serialize(self, document: Any) -> bytes:
        return document.model_dump_json().encode("utf-8")


def get_pipeline(request: Request) -> ProcessingPipeline:
    return request.app.state.pipeline
