import pytest

from app.config import Settings
from app.core.reranker import Reranker, RerankerError
from app.core.retriever import RetrievalResult


class FakeRerankerClient:
    def __init__(self, scores):
        self.scores = scores
        self.calls = []

    def compute_score(self, pairs):
        self.calls.append(list(pairs))
        return list(self.scores)


def candidate(chunk_id, text, rrf_score=0.0):
    return RetrievalResult(
        id=chunk_id,
        text=text,
        metadata={"document_id": f"doc_{chunk_id}"},
        rrf_score=rrf_score,
    )


def test_reranker_reorders_candidates_by_model_score_and_limits_top_k():
    candidates = [
        candidate("chunk_1", "年假申请流程", rrf_score=0.30),
        candidate("chunk_2", "报销发票要求", rrf_score=0.90),
        candidate("chunk_3", "年假余额查询", rrf_score=0.20),
    ]
    client = FakeRerankerClient(scores=[0.41, 0.12, 0.96])
    reranker = Reranker(
        Settings(enable_reranker=True, reranker_model="test-reranker"),
        client=client,
    )

    results = reranker.rerank("如何查询年假？", candidates, top_k=2)

    assert client.calls == [
        [
            ["如何查询年假？", "年假申请流程"],
            ["如何查询年假？", "报销发票要求"],
            ["如何查询年假？", "年假余额查询"],
        ]
    ]
    assert [result.id for result in results] == ["chunk_3", "chunk_1"]
    assert results[0].rerank_score == pytest.approx(0.96)
    assert results[0].rrf_score == pytest.approx(0.20)
    assert results[0].metadata == {"document_id": "doc_chunk_3"}


def test_reranker_disabled_returns_original_order_without_calling_client():
    candidates = [
        candidate("chunk_1", "first"),
        candidate("chunk_2", "second"),
        candidate("chunk_3", "third"),
    ]
    client = FakeRerankerClient(scores=[0.0, 1.0, 0.5])
    reranker = Reranker(Settings(enable_reranker=False), client=client)

    results = reranker.rerank("question", candidates, top_k=2)

    assert [result.id for result in results] == ["chunk_1", "chunk_2"]
    assert [result.rerank_score for result in results] == [None, None]
    assert client.calls == []


def test_reranker_uses_settings_top_k_by_default():
    candidates = [
        candidate(f"chunk_{index}", f"text {index}")
        for index in range(6)
    ]
    client = FakeRerankerClient(scores=[0.1, 0.6, 0.2, 0.5, 0.4, 0.3])
    reranker = Reranker(
        Settings(enable_reranker=True, reranker_top_k=5),
        client=client,
    )

    results = reranker.rerank("question", candidates)

    assert [result.id for result in results] == [
        "chunk_1",
        "chunk_3",
        "chunk_4",
        "chunk_5",
        "chunk_2",
    ]


def test_reranker_default_client_is_created_lazily_only_when_enabled():
    class LazyReranker(Reranker):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.created = False

        def _create_client(self):
            self.created = True
            return FakeRerankerClient(scores=[0.7])

    disabled = LazyReranker(Settings(enable_reranker=False))
    assert disabled.rerank("question", [candidate("chunk_1", "text")])
    assert disabled.created is False

    enabled = LazyReranker(Settings(enable_reranker=True))
    results = enabled.rerank("question", [candidate("chunk_1", "text")])

    assert enabled.created is True
    assert results[0].rerank_score == pytest.approx(0.7)


def test_reranker_raises_when_model_returns_wrong_score_count():
    reranker = Reranker(
        Settings(enable_reranker=True),
        client=FakeRerankerClient(scores=[0.9]),
    )

    with pytest.raises(RerankerError, match="score count"):
        reranker.rerank(
            "question",
            [candidate("chunk_1", "first"), candidate("chunk_2", "second")],
        )
