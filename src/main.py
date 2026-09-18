from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI

from src.api.routes import auth, files, health, notebooks
from src.config import get_settings
from src.db.session import create_engine_and_sessionmaker
from src.errors import register_exception_handlers
from src.storage.local import LocalStorage


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    engine, sessionmaker = create_engine_and_sessionmaker(settings.database_url)
    app.state.engine = engine
    app.state.sessionmaker = sessionmaker
    app.state.storage = LocalStorage(Path(settings.storage_dir))

    yield

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
