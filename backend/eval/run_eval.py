from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
import logging
import os
from pathlib import Path
import sys
from typing import Any

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from dotenv import load_dotenv
import jieba

load_dotenv(BACKEND_ROOT / ".env")
for env_name in ("DATA_DIR", "EMBEDDING_CACHE_DIR"):
    env_value = os.getenv(env_name)
    if env_value and not Path(env_value).is_absolute():
        os.environ[env_name] = str((BACKEND_ROOT / env_value).resolve())

for logger_name in (
    "chromadb.segment.impl.metadata.sqlite",
    "chromadb.segment.impl.vector.brute_force_index",
    "chromadb.segment.impl.vector.local_hnsw",
    "chromadb.segment.impl.vector.local_persistent_hnsw",
):
    logging.getLogger(logger_name).setLevel(logging.ERROR)
jieba.setLogLevel(logging.ERROR)

from app.config import settings
from app.core.embedder import Embedder
from app.core.reranker import Reranker
from app.core.retriever import HybridRetriever
from app.db.sqlite_client import get_connection


DEFAULT_QA_SET_PATH = Path(__file__).with_name("qa_set.json")
DEFAULT_TOP_K = 5
DEFAULT_STAGE_TOP_K = 20


@dataclass(frozen=True)
class EvalCase:
    id: str
    question: str
    answer: str
    gold_chunk_ids: list[str] | None = None
    gold_text_contains: list[str] | None = None


def load_qa_set(path: Path | str = DEFAULT_QA_SET_PATH) -> tuple[dict, list[EvalCase]]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    cases = [
        EvalCase(
            id=str(item["id"]),
            question=str(item["question"]),
            answer=str(item.get("answer", "")),
            gold_chunk_ids=list(item.get("gold_chunk_ids") or []),
            gold_text_contains=list(item.get("gold_text_contains") or []),
        )
        for item in payload.get("questions", [])
    ]
    return payload, cases


def evaluate_retrievers(
    cases: list[EvalCase],
    *,
    kb_id: str,
    embedder,
    retriever,
    reranker,
    top_k: int = DEFAULT_TOP_K,
    stage_top_k: int = DEFAULT_STAGE_TOP_K,
) -> dict[str, dict]:
    embeddings = embedder.embed([case.question for case in cases])

    vector_results = []
    hybrid_results = []
    rerank_results = []

    vector_pool_k = max(top_k, DEFAULT_TOP_K)
    for case, embedding in zip(cases, embeddings, strict=True):
        vector_results.append(
            retriever.retrieve(
                kb_id=kb_id,
                query=case.question,
                query_embedding=embedding,
                top_k=top_k,
                vector_top_k=vector_pool_k,
                bm25_top_k=0,
            )
        )

    for case, embedding in zip(cases, embeddings, strict=True):
        hybrid_results.append(
            retriever.retrieve(
                kb_id=kb_id,
                query=case.question,
                query_embedding=embedding,
                top_k=top_k,
                vector_top_k=stage_top_k,
                bm25_top_k=stage_top_k,
            )
        )

    # 关键：rerank 必须在更大的融合候选池上做（取 stage_top_k 条），再精排到 top_k。
    # 否则只在 top_k 内重排，无法把 RRF 排在偏后却相关的 chunk 捞进 top_k，
    # rerank 的召回提升永远体现不出来。
    rerank_candidate_k = max(stage_top_k, top_k)
    for case, embedding in zip(cases, embeddings, strict=True):
        candidates = retriever.retrieve(
            kb_id=kb_id,
            query=case.question,
            query_embedding=embedding,
            top_k=rerank_candidate_k,
            vector_top_k=stage_top_k,
            bm25_top_k=stage_top_k,
        )
        rerank_results.append(
            reranker.rerank(
                case.question,
                candidates,
                top_k=top_k,
            )
        )

    return {
        "vector": _summarize_config(cases, vector_results, top_k),
        "hybrid_rrf": _summarize_config(cases, hybrid_results, top_k),
        "hybrid_rerank": _summarize_config(cases, rerank_results, top_k),
    }


