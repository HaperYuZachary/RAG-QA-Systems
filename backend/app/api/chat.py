import json
from collections.abc import Iterable

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.api.schemas import ChatRequest
from app.services.chat_service import ChatService, ChatStreamEvent


router = APIRouter()

# 进程级单例：ChatService 内部持有 Chroma 客户端与（惰性加载的）Reranker 模型，
# 这些都是“每路径/每进程只该有一个”的重资源。按请求重建会导致 Chroma 多实例冲突、
# Reranker 模型反复加载。这里只构建一次、所有请求复用。
_chat_service: ChatService | None = None


def get_chat_service() -> ChatService:
    global _chat_service
    if _chat_service is None:
        _chat_service = ChatService()
    return _chat_service


@router.post("/chat")
def chat(
    request: ChatRequest,
    chat_service: ChatService = Depends(get_chat_service),
):
    return StreamingResponse(
        _sse_stream(
            chat_service.stream_chat(
                kb_id=request.kb_id,
                question=request.question,
                conversation_id=request.conversation_id,
            )
        ),
        media_type="text/event-stream",
    )


def _sse_stream(events: Iterable[ChatStreamEvent]):
    try:
        for event in events:
            yield _format_sse_event(event)
    except Exception as error:
        yield _format_sse_event(
            ChatStreamEvent(
                event="error",
                data={
                    "message": str(error),
                    "type": error.__class__.__name__,
                },
            )
        )


def _format_sse_event(event: ChatStreamEvent) -> str:
    return (
        f"event: {event.event}\n"
        f"data: {json.dumps(event.data, ensure_ascii=False)}\n\n"
    )
