from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.kb import get_kb_service, router
from app.services.kb_service import KnowledgeBase, KnowledgeBaseNotFoundError


def make_kb(kb_id="kb_1", name="HR 制度", description="", document_count=0):
    return KnowledgeBase(
        id=kb_id,
        name=name,
        description=description,
        created_at="2026-06-11T00:00:00",
        updated_at="2026-06-11T00:00:00",
        document_count=document_count,
    )


class FakeKBService:
    def __init__(self, raise_not_found=False):
        self.raise_not_found = raise_not_found
        self.calls = []

    def list(self):
        self.calls.append(("list",))
        return [make_kb(document_count=3)]

    def create(self, name, description=""):
        self.calls.append(("create", name, description))
        return make_kb(name=name, description=description)

    def update(self, kb_id, name=None, description=None):
        self.calls.append(("update", kb_id, name, description))
        if self.raise_not_found:
            raise KnowledgeBaseNotFoundError(kb_id)
        return make_kb(kb_id=kb_id, name=name or "HR 制度")

    def delete(self, kb_id):
        self.calls.append(("delete", kb_id))
        if self.raise_not_found:
            raise KnowledgeBaseNotFoundError(kb_id)
        return make_kb(kb_id=kb_id)


def create_test_client(fake_service):
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_kb_service] = lambda: fake_service
    return TestClient(app)


def test_create_knowledge_base_returns_201_and_trims_name():
    fake = FakeKBService()
    client = create_test_client(fake)

    response = client.post(
        "/knowledge-bases",
        json={"name": "  HR 制度  ", "description": "  人事  "},
    )

    assert response.status_code == 201
    assert fake.calls == [("create", "HR 制度", "人事")]
    assert response.json()["name"] == "HR 制度"


def test_list_knowledge_bases_returns_array_with_counts():
    fake = FakeKBService()
    client = create_test_client(fake)

    response = client.get("/knowledge-bases")

    assert response.status_code == 200
    payload = response.json()
    assert payload[0]["document_count"] == 3


def test_update_knowledge_base_passes_partial_fields():
    fake = FakeKBService()
    client = create_test_client(fake)

    response = client.patch("/knowledge-bases/kb_1", json={"name": "新名字"})

    assert response.status_code == 200
    assert fake.calls == [("update", "kb_1", "新名字", None)]


def test_delete_knowledge_base_returns_deleted_record():
    fake = FakeKBService()
    client = create_test_client(fake)

    response = client.delete("/knowledge-bases/kb_1")

    assert response.status_code == 200
    assert response.json()["id"] == "kb_1"
    assert fake.calls == [("delete", "kb_1")]


def test_create_rejects_blank_name_before_calling_service():
    fake = FakeKBService()
    client = create_test_client(fake)

    response = client.post("/knowledge-bases", json={"name": "   "})

    assert response.status_code == 422
    assert fake.calls == []


def test_missing_knowledge_base_maps_to_404():
    fake = FakeKBService(raise_not_found=True)
    client = create_test_client(fake)

    assert client.patch("/knowledge-bases/ghost", json={"name": "x"}).status_code == 404
    assert client.delete("/knowledge-bases/ghost").status_code == 404
