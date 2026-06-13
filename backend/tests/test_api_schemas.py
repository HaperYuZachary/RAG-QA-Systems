import pytest
from pydantic import ValidationError

from app.api.schemas import ChatRequest, DebugSearchRequest


def test_chat_request_accepts_required_fields_and_trims_strings():
    request = ChatRequest(
        kb_id="  kb_1  ",
        question="  年假有几天？  ",
        conversation_id="  conv_1  ",
    )

    assert request.kb_id == "kb_1"
    assert request.question == "年假有几天？"
    assert request.conversation_id == "conv_1"


def test_chat_request_allows_missing_conversation_id():
    request = ChatRequest(kb_id="kb_1", question="继续问")

    assert request.conversation_id is None


@pytest.mark.parametrize(
    "payload",
    [
        {"kb_id": "", "question": "问题"},
        {"kb_id": "kb_1", "question": "   "},
        {"kb_id": "kb_1", "question": "问题", "conversation_id": ""},
    ],
)
def test_chat_request_rejects_blank_strings(payload):
    with pytest.raises(ValidationError):
        ChatRequest(**payload)


def test_debug_search_request_defaults_and_trims_query():
    request = DebugSearchRequest(kb_id=" kb_1 ", query=" 年假 ", top_k=None)

    assert request.kb_id == "kb_1"
    assert request.query == "年假"
    assert request.top_k == 10


@pytest.mark.parametrize("top_k", [1, 10, 50])
def test_debug_search_request_accepts_top_k_range(top_k):
    request = DebugSearchRequest(kb_id="kb_1", query="年假", top_k=top_k)

    assert request.top_k == top_k


@pytest.mark.parametrize(
    "payload",
    [
        {"kb_id": "", "query": "年假"},
        {"kb_id": "kb_1", "query": ""},
        {"kb_id": "kb_1", "query": "年假", "top_k": 0},
        {"kb_id": "kb_1", "query": "年假", "top_k": 51},
    ],
)
def test_debug_search_request_rejects_invalid_payloads(payload):
    with pytest.raises(ValidationError):
        DebugSearchRequest(**payload)
