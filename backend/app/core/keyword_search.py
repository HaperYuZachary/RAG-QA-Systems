from collections.abc import Sequence
from dataclasses import dataclass, field

import jieba
from rank_bm25 import BM25Okapi


DEFAULT_TOP_K = 20


@dataclass(frozen=True)
class KeywordSearchResult:
    id: str
    text: str
    score: float
    rank: int
    metadata: dict = field(default_factory=dict)


class KeywordSearch:
    def __init__(
        self,
        documents: Sequence[str],
        ids: Sequence[str] | None = None,
        metadatas: Sequence[dict] | None = None,
    ):
        self.documents = list(documents)
        self.ids = list(ids) if ids is not None else [
            str(index) for index in range(len(self.documents))
        ]
        self.metadatas = list(metadatas) if metadatas is not None else [
            {} for _ in self.documents
        ]
        if len(self.ids) != len(self.documents):
            raise ValueError("ids length must match documents length")
        if len(self.metadatas) != len(self.documents):
            raise ValueError("metadatas length must match documents length")

        self.tokenized_documents = [_tokenize(document) for document in self.documents]
        self._token_sets = [set(tokens) for tokens in self.tokenized_documents]
        self._bm25 = (
            BM25Okapi(self.tokenized_documents)
            if any(self.tokenized_documents)
            else None
        )

    def search(self, query: str, top_k: int = DEFAULT_TOP_K) -> list[KeywordSearchResult]:
        if top_k <= 0 or self._bm25 is None:
            return []

        query_tokens = _tokenize(query)
        if not query_tokens:
            return []

        query_token_set = set(query_tokens)
        scores = self._bm25.get_scores(query_tokens)
        ranked_matches = [
            (index, float(score))
            for index, score in enumerate(scores)
            if query_token_set & self._token_sets[index]
        ]
        ranked_matches.sort(key=lambda item: (-item[1], item[0]))

        return [
            KeywordSearchResult(
                id=self.ids[index],
                text=self.documents[index],
                score=score,
                rank=rank,
                metadata=dict(self.metadatas[index]),
            )
            for rank, (index, score) in enumerate(ranked_matches[:top_k], start=1)
        ]


def _tokenize(text: str) -> list[str]:
    return [
        token.strip().lower()
        for token in jieba.cut_for_search(text)
        if token.strip()
    ]
