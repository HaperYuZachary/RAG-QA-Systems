from contextlib import closing
import json

from app.config import Settings, settings
from app.db.sqlite_client import get_connection


class ConversationNotFoundError(Exception):
    pass


class ConversationService:
    def __init__(self, app_settings: Settings | None = None):
        self.settings = app_settings or settings

    def list_conversations(self, kb_id: str) -> list[dict]:
        with closing(get_connection(self.settings)) as conn, conn:
            rows = conn.execute(
                """
                SELECT
                    c.id,
                    c.title,
                    c.created_at,
                    c.updated_at,
                    COUNT(m.id) AS message_count
                FROM conversations c
                LEFT JOIN messages m ON m.conversation_id = c.id
                WHERE c.kb_id = ?
                GROUP BY c.id, c.title, c.created_at, c.updated_at
                ORDER BY c.updated_at DESC, c.id DESC
                """,
                (kb_id,),
            ).fetchall()

        return [
            {
                "id": row["id"],
                "title": row["title"] or "",
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
                "message_count": int(row["message_count"]),
            }
            for row in rows
        ]

    def get_messages(self, conversation_id: str) -> list[dict]:
        with closing(get_connection(self.settings)) as conn, conn:
            rows = conn.execute(
                """
                SELECT id, role, content, sources, created_at
                FROM messages
                WHERE conversation_id = ?
                ORDER BY created_at ASC, rowid ASC
                """,
                (conversation_id,),
            ).fetchall()

        return [_row_to_message(row) for row in rows]

    def delete_conversation(self, conversation_id: str) -> None:
        with closing(get_connection(self.settings)) as conn, conn:
            cursor = conn.execute(
                "DELETE FROM conversations WHERE id = ?",
                (conversation_id,),
            )
            if cursor.rowcount == 0:
                raise ConversationNotFoundError(conversation_id)


def _row_to_message(row) -> dict:
    return {
        "id": row["id"],
        "role": row["role"],
        "content": row["content"],
        "sources": _decode_sources(row["sources"]),
        "created_at": row["created_at"],
    }


def _decode_sources(raw_sources: str | None):
    if raw_sources is None:
        return None
    return json.loads(raw_sources)
