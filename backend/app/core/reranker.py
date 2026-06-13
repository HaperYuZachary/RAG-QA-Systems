from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

from app.config import Settings, settings


DEFAULT_RERANKER_TOP_K = 5


class RerankerError(RuntimeError):
    pass


@dataclass(frozen=True)
class RerankedCandidate:
    id: str
    text: str
    metadata: dict = field(default_factory=dict)
    rrf_score: float = 0.0
    vector_rank: int | None = None
    bm25_rank: int | None = None
    vector_distance: float | None = None
    bm25_score: float | None = None
    rerank_score: float | None = None


class Reranker:
    def __init__(
        self,
        app_settings: Settings | None = None,
        client=None,
    ):
        self.settings = app_settings or settings
        self._client = client

    @property
    def client(self):
        if self._client is None:
            self._client = self._create_client()
        return self._client

    def rerank(
        self,
        query: str,
        candidates: Sequence[Any],
        top_k: int | None = None,
    ) -> list[RerankedCandidate]:
        limit = top_k if top_k is not None else self.settings.reranker_top_k
        if limit <= 0 or not candidates:
            return []

        candidate_list = list(candidates)
        if not self.settings.enable_reranker:
            return [
                _to_reranked_candidate(candidate, rerank_score=None)
                for candidate in candidate_list[:limit]
            ]

        scores = self._score(query, candidate_list)
        if len(scores) != len(candidate_list):
            raise RerankerError("Reranker score count must match candidate count")

        ranked = [
            _to_reranked_candidate(candidate, rerank_score=score)
            for candidate, score in zip(candidate_list, scores, strict=True)
        ]
        ranked.sort(
            key=lambda candidate: (
                -(candidate.rerank_score or 0.0),
                -candidate.rrf_score,
                candidate.id,
            )
        )
        return ranked[:limit]

    def _score(self, query: str, candidates: list[Any]) -> list[float]:
        pairs = [[query, candidate.text] for candidate in candidates]

        if hasattr(self.client, "compute_score"):
            raw_scores = self.client.compute_score(pairs)
        elif hasattr(self.client, "rerank"):
            raw_scores = self.client.rerank(
                model=self.settings.reranker_model,
                query=query,
                documents=[candidate.text for candidate in candidates],
                top_n=len(candidates),
            )
        else:
            raise RerankerError("Reranker client must expose compute_score or rerank")

        return _normalize_scores(raw_scores, len(candidates))

    def _create_client(self):
        try:
            from FlagEmbedding import FlagReranker
        except ImportError as exc:
            raise RerankerError(
                "FlagEmbedding is required for the default local reranker; "
                "install it or inject a reranker client"
            ) from exc

        return FlagReranker(
            self.settings.reranker_model,
            use_fp16=self.settings.reranker_use_fp16,
        )


def _to_reranked_candidate(candidate: Any, rerank_score: float | None) -> RerankedCandidate:
    return RerankedCandidate(
        id=candidate.id,
        text=candidate.text,
        metadata=dict(getattr(candidate, "metadata", {}) or {}),
        rrf_score=float(getattr(candidate, "rrf_score", 0.0) or 0.0),
        vector_rank=getattr(candidate, "vector_rank", None),
        bm25_rank=getattr(candidate, "bm25_rank", None),
        vector_distance=getattr(candidate, "vector_distance", None),
        bm25_score=getattr(candidate, "bm25_score", None),
        rerank_score=rerank_score,
    )


def _normalize_scores(raw_scores, expected_count: int) -> list[float]:
    if expected_count == 1 and isinstance(raw_scores, int | float):
        return [float(raw_scores)]

    if hasattr(raw_scores, "results"):
        return _scores_from_ranked_response(raw_scores.results, expected_count)

    if isinstance(raw_scores, dict) and "results" in raw_scores:
        return _scores_from_ranked_response(raw_scores["results"], expected_count)

    return [float(score) for score in raw_scores]


def _scores_from_ranked_response(results, expected_count: int) -> list[float]:
    scores = [0.0 for _ in range(expected_count)]
    for result in results:
        index = _read_attr(result, "index")
        score = _read_attr(result, "relevance_score")
        if index is None:
            index = _read_attr(result, "document_index")
        if score is None:
            score = _read_attr(result, "score")
        if index is not None and 0 <= int(index) < expected_count and score is not None:
            scores[int(index)] = float(score)
    return scores


def _read_attr(value, name: str):
    if isinstance(value, dict):
        return value.get(name)
    return getattr(value, name, None)
