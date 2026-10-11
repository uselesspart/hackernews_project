"""
FastAPI-приложение. Запуск для разработки:

    HN_DB_URL=sqlite:///D:/hackernews_data/run_small/hn.db uvicorn api.main:app --reload
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import sessionmaker

from api.config import Settings
from api.routers import meta, techs
from db.session import get_engine, upgrade_schema


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        engine = get_engine(settings.db_url)
        # Досоздаёт таблицы предрасчёта, если precompute ещё не запускался: API вернёт пустые метрики
        upgrade_schema(engine)
        app.state.sessionmaker = sessionmaker(bind=engine, expire_on_commit=False)
        yield
        engine.dispose()

    app = FastAPI(title="Hacker News Tech Analytics", version="0.1.0", lifespan=lifespan)
    app.state.settings = settings
    app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_methods=["GET"],
                       allow_headers=["*"])
    app.include_router(meta.router)
    app.include_router(techs.router)
    return app


app = create_app()
