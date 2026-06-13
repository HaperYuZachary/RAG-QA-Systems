import json

from fastapi import FastAPI
from fastapi.testclient import TestClient

import app.api.chat as chat_module
from app.api.chat import get_chat_service, router
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


def create_test_client(fake_service):
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_chat_service] = lambda: fake_service
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
