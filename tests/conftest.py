import io

import pypdfium2 as pdfium
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool
from starlette.testclient import TestClient

from src.auth.jwt import create_access_token
from src.config import get_settings
from src.db.models import Base, User
from src.db.session import get_db
from src.main import app
from src.processing.pipeline import get_pipeline
from src.rag.indexing import get_indexer
from src.storage.local import LocalStorage, get_storage
from src.users.repository import UserRepository


class FakeIndexer:
    """Substitui o Elasticsearch nos testes de rota."""

    def __init__(self):
        self.deleted_notebooks: list = []
        self.indexed: list = []

    async def embed_chunks(self, chunks):
        return [[0.1, 0.2, 0.3] for _ in chunks]

    async def index_chunks(self, **kwargs):
        self.indexed.append(kwargs)
        return len(kwargs["chunks"])

    async def delete_by_notebook(self, notebook_id):
        self.deleted_notebooks.append(notebook_id)


class FakePipeline:
    """Registra o disparo do processamento sem executar Docling."""

    def __init__(self):
        self.processed: list = []

    async def process(self, file_id):
        self.processed.append(file_id)


@pytest_asyncio.fixture
async def db_sessionmaker():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield async_sessionmaker(bind=engine, expire_on_commit=False)

    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_sessionmaker):
    async with db_sessionmaker() as session:
        yield session


@pytest.fixture
def storage_dir(tmp_path):
    return tmp_path / "storage"


@pytest.fixture
def fake_indexer():
    return FakeIndexer()


@pytest.fixture
def fake_pipeline():
    return FakePipeline()


@pytest.fixture
def client(db_sessionmaker, storage_dir, fake_indexer, fake_pipeline):
    async def override_get_db():
        async with db_sessionmaker() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_storage] = lambda: LocalStorage(storage_dir)
    app.dependency_overrides[get_indexer] = lambda: fake_indexer
    app.dependency_overrides[get_pipeline] = lambda: fake_pipeline
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def pdf_bytes():
    """PDF válido gerado em memória. Não é determinístico entre chamadas, então
    testes de deduplicação devem reenviar os mesmos bytes."""

    def _make(pages: int = 1, width: int = 595) -> bytes:
        document = pdfium.PdfDocument.new()
        for _ in range(pages):
            document.new_page(width, 842)
        buffer = io.BytesIO()
        document.save(buffer)
        return buffer.getvalue()

    return _make


@pytest_asyncio.fixture
async def user_factory(db_sessionmaker):
    async def _create(*, email: str = "dono@example.com", name: str = "Dono", plan: str = "free") -> User:
        async with db_sessionmaker() as session:
            user = await UserRepository(session).create(email=email, name=name)
            user.plan = plan
            await session.commit()
            return user

    return _create


@pytest.fixture
def auth_headers():
    def _headers(user: User) -> dict[str, str]:
        settings = get_settings()
        token = create_access_token(
            user.id, secret=settings.jwt_secret, algorithm=settings.jwt_algorithm, expires_minutes=5
        )
        return {"Authorization": f"Bearer {token}"}

    return _headers
