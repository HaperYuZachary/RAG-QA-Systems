from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.documents import get_document_service, router
from app.services.document_service import (
    DocumentNotFoundError,
    DocumentRecord,
    IngestResult,
    IngestStatus,
)


def make_doc(doc_id="doc_1"):
    return DocumentRecord(
        id=doc_id,
        kb_id="kb_1",
        filename=f"{doc_id}.md",
        file_type="md",
        file_size=100,
        file_hash="hash",
        chunk_count=3,
        status="ready",
        error_msg=None,
        created_at="2026-06-11T00:00:00",
    )


class FakeDocumentService:
    def __init__(self, raise_not_found=False, ingest_raises=False):
        self.calls = []
        self.raise_not_found = raise_not_found
        self.ingest_raises = ingest_raises

    def ingest_document(self, source_path, kb_id, original_filename=None):
        self.calls.append(("ingest", kb_id, original_filename))
        if self.ingest_raises:
            raise ValueError("boom")
        return IngestResult(
            document_id="doc_1",
            status=IngestStatus.READY,
            chunk_count=5,
            duplicate=False,
        )

    def list_documents(self, kb_id):
        self.calls.append(("list", kb_id))
        return [make_doc()]

    def get_document(self, document_id):
        self.calls.append(("get", document_id))
        if self.raise_not_found:
            raise DocumentNotFoundError(document_id)
        return make_doc(document_id)

    def delete_document(self, document_id):
        self.calls.append(("delete", document_id))
        if self.raise_not_found:
            raise DocumentNotFoundError(document_id)
        return make_doc(document_id)


def create_test_client(fake_service):
    # docs_url=None 关闭 Swagger，避免其默认 /docs 路由与本路由的 /docs 端点在
    # 未加前缀的测试应用里冲突（真实应用走 /api/v1/docs 前缀，无此问题）
    app = FastAPI(docs_url=None, redoc_url=None)
    app.include_router(router)
    app.dependency_overrides[get_document_service] = lambda: fake_service
    return TestClient(app)


def test_upload_ingests_each_file_and_returns_results():
    fake = FakeDocumentService()
    client = create_test_client(fake)

    response = client.post(
        "/upload",
        data={"kb_id": "kb_1"},
        files=[("files", ("hr.md", b"# HR policy content", "text/markdown"))],
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["documents"] == [
        {
            "document_id": "doc_1",
            "filename": "hr.md",
            "status": "ready",
            "chunk_count": 5,
            "duplicate": False,
            "error_msg": None,
        }
    ]
    assert fake.calls == [("ingest", "kb_1", "hr.md")]


def test_upload_reports_per_file_error_without_failing_request():
    fake = FakeDocumentService(ingest_raises=True)
    client = create_test_client(fake)

    response = client.post(
        "/upload",
        data={"kb_id": "kb_1"},
        files=[("files", ("bad.md", b"x", "text/markdown"))],
    )

    assert response.status_code == 201
    item = response.json()["documents"][0]
    assert item["status"] == "error"
    assert "boom" in item["error_msg"]


def test_list_documents_returns_records_for_kb():
    fake = FakeDocumentService()
    client = create_test_client(fake)

    response = client.get("/docs", params={"kb_id": "kb_1"})

    assert response.status_code == 200
    assert response.json()[0]["id"] == "doc_1"
    assert "file_hash" not in response.json()[0]  # 不对外暴露哈希
    assert fake.calls == [("list", "kb_1")]


def test_get_document_status_returns_subset():
    fake = FakeDocumentService()
    client = create_test_client(fake)

    response = client.get("/docs/doc_1/status")

    assert response.status_code == 200
    assert response.json() == {
        "id": "doc_1",
        "status": "ready",
        "chunk_count": 3,
        "error_msg": None,
    }


def test_delete_document_returns_record():
    fake = FakeDocumentService()
    client = create_test_client(fake)

    response = client.delete("/docs/doc_1")

    assert response.status_code == 200
    assert response.json()["id"] == "doc_1"
    assert fake.calls == [("delete", "doc_1")]


def test_missing_document_maps_to_404():
    fake = FakeDocumentService(raise_not_found=True)
    client = create_test_client(fake)

    assert client.get("/docs/ghost").status_code == 404
    assert client.get("/docs/ghost/status").status_code == 404
    assert client.delete("/docs/ghost").status_code == 404
