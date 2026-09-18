from contextlib import asynccontextmanager
from pathlib import Path

from elasticsearch import AsyncElasticsearch
from fastapi import FastAPI

from src.api.routes import auth, files, health, notebooks
from src.config import Settings, get_settings
from src.db.session import create_engine_and_sessionmaker
from src.errors import register_exception_handlers
from src.processing.pipeline import ProcessingPipeline
from src.rag.embeddings import Embedder
from src.rag.indexing import Indexer
from src.storage.local import LocalStorage


def _docling_converter():
    from docling.document_converter import DocumentConverter

    return DocumentConverter()


def _docling_chunker():
    from docling.chunking import HybridChunker

    return HybridChunker()


def create_elasticsearch(settings: Settings) -> AsyncElasticsearch:
    basic_auth = (
        (settings.elasticsearch_user, settings.elasticsearch_password)
        if settings.elasticsearch_user
        else None
    )
    return AsyncElasticsearch(hosts=[settings.elasticsearch_url], basic_auth=basic_auth)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    engine, sessionmaker = create_engine_and_sessionmaker(settings.database_url)
    storage = LocalStorage(Path(settings.storage_dir))
    elasticsearch = create_elasticsearch(settings)
    embedder = Embedder(settings.embedding_model, settings.embedding_batch_size)
    indexer = Indexer(elasticsearch, embedder, settings.elasticsearch_index, settings.embedding_dimensions)

    app.state.engine = engine
    app.state.sessionmaker = sessionmaker
    app.state.storage = storage
    app.state.elasticsearch = elasticsearch
    app.state.indexer = indexer
    app.state.pipeline = ProcessingPipeline(
        sessionmaker=sessionmaker,
        storage=storage,
        indexer=indexer,
        converter_factory=_docling_converter,
        chunker_factory=_docling_chunker,
    )

    yield

    await elasticsearch.close()
    await engine.dispose()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, debug=settings.debug, lifespan=lifespan)

    register_exception_handlers(app)
    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(notebooks.router)
    app.include_router(files.router)

    return app


app = create_app()
