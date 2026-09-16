from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.api.routes import health
from src.config import get_settings
from src.db.session import create_engine_and_sessionmaker
from src.errors import register_exception_handlers


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    engine, sessionmaker = create_engine_and_sessionmaker(settings.database_url)
    app.state.engine = engine
    app.state.sessionmaker = sessionmaker

    yield

    await engine.dispose()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, debug=settings.debug, lifespan=lifespan)

    register_exception_handlers(app)
    app.include_router(health.router)

    return app


app = create_app()
