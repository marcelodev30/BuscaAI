import uuid
from collections.abc import Sequence

from elasticsearch import AsyncElasticsearch
from elasticsearch.helpers import async_bulk
from fastapi import Request
from starlette.concurrency import run_in_threadpool

from src.rag.chunking import Chunk
from src.rag.embeddings import Embedder


class Indexer:
    """Todo acesso de escrita ao índice passa por aqui. Cada documento carrega
    user_id, notebook_id, file_id, chunk_id, página e seção — é o que permite
    filtrar por dono/notebook na busca e montar as citações no backend
    (CLAUDE.md §19 e §20)."""

    def __init__(
        self,
        elasticsearch: AsyncElasticsearch,
        embedder: Embedder,
        index_name: str,
        dimensions: int,
    ):
        self.elasticsearch = elasticsearch
        self.embedder = embedder
        self.index_name = index_name
        self.dimensions = dimensions
        self._index_ready = False

    async def ensure_index(self) -> None:
        if self._index_ready:
            return

        if not await self.elasticsearch.indices.exists(index=self.index_name):
            await self.elasticsearch.indices.create(
                index=self.index_name,
                mappings={
                    "properties": {
                        "user_id": {"type": "keyword"},
                        "notebook_id": {"type": "keyword"},
                        "file_id": {"type": "keyword"},
                        "chunk_id": {"type": "keyword"},
                        "chunk_index": {"type": "integer"},
                        "file_name": {"type": "keyword"},
                        "page": {"type": "integer"},
                        "section": {"type": "text"},
                        "text": {"type": "text"},
                        "embedding": {
                            "type": "dense_vector",
                            "dims": self.dimensions,
                            "index": True,
                            "similarity": "cosine",
                        },
                    }
                },
            )
        self._index_ready = True

    async def embed_chunks(self, chunks: Sequence[Chunk]) -> list[list[float]]:
        return await run_in_threadpool(self.embedder.embed, [chunk.embed_text for chunk in chunks])

    async def index_chunks(
        self,
        *,
        user_id: uuid.UUID,
        notebook_id: uuid.UUID,
        file_id: uuid.UUID,
        file_name: str,
        chunks: Sequence[Chunk],
        embeddings: Sequence[list[float]],
    ) -> int:
        if not chunks:
            return 0

        await self.ensure_index()

        actions = [
            {
                "_index": self.index_name,
                # O id do documento é o chunk_id, que é estável: reprocessar o
                # mesmo arquivo sobrescreve em vez de duplicar.
                "_id": chunk.chunk_id,
                "_source": {
                    "user_id": str(user_id),
                    "notebook_id": str(notebook_id),
                    "file_id": str(file_id),
                    "chunk_id": chunk.chunk_id,
                    "chunk_index": chunk.index,
                    "file_name": file_name,
                    "page": chunk.page,
                    "section": chunk.section,
                    "text": chunk.text,
                    "embedding": embedding,
                },
            }
            for chunk, embedding in zip(chunks, embeddings, strict=True)
        ]

        indexed, _ = await async_bulk(self.elasticsearch, actions, refresh=True)
        return indexed

    async def delete_by_notebook(self, notebook_id: uuid.UUID) -> None:
        await self.elasticsearch.delete_by_query(
            index=self.index_name,
            query={"term": {"notebook_id": str(notebook_id)}},
            ignore_unavailable=True,
            refresh=True,
        )


def get_indexer(request: Request) -> Indexer:
    return request.app.state.indexer
