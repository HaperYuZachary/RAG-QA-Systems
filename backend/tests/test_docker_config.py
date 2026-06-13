from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / "backend"
FRONTEND_DIR = REPO_ROOT / "frontend"
COMPOSE_FILE = REPO_ROOT / "docker-compose.yml"


def test_backend_dockerfile_uses_slim_python_and_uvicorn_entrypoint():
    dockerfile = (BACKEND_DIR / "Dockerfile").read_text(encoding="utf-8")

    assert "FROM python:3.11-slim" in dockerfile
    assert "pip install --no-cache-dir -r requirements.txt" in dockerfile
    assert "COPY app ./app" in dockerfile
    assert "uvicorn" in dockerfile
    assert "app.main:app" in dockerfile
    assert "--host" in dockerfile
    assert "0.0.0.0" in dockerfile
    assert "--port" in dockerfile
    assert "8000" in dockerfile


def test_backend_dockerignore_excludes_local_env_data_and_caches():
    ignored = set(
        line.strip()
        for line in (BACKEND_DIR / ".dockerignore").read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    )

    assert ".venv/" in ignored
    assert "data/" in ignored
    assert "__pycache__/" in ignored
    assert ".env" in ignored


def test_frontend_dockerfile_builds_vite_dist_and_serves_with_nginx():
    dockerfile = (FRONTEND_DIR / "Dockerfile").read_text(encoding="utf-8")

    assert "FROM node:20-alpine AS build" in dockerfile
    assert "npm ci" in dockerfile
    assert "npm run build" in dockerfile
    assert "FROM nginx:alpine" in dockerfile
    assert "COPY --from=build /app/dist /usr/share/nginx/html" in dockerfile
    assert "COPY nginx.conf /etc/nginx/conf.d/default.conf" in dockerfile


def test_frontend_nginx_supports_spa_api_proxy_and_sse_streaming():
    nginx_conf = (FRONTEND_DIR / "nginx.conf").read_text(encoding="utf-8")

    assert "try_files $uri $uri/ /index.html;" in nginx_conf
    assert "location /api/" in nginx_conf
    assert "proxy_pass http://backend:8000;" in nginx_conf
    assert "proxy_buffering off;" in nginx_conf
    assert "proxy_read_timeout 3600s;" in nginx_conf


def test_frontend_dockerignore_excludes_host_build_artifacts():
    ignored = set(
        line.strip()
        for line in (FRONTEND_DIR / ".dockerignore").read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    )

    assert "node_modules" in ignored
    assert "dist" in ignored
    assert ".git" in ignored


def test_docker_compose_wires_backend_frontend_and_persistent_data():
    compose = yaml.safe_load(COMPOSE_FILE.read_text(encoding="utf-8"))
    services = compose["services"]

    backend = services["backend"]
    assert backend["build"] == "./backend"
    assert backend["env_file"] == ["./backend/.env"]
    assert backend["volumes"] == ["./backend/data:/app/data"]
    assert backend["expose"] == ["8000"]

    frontend = services["frontend"]
    assert frontend["build"] == "./frontend"
    assert frontend["depends_on"] == ["backend"]
    assert frontend["ports"] == ["8080:80"]
