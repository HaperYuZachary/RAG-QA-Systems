from contextlib import closing
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
import shutil
from typing import Any
from uuid import uuid4

from app.config import Settings, settings
from app.core.chunker import chunk_text
from app.core.embedder import Embedder
from app.core.parser import parse
from app.core.vector_store import VectorStore
from app.db.sqlite_client import get_connection
from app.utils.file_utils import calculate_sha256, detect_file_type


class IngestStatus(Enum):
    READY = "ready"
    ERROR = "error"


@dataclass(frozen=True)
class IngestResult:
    document_id: str
    status: IngestStatus
    chunk_count: int
    duplicate: bool = False
    error_msg: str | None = None


@dataclass(frozen=True)
class ExistingDocument:
    document_id: str
    status: str
    chunk_count: int


@dataclass(frozen=True)
class DocumentRecord:
    id: str
    kb_id: str
    filename: str
    file_type: str
    file_size: int
    file_hash: str
    chunk_count: int
    status: str
    error_msg: str | None
    created_at: str


class DocumentNotFoundError(Exception):
    pass


class DocumentService:
    def __init__(
        self,
        app_settings: Settings | None = None,
        embedder=None,
        vector_store=None,
        parser=parse,
        chunker=chunk_text,
        id_factory=None,
    ):
        self.settings = app_settings or settings
        self.embedder = embedder or Embedder(self.settings)
        self.vector_store = vector_store or VectorStore(self.settings)
        self.parser = parser
        self.chunker = chunker
        self.id_factory = id_factory or (lambda: f"doc_{uuid4()}")

    def ingest_document(
        self,
        source_path: str | Path,
        kb_id: str,
        original_filename: str | None = None,
    ) -> IngestResult:
        source = Path(source_path)
        filename = original_filename or source.name
        file_type = detect_file_type(filename)
        file_hash = calculate_sha256(source)
        file_size = source.stat().st_size

        existing_document = self._find_existing_document(kb_id, file_hash)
        if existing_document and existing_document.status == IngestStatus.READY.value:
            return IngestResult(
                document_id=existing_document.document_id,
                status=IngestStatus.READY,
                chunk_count=existing_document.chunk_count,
                duplicate=True,
            )

        document_id = (
            existing_document.document_id
            if existing_document
            else self.id_factory()
        )
        chunk_ids: list[str] = []
        try:
            self._save_processing_document(
                document_id=document_id,
                kb_id=kb_id,
                filename=filename,
                file_type=file_type,
                file_size=file_size,
                file_hash=file_hash,
                exists=existing_document is not None,
            )
            stored_path = self._store_source_file(source, document_id, file_type)
            parsed_pages = self.parser(stored_path, file_type)
            chunks = []
            for parsed_page in parsed_pages:
                page_chunks = self.chunker(
                    parsed_page.text,
                    file_type=file_type,
                    chunk_size=self.settings.chunk_size,
                    overlap=self.settings.chunk_overlap,
                )
                for chunk in page_chunks:
                    chunks.append((parsed_page.page, chunk))

            if not chunks:
                raise ValueError("No text chunks generated from document")

            texts = [chunk.text for _, chunk in chunks]
            embeddings = self.embedder.embed(texts)
            if len(embeddings) != len(chunks):
                raise ValueError("Embedding count does not match chunk count")

            chunk_ids = [
                f"{document_id}_chunk_{index}"
                for index in range(len(chunks))
            ]
            metadatas = [
                self._build_metadata(
                    document_id=document_id,
                    kb_id=kb_id,
                    filename=filename,
                    file_type=file_type,
                    index=index,
                    page=page,
                    chunk=chunk,
                )
                for index, (page, chunk) in enumerate(chunks)
            ]
            if existing_document is not None:
                # 幂等护栏：重试已存在文档时，先清掉上次可能残留的同 id 旧分块
                # （例如上次写入向量库后进程被强杀、来不及回滚），避免 Chroma id 冲突
                self.vector_store.delete(kb_id=kb_id, ids=chunk_ids)
            self.vector_store.add(
                kb_id=kb_id,
                ids=chunk_ids,
                embeddings=embeddings,
                documents=texts,
                metadatas=metadatas,
            )
            self._mark_ready(document_id, len(chunks))
            return IngestResult(
                document_id=document_id,
                status=IngestStatus.READY,
                chunk_count=len(chunks),
            )
        except Exception as exc:
            self._rollback_vector_chunks(kb_id, chunk_ids)
            self._mark_error(document_id, str(exc))
            return IngestResult(
                document_id=document_id,
                status=IngestStatus.ERROR,
                chunk_count=0,
                error_msg=str(exc),
            )

    def list_documents(self, kb_id: str) -> list[DocumentRecord]:
        with closing(get_connection(self.settings)) as conn, conn:
            rows = conn.execute(
                """
                SELECT id, kb_id, filename, file_type, file_size, file_hash,
                       chunk_count, status, error_msg, created_at
                FROM documents
                WHERE kb_id = ?
                ORDER BY created_at DESC, id DESC
                """,
                (kb_id,),
            ).fetchall()
        return [_row_to_document(row) for row in rows]

    def get_document(self, document_id: str) -> DocumentRecord:
        with closing(get_connection(self.settings)) as conn, conn:
            row = conn.execute(
                """
                SELECT id, kb_id, filename, file_type, file_size, file_hash,
                       chunk_count, status, error_msg, created_at
                FROM documents
                WHERE id = ?
                """,
                (document_id,),
            ).fetchone()
        if row is None:
            raise DocumentNotFoundError(document_id)
        return _row_to_document(row)

    def delete_document(self, document_id: str) -> DocumentRecord:
        record = self.get_document(document_id)  # 不存在则抛 DocumentNotFoundError
        # 1) 删向量分块  2) 删落盘原文件  3) 删元数据行
        self.vector_store.delete_document(record.kb_id, document_id)
        (self._documents_dir() / f"{document_id}.{record.file_type}").unlink(
            missing_ok=True
        )
        with closing(get_connection(self.settings)) as conn, conn:
            conn.execute("DELETE FROM documents WHERE id = ?", (document_id,))
        return record

    def _documents_dir(self) -> Path:
        path = Path(self.settings.data_dir) / "documents"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _store_source_file(self, source: Path, document_id: str, file_type: str) -> Path:
        destination = self._documents_dir() / f"{document_id}.{file_type}"
        shutil.copy2(source, destination)
        return destination

    def _find_existing_document(
        self,
        kb_id: str,
        file_hash: str,
    ) -> ExistingDocument | None:
        with closing(get_connection(self.settings)) as conn, conn:
            row = conn.execute(
                """
                SELECT id, status, chunk_count FROM documents
                WHERE kb_id = ? AND file_hash = ?
                """,
                (kb_id, file_hash),
            ).fetchone()
            if not row:
                return None
            return ExistingDocument(
                document_id=row["id"],
                status=row["status"],
                chunk_count=int(row["chunk_count"]),
            )

    def _save_processing_document(
        self,
        document_id: str,
        kb_id: str,
        filename: str,
        file_type: str,
        file_size: int,
        file_hash: str,
        exists: bool,
    ) -> None:
        with closing(get_connection(self.settings)) as conn, conn:
            if exists:
                conn.execute(
                    """
                    UPDATE documents
                    SET filename = ?, file_type = ?, file_size = ?, file_hash = ?,
                        chunk_count = 0, status = 'processing', error_msg = NULL
                    WHERE id = ?
                    """,
                    (filename, file_type, file_size, file_hash, document_id),
                )
            else:
                conn.execute(
                    """
                    INSERT INTO documents (
                        id, kb_id, filename, file_type, file_size, file_hash,
                        chunk_count, status, error_msg, created_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, 0, 'processing', NULL, ?)
                    """,
                    (
                        document_id,
                        kb_id,
                        filename,
                        file_type,
                        file_size,
                        file_hash,
                        _utc_now(),
                    ),
                )

    def _mark_ready(self, document_id: str, chunk_count: int) -> None:
        with closing(get_connection(self.settings)) as conn, conn:
            conn.execute(
                """
                UPDATE documents
                SET status = 'ready', chunk_count = ?, error_msg = NULL
                WHERE id = ?
                """,
                (chunk_count, document_id),
            )

    def _mark_error(self, document_id: str, error_msg: str) -> None:
        with closing(get_connection(self.settings)) as conn, conn:
            conn.execute(
                """
                UPDATE documents
                SET status = 'error', chunk_count = 0, error_msg = ?
                WHERE id = ?
                """,
                (error_msg, document_id),
            )

    def _rollback_vector_chunks(self, kb_id: str, chunk_ids: list[str]) -> None:
        if not chunk_ids or not hasattr(self.vector_store, "delete"):
            return

        try:
            self.vector_store.delete(kb_id=kb_id, ids=chunk_ids)
        except Exception:
            pass

    def _build_metadata(
        self,
        document_id: str,
        kb_id: str,
        filename: str,
        file_type: str,
        index: int,
        page: int | None,
        chunk,
    ) -> dict[str, str | int | float | bool]:
        metadata: dict[str, Any] = {
            "document_id": document_id,
            "kb_id": kb_id,
            "filename": filename,
            "file_type": file_type,
            "chunk_index": index,
            "start_pos": chunk.start_pos,
            "end_pos": chunk.end_pos,
            **chunk.metadata,
        }
        if page is not None:
            metadata["page"] = page
        return _chroma_safe_metadata(metadata)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _row_to_document(row) -> DocumentRecord:
    return DocumentRecord(
        id=row["id"],
        kb_id=row["kb_id"],
        filename=row["filename"],
        file_type=row["file_type"],
        file_size=int(row["file_size"]),
        file_hash=row["file_hash"],
        chunk_count=int(row["chunk_count"]),
        status=row["status"],
        error_msg=row["error_msg"],
        created_at=row["created_at"],
    )


def _chroma_safe_metadata(
    metadata: dict[str, Any],
) -> dict[str, str | int | float | bool]:
    safe_metadata: dict[str, str | int | float | bool] = {}
    for key, value in metadata.items():
        if value is None:
            continue
        if isinstance(value, str | int | float | bool):
            safe_metadata[key] = value
        else:
            safe_metadata[key] = str(value)
    return safe_metadata
