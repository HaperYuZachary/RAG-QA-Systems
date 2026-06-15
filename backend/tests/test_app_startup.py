from fastapi.testclient import TestClient

from app.api import chat as chat_module
from app.config import Settings
from app.db.sqlite_client import get_db_path
from app.main import create_app


def test_create_app_initializes_sqlite_database(tmp_path):
    settings = Settings(data_dir=str(tmp_path))

    create_app(settings)

    assert get_db_path(settings).exists()


def test_api_routes_are_mounted_without_touching_heavy_services(tmp_path, monkeypatch):
    monkeypatch.setattr(chat_module, "_chat_service", None)
    app = create_app(Settings(data_dir=str(tmp_path)))
    paths = {route.path for route in app.routes}

    assert {
        "/api/v1/health",
        "/api/v1/knowledge-bases",
        "/api/v1/upload",
        "/api/v1/docs",
        "/api/v1/chat",
        "/api/v1/chat/conversations",
        "/api/v1/debug/search",
    } <= paths

    # Health is deliberately lightweight; /chat and /debug/search are only
    # checked via route registration so this smoke test does not build Chroma.
    client = TestClient(app)
    assert client.get("/api/v1/health").status_code == 200
    assert chat_module._chat_service is None
