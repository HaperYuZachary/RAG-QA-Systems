import time
from collections.abc import Callable
from typing import Any

from app.api.schemas import DebugSearchHit, DebugSearchResponse, DebugTiming
from app.config import Settings, settings
from app.core.embedder import Embedder
from app.core.reranker import Reranker
from app.core.retriever import HybridRetriever


class DebugService:
    def __init__(
        self,
        app_settings: Settings | None = None,
        embedder=None,
        retriever=None,
        reranker=None,
        clock: Callable[[], float] = time.perf_counter,
    ):
        self.settings = app_settings or settings
        self.embedder = embedder or Embedder(self.settings)
        self.retriever = retriever or HybridRetriever(self.settings)
        self.reranker = reranker or Reranker(self.settings)
        self.clock = clock

    def search(self, kb_id: str, query: str, top_k: int) -> DebugSearchResponse:
        total_start = self.clock()

        embeddings, embedding_ms = self._timed(lambda: self.embedder.embed([query]))
        candidates, retrieval_ms = self._timed(
            lambda: self.retriever.retrieve(
                kb_id=kb_id,
                query=query,
                query_embedding=embeddings[0],
                top_k=top_k,
            )
        )
        ranked_candidates, rerank_ms = self._timed(
            lambda: self.reranker.rerank(
                query,
                candidates,
                top_k=top_k,
            )
        )
        total_ms = _elapsed_ms(total_start, self.clock())

        return DebugSearchResponse(
            query=query,
            hits=[_to_debug_hit(candidate) for candidate in ranked_candidates],
            timings=DebugTiming(
                embedding_ms=embedding_ms,
                retrieval_ms=retrieval_ms,
                rerank_ms=rerank_ms,
                total_ms=total_ms,
            ),
        )

    def _timed(self, operation):
        started_at = self.clock()
        result = operation()
        return result, _elapsed_ms(started_at, self.clock())


def _to_debug_hit(candidate: Any) -> DebugSearchHit:
    return DebugSearchHit(
        id=candidate.id,
        text=candidate.text,
        metadata=dict(getattr(candidate, "metadata", {}) or {}),
        vector_rank=getattr(candidate, "vector_rank", None),
        vector_distance=getattr(candidate, "vector_distance", None),
        bm25_rank=getattr(candidate, "bm25_rank", None),
        bm25_score=getattr(candidate, "bm25_score", None),
        rrf_score=getattr(candidate, "rrf_score", 0.0),
        rerank_score=getattr(candidate, "rerank_score", None),
    )


def _elapsed_ms(started_at: float, ended_at: float) -> float:
    return (ended_at - started_at) * 1000
