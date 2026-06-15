import json

from fastapi import FastAPI
from fastapi.testclient import TestClient

import app.api.chat as chat_module
from app.api.chat import get_chat_service, get_conversation_service, router
from app.services.conversation_service import ConversationNotFoundError
from app.services.chat_service import ChatStreamEvent


class FakeChatService:
    def __init__(self):
        self.calls = []

    def stream_chat(self, kb_id, question, conversation_id=None):
        self.calls.append(
            {
                "kb_id": kb_id,
                "question": question,
                "conversation_id": conversation_id,
            }
        )
        yield ChatStreamEvent(event="chunk", data={"delta": "年假"})
        yield ChatStreamEvent(
            event="sources",
            data={"sources": [{"id": "chunk_1"}], "invalid_references": []},
        )
        yield ChatStreamEvent(
            event="done",
            data={"conversation_id": "conv_1", "answer": "年假[1]"},
        )


class FakeConversationService:
    def __init__(self):
        self.calls = []
        self.conversations = [
            {
                "id": "conv_1",
                "title": "年假",
                "created_at": "2026-06-10T00:00:00",
                "updated_at": "2026-06-10T00:02:00",
                "message_count": 2,
            }
        ]
        self.messages = [
            {
                "id": "msg_1",
                "role": "user",
                "content": "年假几天？",
                "sources": None,
                "created_at": "2026-06-10T00:01:00",
            },
            {
                "id": "msg_2",
                "role": "assistant",
                "content": "满一年五天[1]。",
                "sources": {"sources": [{"id": "chunk_1"}], "invalid_references": []},
                "created_at": "2026-06-10T00:02:00",
            },
        ]
        self.missing_ids = set()

    def list_conversations(self, kb_id):
        self.calls.append(("list_conversations", kb_id))
        return self.conversations

    def get_messages(self, conversation_id):
        self.calls.append(("get_messages", conversation_id))
        return self.messages

    def delete_conversation(self, conversation_id):
        self.calls.append(("delete_conversation", conversation_id))
        if conversation_id in self.missing_ids:
            raise ConversationNotFoundError(conversation_id)


def create_test_client(fake_service, fake_conversation_service=None):
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_chat_service] = lambda: fake_service
    if fake_conversation_service is not None:
        app.dependency_overrides[get_conversation_service] = (
            lambda: fake_conversation_service
        )
    return TestClient(app)


def parse_sse_events(response_text):
    events = []
    for frame in response_text.strip().split("\n\n"):
        lines = frame.splitlines()
        event_name = lines[0].removeprefix("event: ")
        data = json.loads(lines[1].removeprefix("data: "))
        events.append({"event": event_name, "data": data})
    return events


def test_chat_endpoint_streams_chat_service_events_as_sse_frames():
    fake_service = FakeChatService()
    client = create_test_client(fake_service)

    response = client.post(
        "/chat",
        json={
            "kb_id": " kb_1 ",
            "question": " 年假有几天？ ",
            "conversation_id": " conv_1 ",
        },
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert fake_service.calls == [
        {
            "kb_id": "kb_1",
            "question": "年假有几天？",
            "conversation_id": "conv_1",
        }
    ]
    assert parse_sse_events(response.text) == [
        {"event": "chunk", "data": {"delta": "年假"}},
        {
            "event": "sources",
            "data": {"sources": [{"id": "chunk_1"}], "invalid_references": []},
        },
        {
            "event": "done",
            "data": {"conversation_id": "conv_1", "answer": "年假[1]"},
        },
    ]


def test_chat_endpoint_converts_stream_failures_to_error_sse_frame():
    class FailingChatService:
        def stream_chat(self, kb_id, question, conversation_id=None):
            yield ChatStreamEvent(event="chunk", data={"delta": "先返回"})
            raise RuntimeError("generator unavailable")

    client = create_test_client(FailingChatService())

    response = client.post(
        "/chat",
        json={"kb_id": "kb_1", "question": "年假有几天？"},
    )

    assert response.status_code == 200
    assert parse_sse_events(response.text) == [
        {"event": "chunk", "data": {"delta": "先返回"}},
        {
            "event": "error",
            "data": {
                "message": "generator unavailable",
                "type": "RuntimeError",
            },
        },
    ]


def test_chat_endpoint_rejects_invalid_request_before_calling_service():
    fake_service = FakeChatService()
    client = create_test_client(fake_service)

    response = client.post("/chat", json={"kb_id": "kb_1", "question": "   "})

    assert response.status_code == 422
    assert fake_service.calls == []


def test_get_chat_service_builds_one_shared_instance(monkeypatch):
    created = []

    class DummyChatService:
        def __init__(self):
            created.append(self)

    monkeypatch.setattr(chat_module, "ChatService", DummyChatService)
    monkeypatch.setattr(chat_module, "_chat_service", None)

    first = chat_module.get_chat_service()
    second = chat_module.get_chat_service()

    assert first is second
    assert len(created) == 1


def test_list_conversations_endpoint_returns_service_results():
    fake_conversation_service = FakeConversationService()
    client = create_test_client(FakeChatService(), fake_conversation_service)

    response = client.get("/chat/conversations", params={"kb_id": "kb_1"})

    assert response.status_code == 200
    assert fake_conversation_service.calls == [("list_conversations", "kb_1")]
    assert response.json() == fake_conversation_service.conversations


def test_get_conversation_messages_endpoint_returns_service_results():
    fake_conversation_service = FakeConversationService()
    client = create_test_client(FakeChatService(), fake_conversation_service)

    response = client.get("/chat/conversations/conv_1/messages")

    assert response.status_code == 200
    assert fake_conversation_service.calls == [("get_messages", "conv_1")]
    assert response.json() == fake_conversation_service.messages


def test_delete_conversation_endpoint_deletes_with_no_body():
    fake_conversation_service = FakeConversationService()
    client = create_test_client(FakeChatService(), fake_conversation_service)

    response = client.delete("/chat/conversations/conv_1")

    assert response.status_code == 204
    assert response.content == b""
    assert fake_conversation_service.calls == [("delete_conversation", "conv_1")]


def test_delete_conversation_endpoint_maps_missing_conversation_to_404():
    fake_conversation_service = FakeConversationService()
    fake_conversation_service.missing_ids.add("conv_missing")
    client = create_test_client(FakeChatService(), fake_conversation_service)

    response = client.delete("/chat/conversations/conv_missing")

    assert response.status_code == 404
    assert response.json() == {"detail": "Conversation not found"}
