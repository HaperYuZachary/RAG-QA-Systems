import pytest

from app.core.retriever import HybridRetriever


class FakeVectorStore:
    def __init__(self):
        self.query_calls = []
        self.list_chunks_calls = []

    def query(self, kb_id, query_embedding, top_k):
        self.query_calls.append(
            {
                "kb_id": kb_id,
                "query_embedding": query_embedding,
                "top_k": top_k,
            }
        )
        return {
            "ids": [["chunk_vector", "chunk_shared"]],
            "documents": [
                [
                    "语义相关但没有直接关键词。",
                    "年假余额可以在人事系统查看。",
                ]
            ],
            "metadatas": [
                [
                    {"document_id": "doc_1", "chunk_index": 0},
                    {"document_id": "doc_2", "chunk_index": 1},
                ]
            ],
            "distances": [[0.1, 0.2]],
        }

    def list_chunks(self, kb_id):
        self.list_chunks_calls.append(kb_id)
        return [
            {
                "id": "chunk_vector",
                "text": "语义相关但没有直接关键词。",
                "metadata": {"document_id": "doc_1", "chunk_index": 0},
            },
            {
                "id": "chunk_keyword",
                "text": "年假申请需要填写审批表。",
                "metadata": {"document_id": "doc_3", "chunk_index": 0},
            },
            {
                "id": "chunk_shared",
                "text": "年假余额可以在人事系统查看。",
                "metadata": {"document_id": "doc_2", "chunk_index": 1},
            },
        ]


def test_hybrid_retriever_fuses_vector_and_bm25_results_with_rrf():
    vector_store = FakeVectorStore()
    retriever = HybridRetriever(vector_store=vector_store, rrf_k=60)

    results = retriever.retrieve(
        kb_id="kb_1",
        query="年假申请",
        query_embedding=[1.0, 0.0, 0.0],
        top_k=3,
        vector_top_k=2,
        bm25_top_k=2,
    )

    assert vector_store.query_calls == [
        {"kb_id": "kb_1", "query_embedding": [1.0, 0.0, 0.0], "top_k": 2}
    ]
    assert vector_store.list_chunks_calls == ["kb_1"]
    assert [result.id for result in results] == [
        "chunk_shared",
        "chunk_keyword",
        "chunk_vector",
    ]

    by_id = {result.id: result for result in results}
    assert by_id["chunk_shared"].rrf_score == pytest.approx(
        1 / (60 + 2) + 1 / (60 + 2)
    )
    assert by_id["chunk_keyword"].rrf_score == pytest.approx(1 / (60 + 1))
    assert by_id["chunk_vector"].rrf_score == pytest.approx(1 / (60 + 1))
    assert by_id["chunk_shared"].vector_rank == 2
    assert by_id["chunk_shared"].bm25_rank == 2
    assert by_id["chunk_keyword"].vector_rank is None
    assert by_id["chunk_keyword"].bm25_rank == 1
    assert by_id["chunk_vector"].vector_rank == 1
    assert by_id["chunk_vector"].bm25_rank is None


def test_hybrid_retriever_respects_top_k_and_preserves_metadata():
    retriever = HybridRetriever(vector_store=FakeVectorStore(), rrf_k=60)

    results = retriever.retrieve(
        kb_id="kb_1",
        query="年假申请",
        query_embedding=[1.0, 0.0, 0.0],
        top_k=1,
        vector_top_k=2,
        bm25_top_k=2,
    )

    assert len(results) == 1
    assert results[0].id == "chunk_shared"
    assert results[0].text == "年假余额可以在人事系统查看。"
    assert results[0].metadata == {"document_id": "doc_2", "chunk_index": 1}


def test_hybrid_retriever_returns_empty_for_non_positive_top_k():
    retriever = HybridRetriever(vector_store=FakeVectorStore(), rrf_k=60)

    assert retriever.retrieve("kb_1", "年假", [1.0], top_k=0) == []
