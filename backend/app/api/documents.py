import shutil
import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from app.api.chat import get_chat_service
from app.api.schemas import (
    DocumentResponse,
    DocumentStatusResponse,
    UploadResponse,
    UploadResultItem,
)
from app.services.chat_service import ChatService
from app.services.document_service import DocumentNotFoundError, DocumentService


router = APIRouter()


def get_document_service(
    chat_service: ChatService = Depends(get_chat_service),
) -> DocumentService:
    # 复用单例 ChatService 的 embedder 与 vector_store，全进程仍只有一个 Chroma 客户端
    return DocumentService(
        app_settings=chat_service.settings,
        embedder=chat_service.embedder,
        vector_store=chat_service.retriever.vector_store,
    )


@router.post("/upload", response_model=UploadResponse, status_code=201)
def upload_documents(
    kb_id: str = Form(...),
    files: list[UploadFile] = File(...),
    service: DocumentService = Depends(get_document_service),
):
    documents = [_ingest_one(service, upload, kb_id) for upload in files]
    return UploadResponse(documents=documents)


@router.get("/docs", response_model=list[DocumentResponse])
def list_documents(
    kb_id: str,
    service: DocumentService = Depends(get_document_service),
):
    return service.list_documents(kb_id)


@router.get("/docs/{document_id}", response_model=DocumentResponse)
def get_document(
    document_id: str,
    service: DocumentService = Depends(get_document_service),
):
    try:
        return service.get_document(document_id)
    except DocumentNotFoundError:
        raise HTTPException(status_code=404, detail="Document not found")


@router.get("/docs/{document_id}/status", response_model=DocumentStatusResponse)
def get_document_status(
    document_id: str,
    service: DocumentService = Depends(get_document_service),
):
    try:
        record = service.get_document(document_id)
    except DocumentNotFoundError:
        raise HTTPException(status_code=404, detail="Document not found")
    return DocumentStatusResponse(
        id=record.id,
        status=record.status,
        chunk_count=record.chunk_count,
        error_msg=record.error_msg,
    )


@router.delete("/docs/{document_id}", response_model=DocumentResponse)
def delete_document(
    document_id: str,
    service: DocumentService = Depends(get_document_service),
):
    try:
        return service.delete_document(document_id)
    except DocumentNotFoundError:
        raise HTTPException(status_code=404, detail="Document not found")


def _ingest_one(
    service: DocumentService,
    upload: UploadFile,
    kb_id: str,
) -> UploadResultItem:
    filename = upload.filename or "upload"
    tmp_path: str | None = None
    try:
        suffix = Path(filename).suffix
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            shutil.copyfileobj(upload.file, tmp)
            tmp_path = tmp.name

        result = service.ingest_document(
            tmp_path,
            kb_id=kb_id,
            original_filename=filename,
        )
        return UploadResultItem(
            document_id=result.document_id,
            filename=filename,
            status=result.status.value,
            chunk_count=result.chunk_count,
            duplicate=result.duplicate,
            error_msg=result.error_msg,
        )
    except Exception as exc:  # 单个文件失败不影响其余文件，逐条返回错误
        return UploadResultItem(
            document_id="",
            filename=filename,
            status="error",
            chunk_count=0,
            duplicate=False,
            error_msg=str(exc),
        )
    finally:
        if tmp_path:
            Path(tmp_path).unlink(missing_ok=True)
