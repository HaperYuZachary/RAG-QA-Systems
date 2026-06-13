from contextlib import closing

import pytest

from app.config import Settings
from app.db.sqlite_client import get_connection, init_db
from app.services.document_service import DocumentNotFoundError, DocumentService


class FakeVectorStore:
    def __init__(self):
        self.deleted = []

    def delete_document(self, kb_id, document_id):
        self.deleted.append((kb_id, document_id))


def make_service(settings, vector_store=None):
    return DocumentService(
        settings,
        embedder=object(),
        vector_store=vector_store or FakeVectorStore(),
    )


def seed_kb(settings, kb_id="kb_1"):
    with closing(get_connection(settings)) as conn, conn:
        conn.execute(
            """
            INSERT INTO knowledge_bases (id, name, created_at, updated_at)
            VALUES (?, ?, ?, ?)
            """,
            (kb_id, "KB", "2026-06-11T00:00:00", "2026-06-11T00:00:00"),
        )


def insert_doc(settings, doc_id, kb_id="kb_1", file_type="md", created_at="2026-06-11T00:00:00"):
    with closing(get_connection(settings)) as conn, conn:
        conn.execute(
            """
            INSERT INTO documents
                (id, kb_id, filename, file_type, file_size, file_hash,
                 chunk_count, status, error_msg, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                doc_id, kb_id, f"{doc_id}.{file_type}", file_type, 100,
                f"hash_{doc_id}", 3, "ready", None, created_at,
            ),
        )


def test_list_documents_for_kb_sorted_newest_first(tmp_path):
    settings = Settings(data_dir=str(tmp_path))
    init_db(settings)
    seed_kb(settings)
    insert_doc(settings, "doc_1", created_at="2026-06-11T00:00:01")
    insert_doc(settings, "doc_2", created_at="2026-06-11T00:00:02")
    service = make_service(settings)

    docs = service.list_documents("kb_1")

    assert [d.id for d in docs] == ["doc_2", "doc_1"]
    assert docs[0].chunk_count == 3
    assert docs[0].status == "ready"


def test_get_document_and_not_found(tmp_path):
    settings = Settings(data_dir=str(tmp_path))
    init_db(settings)
    seed_kb(settings)
    insert_doc(settings, "doc_1")
    service = make_service(settings)

    assert service.get_document("doc_1").filename == "doc_1.md"
    with pytest.raises(DocumentNotFoundError):
        service.get_document("missing")


def test_delete_document_removes_row_file_and_vectors(tmp_path):
    settings = Settings(data_dir=str(tmp_path))
    init_db(settings)
    seed_kb(settings)
    insert_doc(settings, "doc_1", file_type="md")
    vector_store = FakeVectorStore()
    service = make_service(settings, vector_store=vector_store)

    # 造一个落盘原文件
    stored = service._documents_dir() / "doc_1.md"
    stored.write_text("content", encoding="utf-8")

    deleted = service.delete_document("doc_1")

    assert deleted.id == "doc_1"
    assert vector_store.deleted == [("kb_1", "doc_1")]
    assert not stored.exists()
    with closing(get_connection(settings)) as conn, conn:
        remaining = conn.execute(
            "SELECT COUNT(*) AS c FROM documents WHERE id = ?", ("doc_1",)
        ).fetchone()["c"]
    assert remaining == 0


def test_delete_missing_document_raises(tmp_path):
    settings = Settings(data_dir=str(tmp_path))
    init_db(settings)
    service = make_service(settings)

    with pytest.raises(DocumentNotFoundError):
        service.delete_document("missing")
