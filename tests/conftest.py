import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool
from starlette.testclient import TestClient

from src.db.models import Base
from src.db.session import get_db
from src.main import app


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


@pytest.fixture
def client(db_sessionmaker):
    async def override_get_db():
        async with db_sessionmaker() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
