from fastapi import APIRouter, Depends

from app.api.chat import get_chat_service
from app.api.schemas import DebugSearchRequest, DebugSearchResponse
from app.services.chat_service import ChatService
from app.services.debug_service import DebugService


router = APIRouter()


def get_debug_service(
    chat_service: ChatService = Depends(get_chat_service),
) -> DebugService:
    return DebugService(
        app_settings=chat_service.settings,
        embedder=chat_service.embedder,
        retriever=chat_service.retriever,
        reranker=chat_service.reranker,
    )


@router.post("/debug/search", response_model=DebugSearchResponse)
def debug_search(
    request: DebugSearchRequest,
    debug_service: DebugService = Depends(get_debug_service),
) -> DebugSearchResponse:
    return debug_service.search(
        kb_id=request.kb_id,
        query=request.query,
        top_k=request.top_k,
    )
