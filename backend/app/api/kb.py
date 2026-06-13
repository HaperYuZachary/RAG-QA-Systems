from fastapi import APIRouter, Depends, HTTPException

from app.api.chat import get_chat_service
from app.api.schemas import (
    KnowledgeBaseCreateRequest,
    KnowledgeBaseResponse,
    KnowledgeBaseUpdateRequest,
)
from app.services.chat_service import ChatService
from app.services.kb_service import KBService, KnowledgeBaseNotFoundError


router = APIRouter()


def get_kb_service(
    chat_service: ChatService = Depends(get_chat_service),
) -> KBService:
    # 复用单例 ChatService 的 VectorStore，全进程仍只有一个 Chroma 客户端
    return KBService(
        app_settings=chat_service.settings,
        vector_store=chat_service.retriever.vector_store,
    )


@router.get("/knowledge-bases", response_model=list[KnowledgeBaseResponse])
def list_knowledge_bases(kb_service: KBService = Depends(get_kb_service)):
    return kb_service.list()


@router.post(
    "/knowledge-bases",
    response_model=KnowledgeBaseResponse,
    status_code=201,
)
def create_knowledge_base(
    request: KnowledgeBaseCreateRequest,
    kb_service: KBService = Depends(get_kb_service),
):
    return kb_service.create(name=request.name, description=request.description)


@router.patch(
    "/knowledge-bases/{kb_id}",
    response_model=KnowledgeBaseResponse,
)
def update_knowledge_base(
    kb_id: str,
    request: KnowledgeBaseUpdateRequest,
    kb_service: KBService = Depends(get_kb_service),
):
    try:
        return kb_service.update(
            kb_id,
            name=request.name,
            description=request.description,
        )
    except KnowledgeBaseNotFoundError:
        raise HTTPException(status_code=404, detail="Knowledge base not found")


@router.delete(
    "/knowledge-bases/{kb_id}",
    response_model=KnowledgeBaseResponse,
)
def delete_knowledge_base(
    kb_id: str,
    kb_service: KBService = Depends(get_kb_service),
):
    try:
        return kb_service.delete(kb_id)
    except KnowledgeBaseNotFoundError:
        raise HTTPException(status_code=404, detail="Knowledge base not found")
