from contextlib import closing
import json

import pytest

from app.config import Settings
from app.db.sqlite_client import get_connection, init_db
from app.services.conversation_service import (
    ConversationNotFoundError,
    ConversationService,
)


def seed_kb(settings: Settings, kb_id: str, name: str = "Default") -> None:
    with closing(get_connection(settings)) as conn, conn:
        conn.execute(
            """
            INSERT INTO knowledge_bases (id, name, created_at, updated_at)
            VALUES (?, ?, ?, ?)
            """,
            (kb_id, name, "2026-06-10T00:00:00", "2026-06-10T00:00:00"),
        )


def insert_conversation(
    settings: Settings,
    conversation_id: str,
    kb_id: str,
    title: str,
    created_at: str,
    updated_at: str,
) -> None:
    with closing(get_connection(settings)) as conn, conn:
        conn.execute(
            """
            INSERT INTO conversations (id, kb_id, title, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (conversation_id, kb_id, title, created_at, updated_at),
        )


def insert_message(
    settings: Settings,
    message_id: str,
    conversation_id: str,
    role: str,
    content: str,
    created_at: str,
    sources: dict | None = None,
) -> None:
    with closing(get_connection(settings)) as conn, conn:
        conn.execute(
            """
            INSERT INTO messages
                (id, conversation_id, role, content, sources, token_count, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                message_id,
                conversation_id,
                role,
                content,
                json.dumps(sources, ensure_ascii=False) if sources is not None else None,
                len(content),
                created_at,
            ),
        )


def test_list_conversations_filters_by_kb_and_orders_by_recent_update(tmp_path):
    settings = Settings(data_dir=str(tmp_path))
    init_db(settings)
    seed_kb(settings, "kb_1")
    seed_kb(settings, "kb_2", name="Other")
    insert_conversation(
        settings,
        "conv_old",
        "kb_1",
        "旧会话",
        "2026-06-10T00:00:00",
        "2026-06-10T00:10:00",
    )
    insert_conversation(
        settings,
        "conv_recent",
        "kb_1",
        "新会话",
        "2026-06-11T00:00:00",
        "2026-06-11T00:10:00",
    )
    insert_conversation(
        settings,
        "conv_other_kb",
        "kb_2",
        "别的知识库",
        "2026-06-12T00:00:00",
        "2026-06-12T00:10:00",
    )
    insert_message(settings, "msg_1", "conv_old", "user", "问题一", "2026-06-10T00:01:00")
    insert_message(
        settings,
        "msg_2",
        "conv_old",
        "assistant",
        "回答一",
        "2026-06-10T00:02:00",
    )
    insert_message(
        settings,
        "msg_3",
        "conv_recent",
        "user",
        "问题二",
        "2026-06-11T00:01:00",
    )

    conversations = ConversationService(settings).list_conversations("kb_1")

    assert conversations == [
        {
            "id": "conv_recent",
            "title": "新会话",
            "created_at": "2026-06-11T00:00:00",
            "updated_at": "2026-06-11T00:10:00",
            "message_count": 1,
        },
        {
            "id": "conv_old",
            "title": "旧会话",
            "created_at": "2026-06-10T00:00:00",
            "updated_at": "2026-06-10T00:10:00",
            "message_count": 2,
        },
    ]


def test_get_messages_returns_time_ordered_messages_and_decoded_sources(tmp_path):
    settings = Settings(data_dir=str(tmp_path))
    init_db(settings)
    seed_kb(settings, "kb_1")
    insert_conversation(
        settings,
        "conv_1",
        "kb_1",
        "带引用会话",
        "2026-06-10T00:00:00",
        "2026-06-10T00:03:00",
    )
    sources_payload = {
        "sources": [{"id": "chunk_1", "text": "年假制度", "index": 1}],
        "invalid_references": [3],
    }
    insert_message(
        settings,
        "msg_assistant",
        "conv_1",
        "assistant",
        "满一年五天[1]。",
        "2026-06-10T00:02:00",
        sources=sources_payload,
    )
    insert_message(
        settings,
        "msg_user",
        "conv_1",
        "user",
        "年假几天？",
        "2026-06-10T00:01:00",
    )

    messages = ConversationService(settings).get_messages("conv_1")

    assert messages == [
        {
            "id": "msg_user",
            "role": "user",
            "content": "年假几天？",
            "sources": None,
            "created_at": "2026-06-10T00:01:00",
        },
        {
            "id": "msg_assistant",
            "role": "assistant",
            "content": "满一年五天[1]。",
            "sources": sources_payload,
            "created_at": "2026-06-10T00:02:00",
        },
    ]


def test_delete_conversation_removes_messages_via_cascade(tmp_path):
    settings = Settings(data_dir=str(tmp_path))
    init_db(settings)
    seed_kb(settings, "kb_1")
    insert_conversation(
        settings,
        "conv_1",
        "kb_1",
        "待删除",
        "2026-06-10T00:00:00",
        "2026-06-10T00:03:00",
    )
    insert_message(settings, "msg_1", "conv_1", "user", "问题", "2026-06-10T00:01:00")

    ConversationService(settings).delete_conversation("conv_1")

    assert ConversationService(settings).list_conversations("kb_1") == []
    assert ConversationService(settings).get_messages("conv_1") == []


def test_delete_missing_conversation_raises(tmp_path):
    settings = Settings(data_dir=str(tmp_path))
    init_db(settings)

    with pytest.raises(ConversationNotFoundError):
        ConversationService(settings).delete_conversation("conv_missing")
