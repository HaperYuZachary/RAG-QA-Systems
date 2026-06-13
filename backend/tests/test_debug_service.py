import pytest

from app.config import Settings
from app.core.reranker import RerankedCandidate
from app.core.retriever import RetrievalResult
from app.services.debug_service import DebugService


class FakeClock:
    def __init__(self, values):
        self.values = iter(values)

    def __call__(self):
        return next(self.values)


class FakeEmbedder:
    def __init__(self):
        self.calls = []

    def embed(self, texts):
        self.calls.append(list(texts))
        return [[0.1, 0.2, 0.3]]


class FakeRetriever:
    def __init__(self):
        self.calls = []
        self.results = [
            RetrievalResult(
                id="chunk_a",
                text="员工满一年享有五天年假。",
                metadata={"document_id": "doc_a", "chunk_index": 0},
                rrf_score=0.031,
                vector_rank=1,
                vector_distance=0.12,
                bm25_rank=None,
                bm25_score=None,
            ),
            RetrievalResult(
                id="chunk_b",
                text="年假余额可以在人事系统查看。",
                metadata={"document_id": "doc_b", "chunk_index": 1},
                rrf_score=0.029,
                vector_rank=None,
                vector_distance=None,
                bm25_rank=1,
                bm25_score=2.4,
            ),
        ]

    def retrieve(self, kb_id, query, query_embedding, top_k):
        self.calls.append(
            {
                "kb_id": kb_id,
                "query": query,
                "query_embedding": query_embedding,
                "top_k": top_k,
            }
        )
        return list(self.results)


class FakeReranker:
    def __init__(self):
        self.calls = []

    def rerank(self, query, candidates, top_k):
        candidate_list = list(candidates)
        self.calls.append(
            {
                "query": query,
                "candidates": candidate_list,
                "top_k": top_k,
            }
        )
        return [
            RerankedCandidate(
                id=candidate_list[1].id,
                text=candidate_list[1].text,
                metadata=candidate_list[1].metadata,
                rrf_score=candidate_list[1].rrf_score,
                vector_rank=candidate_list[1].vector_rank,
                vector_distance=candidate_list[1].vector_distance,
                bm25_rank=candidate_list[1].bm25_rank,
                bm25_score=candidate_list[1].bm25_score,
                rerank_score=0.92,
            ),
            RerankedCandidate(
                id=candidate_list[0].id,
                text=candidate_list[0].text,
                metadata=candidate_list[0].metadata,
                rrf_score=candidate_list[0].rrf_score,
                vector_rank=candidate_list[0].vector_rank,
                vector_distance=candidate_list[0].vector_distance,
                bm25_rank=candidate_list[0].bm25_rank,
                bm25_score=candidate_list[0].bm25_score,
                rerank_score=0.41,
            ),
        ]


def test_debug_search_runs_embed_retrieve_rerank_and_returns_scores_with_timings():
    embedder = FakeEmbedder()
    retriever = FakeRetriever()
    reranker = FakeReranker()
    clock = FakeClock([0.0, 0.0, 0.010, 0.010, 0.030, 0.030, 0.035, 0.040])
    service = DebugService(
        Settings(),
        embedder=embedder,
        retriever=retriever,
        reranker=reranker,
        clock=clock,
    )

    response = service.search(kb_id="kb_1", query="年假", top_k=2)

    assert embedder.calls == [["年假"]]
    assert retriever.calls == [
        {
            "kb_id": "kb_1",
            "query": "年假",
            "query_embedding": [0.1, 0.2, 0.3],
            "top_k": 2,
        }
    ]
    assert [candidate.id for candidate in reranker.calls[0]["candidates"]] == [
        "chunk_a",
        "chunk_b",
    ]
    assert reranker.calls[0]["top_k"] == 2

    assert response.query == "年假"
    assert response.timings.embedding_ms == pytest.approx(10.0)
    assert response.timings.retrieval_ms == pytest.approx(20.0)
    assert response.timings.rerank_ms == pytest.approx(5.0)
    assert response.timings.total_ms == pytest.approx(40.0)

    assert [hit.id for hit in response.hits] == ["chunk_b", "chunk_a"]
    first_hit = response.hits[0]
    assert first_hit.text == "年假余额可以在人事系统查看。"
    assert first_hit.metadata == {"document_id": "doc_b", "chunk_index": 1}
    assert first_hit.vector_rank is None
    assert first_hit.vector_distance is None
    assert first_hit.bm25_rank == 1
    assert first_hit.bm25_score == pytest.approx(2.4)
    assert first_hit.rrf_score == pytest.approx(0.029)
    assert first_hit.rerank_score == pytest.approx(0.92)


def test_debug_search_handles_empty_results():
    class EmptyRetriever(FakeRetriever):
        def __init__(self):
            super().__init__()
            self.results = []

    class EmptyReranker(FakeReranker):
        def rerank(self, query, candidates, top_k):
            self.calls.append(
                {"query": query, "candidates": list(candidates), "top_k": top_k}
            )
            return []

    clock = FakeClock([1.0, 1.0, 1.001, 1.001, 1.002, 1.002, 1.003, 1.003])
    service = DebugService(
        Settings(),
        embedder=FakeEmbedder(),
        retriever=EmptyRetriever(),
        reranker=EmptyReranker(),
        clock=clock,
    )

    response = service.search(kb_id="kb_1", query="没有命中", top_k=5)

    assert response.hits == []
    assert response.timings.total_ms == pytest.approx(3.0)
