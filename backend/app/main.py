from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import chat, debug, documents, kb
from app.config import Settings, settings
from app.db.sqlite_client import init_db


def create_app(app_settings: Settings | None = None) -> FastAPI:
    active_settings = app_settings or settings
    init_db(active_settings)

    app = FastAPI(title=active_settings.app_name, version="1.0.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[active_settings.frontend_origin],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get(f"{active_settings.api_v1_prefix}/health")
    def health():
        return {"status": "ok"}

    app.include_router(kb.router, prefix=active_settings.api_v1_prefix)
    app.include_router(documents.router, prefix=active_settings.api_v1_prefix)
    app.include_router(chat.router, prefix=active_settings.api_v1_prefix)
    app.include_router(debug.router, prefix=active_settings.api_v1_prefix)

    return app


app = create_app()
