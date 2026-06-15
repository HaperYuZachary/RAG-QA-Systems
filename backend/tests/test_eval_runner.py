import pytest

from eval.run_eval import (
    EvalCase,
    evaluate_retrievers,
    is_gold_hit,
    recall_at_k,
)


class FakeEmbedder:
    def __init__(self):
        self.calls = []

    def embed(self, texts):
        self.calls.append(list(texts))
        return [[1.0, 0.0] for _ in texts]


class FakeRetriever:
    def __init__(self):
        self.calls = []
        self.results_by_query = {
            "问题 A": ["chunk_semantic", "chunk_other"],
            "问题 B": ["chunk_wrong", "chunk_keyword"],
        }

    def retrieve(
        self,
        kb_id,
        query,
        query_embedding,
        top_k,
        vector_top_k=20,
        bm25_top_k=20,
    ):
        self.calls.append(
            {
                "kb_id": kb_id,
                "query": query,
                "query_embedding": query_embedding,
                "top_k": top_k,
                "vector_top_k": vector_top_k,
                "bm25_top_k": bm25_top_k,
            }
        )
        return [
            {"id": chunk_id, "text": f"text for {chunk_id}"}
            for chunk_id in self.results_by_query[query]
        ][:top_k]


class FakeReranker:
    def __init__(self):
        self.calls = []

    def rerank(self, query, candidates, top_k):
        self.calls.append(
            {
                "query": query,
                "candidates": list(candidates),
                "top_k": top_k,
            }
        )
        candidate_list = list(candidates)
        if query == "问题 B":
            candidate_list = list(reversed(candidate_list))
        return candidate_list[:top_k]


def test_gold_hit_matches_chunk_ids_or_text_features():
    case = EvalCase(
        id="q1",
        question="问题",
        answer="答案",
        gold_chunk_ids=["chunk_a"],
        gold_text_contains=["关键证据"],
    )

    assert is_gold_hit({"id": "chunk_a", "text": "anything"}, case)
    assert is_gold_hit({"id": "chunk_b", "text": "包含关键证据的文本"}, case)
    assert not is_gold_hit({"id": "chunk_b", "text": "无关文本"}, case)


def test_recall_at_k_counts_questions_with_any_gold_hit_in_top_k():
    cases = [
        EvalCase("q1", "问题 1", "答案", gold_chunk_ids=["chunk_1"]),
        EvalCase("q2", "问题 2", "答案", gold_text_contains=["gold text"]),
    ]
    retrieved = [
        [{"id": "wrong", "text": "no"}, {"id": "chunk_1", "text": "yes"}],
        [{"id": "wrong", "text": "gold text appears"}],
    ]

    assert recall_at_k(cases, retrieved, k=1) == pytest.approx(0.5)
    assert recall_at_k(cases, retrieved, k=2) == pytest.approx(1.0)


def test_evaluate_retrievers_runs_vector_hybrid_and_rerank_configs():
    cases = [
        EvalCase("q1", "问题 A", "答案 A", gold_chunk_ids=["chunk_semantic"]),
        EvalCase("q2", "问题 B", "答案 B", gold_chunk_ids=["chunk_keyword"]),
    ]
    embedder = FakeEmbedder()
    retriever = FakeRetriever()
    reranker = FakeReranker()

    result = evaluate_retrievers(
        cases,
        kb_id="kb_1",
        embedder=embedder,
        retriever=retriever,
        reranker=reranker,
        top_k=1,
    )

    assert result["vector"]["recall_at_5"] == pytest.approx(0.5)
    assert result["hybrid_rrf"]["recall_at_5"] == pytest.approx(0.5)
    assert result["hybrid_rerank"]["recall_at_5"] == pytest.approx(1.0)

    assert retriever.calls == [
        {
            "kb_id": "kb_1",
            "query": "问题 A",
            "query_embedding": [1.0, 0.0],
            "top_k": 1,
            "vector_top_k": 5,
            "bm25_top_k": 0,
        },
        {
            "kb_id": "kb_1",
            "query": "问题 B",
            "query_embedding": [1.0, 0.0],
            "top_k": 1,
            "vector_top_k": 5,
            "bm25_top_k": 0,
        },
        {
            "kb_id": "kb_1",
            "query": "问题 A",
            "query_embedding": [1.0, 0.0],
            "top_k": 1,
            "vector_top_k": 20,
            "bm25_top_k": 20,
        },
        {
            "kb_id": "kb_1",
            "query": "问题 B",
            "query_embedding": [1.0, 0.0],
            "top_k": 1,
            "vector_top_k": 20,
            "bm25_top_k": 20,
        },
        {
            "kb_id": "kb_1",
            "query": "问题 A",
            "query_embedding": [1.0, 0.0],
            "top_k": 20,
            "vector_top_k": 20,
            "bm25_top_k": 20,
        },
        {
            "kb_id": "kb_1",
            "query": "问题 B",
            "query_embedding": [1.0, 0.0],
            "top_k": 20,
            "vector_top_k": 20,
            "bm25_top_k": 20,
        },
    ]
    assert [call["query"] for call in reranker.calls] == ["问题 A", "问题 B"]
