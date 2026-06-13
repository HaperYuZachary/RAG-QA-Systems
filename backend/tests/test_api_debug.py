from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.debug import get_debug_service, router
from app.api.schemas import DebugSearchHit, DebugSearchResponse, DebugTiming


class FakeDebugService:
    def __init__(self):
        self.calls = []

    def search(self, kb_id, query, top_k):
        self.calls.append({"kb_id": kb_id, "query": query, "top_k": top_k})
        return DebugSearchResponse(
            query=query,
            hits=[
                DebugSearchHit(
                    id="chunk_1",
                    text="员工满一年享有五天年假。",
                    metadata={"document_id": "doc_1"},
                    vector_rank=1,
                    vector_distance=0.12,
                    bm25_rank=2,
                    bm25_score=1.7,
                    rrf_score=0.031,
                    rerank_score=0.92,
                )
            ],
            timings=DebugTiming(
                embedding_ms=1.0,
                retrieval_ms=2.0,
                rerank_ms=3.0,
                total_ms=6.0,
            ),
        )


def create_test_client(fake_service):
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_debug_service] = lambda: fake_service
    return TestClient(app)


def test_debug_search_endpoint_returns_structured_scores_and_timings():
    fake_service = FakeDebugService()
    client = create_test_client(fake_service)

    response = client.post(
        "/debug/search",
        json={"kb_id": " kb_1 ", "query": " 年假 ", "top_k": 3},
    )

    assert response.status_code == 200
    assert fake_service.calls == [{"kb_id": "kb_1", "query": "年假", "top_k": 3}]
    payload = response.json()
    assert payload["query"] == "年假"
    assert payload["timings"] == {
        "embedding_ms": 1.0,
        "retrieval_ms": 2.0,
        "rerank_ms": 3.0,
        "total_ms": 6.0,
    }
    assert payload["hits"] == [
        {
            "id": "chunk_1",
            "text": "员工满一年享有五天年假。",
            "metadata": {"document_id": "doc_1"},
            "vector_rank": 1,
            "vector_distance": 0.12,
            "bm25_rank": 2,
            "bm25_score": 1.7,
            "rrf_score": 0.031,
            "rerank_score": 0.92,
        }
    ]


def test_debug_search_endpoint_rejects_invalid_request_before_calling_service():
    fake_service = FakeDebugService()
    client = create_test_client(fake_service)

    response = client.post("/debug/search", json={"kb_id": "kb_1", "query": ""})

    assert response.status_code == 422
    assert fake_service.calls == []


def test_get_debug_service_reuses_chat_service_components():
    class FakeChatService:
        def __init__(self):
            self.settings = object()
            self.embedder = object()
            self.retriever = object()
            self.reranker = object()

    chat_service = FakeChatService()

    debug_service = get_debug_service(chat_service=chat_service)

    assert debug_service.settings is chat_service.settings
    assert debug_service.embedder is chat_service.embedder
    assert debug_service.retriever is chat_service.retriever
    assert debug_service.reranker is chat_service.reranker
