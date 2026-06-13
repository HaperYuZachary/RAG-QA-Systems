from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


def test_health_endpoint_returns_ok_with_explicit_test_settings(monkeypatch):
    monkeypatch.setenv("API_V1_PREFIX", "/ci-prefix")
    app = create_app(
        Settings(
            app_name="Test RAG",
            api_v1_prefix="/api/v1",
            frontend_origin="http://testserver",
        )
    )
    client = TestClient(app)

    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert client.get("/ci-prefix/health").status_code == 404
