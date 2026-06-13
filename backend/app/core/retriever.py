from dataclasses import dataclass, field
from math import inf

from app.config import Settings, settings
from app.core.keyword_search import KeywordSearch
from app.core.vector_store import VectorStore


DEFAULT_RRF_K = 60
DEFAULT_RETRIEVAL_TOP_K = 10
DEFAULT_STAGE_TOP_K = 20


@dataclass
class RetrievalResult:
    id: str
    text: str
    metadata: dict = field(default_factory=dict)
    rrf_score: float = 0.0
    vector_rank: int | None = None
    bm25_rank: int | None = None
    vector_distance: float | None = None
    bm25_score: float | None = None


@dataclass(frozen=True)
class _VectorHit:
    id: str
    text: str
    metadata: dict
    rank: int
    distance: float | None


class HybridRetriever:
    def __init__(
        self,
        app_settings: Settings | None = None,
        vector_store=None,
        rrf_k: int = DEFAULT_RRF_K,
    ):
        self.settings = app_settings or settings
        self.vector_store = vector_store or VectorStore(self.settings)
        self.rrf_k = rrf_k

    def retrieve(
        self,
        kb_id: str,
        query: str,
        query_embedding: list[float],
        top_k: int = DEFAULT_RETRIEVAL_TOP_K,
        vector_top_k: int = DEFAULT_STAGE_TOP_K,
        bm25_top_k: int = DEFAULT_STAGE_TOP_K,
    ) -> list[RetrievalResult]:
        if top_k <= 0:
            return []

        # 顺序执行两路检索：MVP 规模下并行收益仅数十毫秒，而顺序调用彻底消除了
        # “多线程并发读同一个 Chroma client” 的线程安全假设——从根上杜绝并发隐患。
        vector_hits = self._search_vector(kb_id, query_embedding, vector_top_k)
        bm25_hits = self._search_bm25(kb_id, query, bm25_top_k)

        return self._fuse(vector_hits, bm25_hits)[:top_k]

    def _search_vector(
        self,
        kb_id: str,
        query_embedding: list[float],
        top_k: int,
    ) -> list[_VectorHit]:
        if top_k <= 0:
            return []

        result = self.vector_store.query(
            kb_id=kb_id,
            query_embedding=query_embedding,
            top_k=top_k,
        )
        ids = _first_result_list(result, "ids")
        documents = _first_result_list(result, "documents")
        metadatas = _first_result_list(result, "metadatas")
        distances = _first_result_list(result, "distances")

        hits = []
        for index, chunk_id in enumerate(ids):
            hits.append(
                _VectorHit(
                    id=chunk_id,
                    text=_get_or_default(documents, index, ""),
                    metadata=_get_or_default(metadatas, index, {}) or {},
                    rank=index + 1,
                    distance=_get_or_default(distances, index, None),
                )
            )
        return hits

    def _search_bm25(self, kb_id: str, query: str, top_k: int):
        if top_k <= 0:
            return []

        # 刻意每次查询都从 Chroma 拉全量 chunk 现建 BM25：保证索引永远最新、
        # 结构上不可能返回过期结果。MVP 规模足够；若未来真成瓶颈再引入
        # 带失效机制的缓存（届时需保证每条写入路径都失效，否则会读到旧索引）。
        chunks = self.vector_store.list_chunks(kb_id)
        keyword_search = KeywordSearch(
            documents=[chunk.get("text", "") for chunk in chunks],
            ids=[chunk.get("id", "") for chunk in chunks],
            metadatas=[chunk.get("metadata", {}) or {} for chunk in chunks],
        )
        return keyword_search.search(query, top_k=top_k)

    def _fuse(self, vector_hits, bm25_hits) -> list[RetrievalResult]:
        fused: dict[str, RetrievalResult] = {}

        for hit in vector_hits:
            result = fused.setdefault(
                hit.id,
                RetrievalResult(id=hit.id, text=hit.text, metadata=dict(hit.metadata)),
            )
            result.vector_rank = hit.rank
            result.vector_distance = hit.distance
            result.rrf_score += _rrf_score(self.rrf_k, hit.rank)

        for hit in bm25_hits:
            result = fused.setdefault(
                hit.id,
                RetrievalResult(id=hit.id, text=hit.text, metadata=dict(hit.metadata)),
            )
            result.bm25_rank = hit.rank
            result.bm25_score = hit.score
            result.rrf_score += _rrf_score(self.rrf_k, hit.rank)

        return sorted(
            fused.values(),
            key=lambda result: (
                -result.rrf_score,
                result.bm25_rank if result.bm25_rank is not None else inf,
                result.vector_rank if result.vector_rank is not None else inf,
                result.id,
            ),
        )


def _rrf_score(k: int, rank: int) -> float:
    return 1 / (k + rank)


def _first_result_list(result: dict, key: str) -> list:
    values = result.get(key) or [[]]
    if not values:
        return []
    return values[0] or []


def _get_or_default(values: list, index: int, default):
    return values[index] if index < len(values) else default
