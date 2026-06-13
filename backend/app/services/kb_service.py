from contextlib import closing
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import uuid4

from app.config import Settings, settings
from app.db.sqlite_client import get_connection


class KnowledgeBaseNotFoundError(Exception):
    pass


@dataclass(frozen=True)
class KnowledgeBase:
    id: str
    name: str
    description: str
    created_at: str
    updated_at: str
    document_count: int = 0


_SELECT_WITH_COUNT = """
    SELECT kb.id, kb.name, kb.description, kb.created_at, kb.updated_at,
           COUNT(d.id) AS document_count
    FROM knowledge_bases kb
    LEFT JOIN documents d ON d.kb_id = kb.id
"""


class KBService:
    def __init__(
        self,
        app_settings: Settings | None = None,
        id_factory=None,
        vector_store=None,
    ):
        self.settings = app_settings or settings
        self.id_factory = id_factory or (lambda: f"kb_{uuid4()}")
        # 可选：删除知识库时一并清掉其向量 collection；不注入则跳过（测试无需 Chroma）
        self.vector_store = vector_store

    def create(self, name: str, description: str = "") -> KnowledgeBase:
        kb_id = self.id_factory()
        now = _utc_now()
        with closing(get_connection(self.settings)) as conn, conn:
            conn.execute(
                """
                INSERT INTO knowledge_bases (id, name, description, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (kb_id, name, description, now, now),
            )
        return KnowledgeBase(
            id=kb_id,
            name=name,
            description=description,
            created_at=now,
            updated_at=now,
            document_count=0,
        )

    def list(self) -> list[KnowledgeBase]:
        with closing(get_connection(self.settings)) as conn, conn:
            rows = conn.execute(
                f"{_SELECT_WITH_COUNT} GROUP BY kb.id "
                "ORDER BY kb.created_at DESC, kb.id DESC"
            ).fetchall()
        return [_row_to_kb(row) for row in rows]

    def get(self, kb_id: str) -> KnowledgeBase:
        with closing(get_connection(self.settings)) as conn, conn:
            row = conn.execute(
                f"{_SELECT_WITH_COUNT} WHERE kb.id = ? GROUP BY kb.id",
                (kb_id,),
            ).fetchone()
        if row is None:
            raise KnowledgeBaseNotFoundError(kb_id)
        return _row_to_kb(row)

    def update(
        self,
        kb_id: str,
        name: str | None = None,
        description: str | None = None,
    ) -> KnowledgeBase:
        existing = self.get(kb_id)  # 不存在则抛 KnowledgeBaseNotFoundError
        new_name = existing.name if name is None else name
        new_description = (
            existing.description if description is None else description
        )
        now = _utc_now()
        with closing(get_connection(self.settings)) as conn, conn:
            conn.execute(
                """
                UPDATE knowledge_bases
                SET name = ?, description = ?, updated_at = ?
                WHERE id = ?
                """,
                (new_name, new_description, now, kb_id),
            )
        return self.get(kb_id)

    def delete(self, kb_id: str) -> KnowledgeBase:
        existing = self.get(kb_id)  # 不存在则抛 KnowledgeBaseNotFoundError
        with closing(get_connection(self.settings)) as conn, conn:
            # documents / conversations 经 FK ON DELETE CASCADE 级联清除
            # （get_connection 已开启 PRAGMA foreign_keys=ON）
            conn.execute("DELETE FROM knowledge_bases WHERE id = ?", (kb_id,))
        if self.vector_store is not None:
            self.vector_store.delete_collection(kb_id)
        return existing


def _row_to_kb(row) -> KnowledgeBase:
    return KnowledgeBase(
        id=row["id"],
        name=row["name"],
        description=row["description"] or "",
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        document_count=int(row["document_count"]),
    )


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()
