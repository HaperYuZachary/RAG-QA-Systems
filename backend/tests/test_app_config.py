from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


def test_app_uses_configured_title_api_prefix_and_cors_origin():
    settings = Settings(
        app_name="Configured RAG",
        api_v1_prefix="/custom",
        frontend_origin="http://example.test",
    )
    app = create_app(settings)
    client = TestClient(app)

    assert app.title == "Configured RAG"
    assert client.get("/custom/health").json() == {"status": "ok"}
    assert client.get("/api/v1/health").status_code == 404

    response = client.options(
        "/custom/health",
        headers={
            "Origin": "http://example.test",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.headers["access-control-allow-origin"] == "http://example.test"
