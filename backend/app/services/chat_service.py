from collections.abc import Iterator
from contextlib import closing
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
from uuid import uuid4

from app.config import Settings, settings
from app.core.citation import resolve_citations
from app.core.embedder import Embedder
from app.core.generator import LLMGenerator
from app.core.reranker import Reranker
from app.core.retriever import HybridRetriever
from app.db.sqlite_client import get_connection


@dataclass(frozen=True)
class ChatStreamEvent:
    event: str
    data: dict


class ChatService:
    def __init__(
        self,
        app_settings: Settings | None = None,
        embedder=None,
        retriever=None,
        reranker=None,
        generator=None,
        citation_resolver=resolve_citations,
        id_factory=None,
    ):
        self.settings = app_settings or settings
        self.embedder = embedder or Embedder(self.settings)
        self.retriever = retriever or HybridRetriever(self.settings)
        self.reranker = reranker or Reranker(self.settings)
        self.generator = generator or LLMGenerator(self.settings)
        self.citation_resolver = citation_resolver
        self.id_factory = id_factory or (lambda prefix: f"{prefix}_{uuid4()}")

    def stream_chat(
        self,
        kb_id: str,
        question: str,
        conversation_id: str | None = None,
    ) -> Iterator[ChatStreamEvent]:
        active_conversation_id = conversation_id or self._create_conversation(
            kb_id=kb_id,
            title=_conversation_title(question),
        )
        # 先读历史，再落库当前问题——否则会把当前这条 user 消息也算进历史
        history = self._load_history(active_conversation_id)
        self._save_message(
            conversation_id=active_conversation_id,
            role="user",
            content=question,
            sources=None,
        )

        query_embedding = self.embedder.embed([question])[0]
        candidates = self.retriever.retrieve(
            kb_id=kb_id,
            query=question,
            query_embedding=query_embedding,
        )
        ranked_contexts = self.reranker.rerank(question, candidates)

        answer_parts: list[str] = []
        for token in self.generator.stream_chat(
            question, ranked_contexts, history=history
        ):
            answer_parts.append(token)
            yield ChatStreamEvent(event="chunk", data={"delta": token})

        raw_answer = "".join(answer_parts)
        citation_result = self.citation_resolver(raw_answer, ranked_contexts)
        sources_payload = {
            "sources": [asdict(source) for source in citation_result.sources],
            "invalid_references": citation_result.invalid_references,
        }
        assistant_message_id = self._save_message(
            conversation_id=active_conversation_id,
            role="assistant",
            content=citation_result.answer,
            sources=sources_payload,
        )
        self._touch_conversation(active_conversation_id)

        yield ChatStreamEvent(event="sources", data=sources_payload)
        yield ChatStreamEvent(
            event="done",
            data={
                "conversation_id": active_conversation_id,
                "message_id": assistant_message_id,
                "answer": citation_result.answer,
            },
        )

    def _load_history(self, conversation_id: str) -> list[dict]:
        limit = self.settings.max_history_messages
        if limit <= 0:
            return []

        with closing(get_connection(self.settings)) as conn, conn:
            rows = conn.execute(
                """
                SELECT role, content FROM messages
                WHERE conversation_id = ?
                ORDER BY rowid DESC
                LIMIT ?
                """,
                (conversation_id, limit),
            ).fetchall()

        # rowid DESC + LIMIT 取最近 N 条，再 reversed 还原成时间正序
        return [
            {"role": row["role"], "content": row["content"]}
            for row in reversed(rows)
        ]

    def _create_conversation(self, kb_id: str, title: str) -> str:
        conversation_id = self.id_factory("conv")
        now = _utc_now()
        with closing(get_connection(self.settings)) as conn, conn:
            conn.execute(
                """
                INSERT INTO conversations (id, kb_id, title, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (conversation_id, kb_id, title, now, now),
            )
        return conversation_id

    def _touch_conversation(self, conversation_id: str) -> None:
        with closing(get_connection(self.settings)) as conn, conn:
            conn.execute(
                "UPDATE conversations SET updated_at = ? WHERE id = ?",
                (_utc_now(), conversation_id),
            )

    def _save_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        sources: dict | None,
    ) -> str:
        message_id = self.id_factory("msg")
        with closing(get_connection(self.settings)) as conn, conn:
            conn.execute(
                """
                INSERT INTO messages (
                    id, conversation_id, role, content, sources, token_count, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    message_id,
                    conversation_id,
                    role,
                    content,
                    (
                        json.dumps(sources, ensure_ascii=False)
                        if sources is not None
                        else None
                    ),
                    len(content),
                    _utc_now(),
                ),
            )
        return message_id


def _conversation_title(question: str) -> str:
    title = " ".join(question.split())
    return title[:80] or "New conversation"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()