def recall_at_k(cases: list[EvalCase], retrieved_by_case: list[list[Any]], k: int) -> float:
    if not cases:
        return 0.0

    hits = 0
    for case, retrieved in zip(cases, retrieved_by_case, strict=True):
        if any(is_gold_hit(hit, case) for hit in list(retrieved)[:k]):
            hits += 1

    return hits / len(cases)


def is_gold_hit(hit: Any, case: EvalCase) -> bool:
    hit_id = _read_attr(hit, "id")
    hit_text = str(_read_attr(hit, "text") or "")

    if hit_id and hit_id in set(case.gold_chunk_ids or []):
        return True

    return any(snippet and snippet in hit_text for snippet in case.gold_text_contains or [])


def resolve_kb_id(kb_id: str | None, kb_name: str | None) -> str:
    if kb_id:
        return kb_id

    if not kb_name:
        raise ValueError("Either kb_id or kb_name is required")

    with get_connection(settings) as conn:
        row = conn.execute(
            "SELECT id FROM knowledge_bases WHERE name = ? ORDER BY created_at DESC LIMIT 1",
            (kb_name,),
        ).fetchone()

    if not row:
        raise ValueError(f"Knowledge base not found: {kb_name}")

    return str(row["id"])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run RAG retrieval evaluation and print Recall@5 comparisons.",
    )
    parser.add_argument("--qa-set", default=str(DEFAULT_QA_SET_PATH))
    parser.add_argument("--kb-id", default=None)
    parser.add_argument("--kb-name", default=None)
    parser.add_argument("--top-k", type=int, default=DEFAULT_TOP_K)
    parser.add_argument("--stage-top-k", type=int, default=DEFAULT_STAGE_TOP_K)
    args = parser.parse_args(argv)

    metadata, cases = load_qa_set(args.qa_set)
    kb_id = resolve_kb_id(
        args.kb_id or metadata.get("kb_id"),
        args.kb_name or metadata.get("kb_name"),
    )

    result = evaluate_retrievers(
        cases,
        kb_id=kb_id,
        embedder=Embedder(settings),
        retriever=HybridRetriever(settings),
        reranker=Reranker(settings),
        top_k=args.top_k,
        stage_top_k=args.stage_top_k,
    )
    print_report(result, case_count=len(cases), top_k=args.top_k)
    if not settings.enable_reranker:
        print("")
        print("Note: ENABLE_RERANKER=false; hybrid_rerank uses the fused order without model reranking.")
    return 0


def print_report(result: dict[str, dict], *, case_count: int, top_k: int) -> None:
    print(f"Evaluation cases: {case_count}")
    print(f"Metric: Recall@{top_k}")
    print("")
    print("| config | recall | hits |")
    print("| --- | ---: | ---: |")
    for key in ("vector", "hybrid_rrf", "hybrid_rerank"):
        item = result[key]
        print(f"| {key} | {item['recall_at_5']:.2%} | {item['hit_count']}/{item['case_count']} |")


def _summarize_config(
    cases: list[EvalCase],
    retrieved_by_case: list[list[Any]],
    top_k: int,
) -> dict:
    hits = [
        any(is_gold_hit(hit, case) for hit in list(retrieved)[:top_k])
        for case, retrieved in zip(cases, retrieved_by_case, strict=True)
    ]
    hit_count = sum(1 for hit in hits if hit)
    return {
        "recall_at_5": hit_count / len(cases) if cases else 0.0,
        "hit_count": hit_count,
        "case_count": len(cases),
        "misses": [
            case.id
            for case, hit in zip(cases, hits, strict=True)
            if not hit
        ],
    }


def _read_attr(value: Any, name: str):
    if isinstance(value, dict):
        return value.get(name)
    return getattr(value, name, None)


if __name__ == "__main__":
    raise SystemExit(main())
