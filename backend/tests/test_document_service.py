from contextlib import closing

import pytest

from app.config import Settings
from app.db.sqlite_client import get_connection, init_db
from app.services.document_service import DocumentService, IngestStatus


class FakeEmbedder:
    def __init__(self):
        self.calls = []

    def embed(self, texts):
        self.calls.append(list(texts))
        return [[float(index), 0.0, 1.0] for index, _ in enumerate(texts)]


class FakeVectorStore:
    def __init__(self, fail=False):
        self.fail = fail
        self.add_calls = []
        self.delete_calls = []

    def add(self, kb_id, ids, embeddings, documents, metadatas):
        if self.fail:
            raise RuntimeError("vector write failed")
        self.add_calls.append(
            {
                "kb_id": kb_id,
                "ids": ids,
                "embeddings": embeddings,
                "documents": documents,
                "metadatas": metadatas,
            }
        )

    def delete(self, kb_id, ids):
        self.delete_calls.append({"kb_id": kb_id, "ids": ids})


def seed_kb(settings: Settings, kb_id: str = "kb_1") -> None:
    with closing(get_connection(settings)) as conn, conn:
        conn.execute(
            """
            INSERT INTO knowledge_bases (id, name, created_at, updated_at)
            VALUES (?, ?, ?, ?)
            """,
            (kb_id, "Default", "2026-06-10T00:00:00", "2026-06-10T00:00:00"),
        )


def fetch_document(settings: Settings, document_id: str):
    with closing(get_connection(settings)) as conn, conn:
        return conn.execute(
            "SELECT * FROM documents WHERE id = ?",
            (document_id,),
        ).fetchone()


def test_ingest_document_chunks_embeds_and_writes_sqlite_and_vector_store(tmp_path):
    settings = Settings(data_dir=str(tmp_path), chunk_size=80, chunk_overlap=10)
    init_db(settings)
    seed_kb(settings)
    source = tmp_path / "policy.md"
    source.write_text(
        "# Policy\n"
        "Employees can ask HR questions.\n\n"
        "## Annual Leave\n"
        "Employees with 1-10 years receive 5 days.",
        encoding="utf-8",
    )
    embedder = FakeEmbedder()
    vector_store = FakeVectorStore()
    service = DocumentService(
        settings,
        embedder=embedder,
        vector_store=vector_store,
        id_factory=lambda: "doc_fixed",
    )

    result = service.ingest_document(source, kb_id="kb_1")

    assert result.status is IngestStatus.READY
    assert result.document_id == "doc_fixed"
    assert result.chunk_count == 2
    assert result.duplicate is False
    assert (tmp_path / "documents" / "doc_fixed.md").read_text(encoding="utf-8")
    assert embedder.calls == [
        [
            "# Policy\nEmployees can ask HR questions.",
            "## Annual Leave\nEmployees with 1-10 years receive 5 days.",
        ]
    ]
    assert len(vector_store.add_calls) == 1
    call = vector_store.add_calls[0]
    assert call["kb_id"] == "kb_1"
    assert call["ids"] == ["doc_fixed_chunk_0", "doc_fixed_chunk_1"]
    assert call["embeddings"] == [[0.0, 0.0, 1.0], [1.0, 0.0, 1.0]]
    assert call["metadatas"][0]["document_id"] == "doc_fixed"
    assert call["metadatas"][0]["filename"] == "policy.md"
    assert "page" not in call["metadatas"][0]

    row = fetch_document(settings, "doc_fixed")
    assert row["status"] == "ready"
    assert row["chunk_count"] == 2
    assert row["file_hash"]
    assert row["error_msg"] is None


def test_ingest_duplicate_document_skips_embedding_and_vector_write(tmp_path):
    settings = Settings(data_dir=str(tmp_path))
    init_db(settings)
    seed_kb(settings)
    source = tmp_path / "policy.md"
    source.write_text("# Policy\nSame content.", encoding="utf-8")
    embedder = FakeEmbedder()
    vector_store = FakeVectorStore()
    ids = iter(["doc_first", "doc_second"])
    service = DocumentService(
        settings,
        embedder=embedder,
        vector_store=vector_store,
        id_factory=lambda: next(ids),
    )

    first = service.ingest_document(source, kb_id="kb_1")
    duplicate = service.ingest_document(source, kb_id="kb_1")

    assert first.document_id == "doc_first"
    assert duplicate.document_id == "doc_first"
    assert duplicate.duplicate is True
    assert duplicate.status is IngestStatus.READY
    assert len(embedder.calls) == 1
    assert len(vector_store.add_calls) == 1


def test_ingest_failure_marks_document_error_and_skips_vector_write(tmp_path):
    settings = Settings(data_dir=str(tmp_path))
    init_db(settings)
    seed_kb(settings)
    source = tmp_path / "broken.md"
    source.write_text("broken content", encoding="utf-8")
    vector_store = FakeVectorStore()

    def failing_parser(path, file_type):
        raise ValueError("parser failed")

    service = DocumentService(
        settings,
        embedder=FakeEmbedder(),
        vector_store=vector_store,
        parser=failing_parser,
        id_factory=lambda: "doc_error",
    )

    result = service.ingest_document(source, kb_id="kb_1")

    assert result.status is IngestStatus.ERROR
    assert result.document_id == "doc_error"
    assert result.chunk_count == 0
    assert "parser failed" in (result.error_msg or "")
    assert vector_store.add_calls == []
    row = fetch_document(settings, "doc_error")
    assert row["status"] == "error"
    assert row["chunk_count"] == 0
    assert "parser failed" in row["error_msg"]


def test_vector_write_failure_marks_document_error(tmp_path):
    settings = Settings(data_dir=str(tmp_path))
    init_db(settings)
    seed_kb(settings)
    source = tmp_path / "policy.md"
    source.write_text("# Policy\nUseful content.", encoding="utf-8")
    service = DocumentService(
        settings,
        embedder=FakeEmbedder(),
        vector_store=FakeVectorStore(fail=True),
        id_factory=lambda: "doc_vector_error",
    )

    result = service.ingest_document(source, kb_id="kb_1")

    assert result.status is IngestStatus.ERROR
    assert "vector write failed" in (result.error_msg or "")
    row = fetch_document(settings, "doc_vector_error")
    assert row["status"] == "error"
    assert row["chunk_count"] == 0


def test_failure_after_vector_write_rolls_back_chunks(tmp_path):
    settings = Settings(data_dir=str(tmp_path))
    init_db(settings)
    seed_kb(settings)
    source = tmp_path / "policy.md"
    source.write_text("# Policy\nUseful content.", encoding="utf-8")
    vector_store = FakeVectorStore()

    class FailingReadyDocumentService(DocumentService):
        def _mark_ready(self, document_id: str, chunk_count: int) -> None:
            raise RuntimeError("sqlite update failed")

    service = FailingReadyDocumentService(
        settings,
        embedder=FakeEmbedder(),
        vector_store=vector_store,
        id_factory=lambda: "doc_cleanup",
    )

    result = service.ingest_document(source, kb_id="kb_1")

    assert result.status is IngestStatus.ERROR
    assert "sqlite update failed" in (result.error_msg or "")
    assert vector_store.add_calls[0]["ids"] == ["doc_cleanup_chunk_0"]
    assert vector_store.delete_calls == [
        {"kb_id": "kb_1", "ids": ["doc_cleanup_chunk_0"]}
    ]
    row = fetch_document(settings, "doc_cleanup")
    assert row["status"] == "error"


def test_retry_purges_possible_orphan_chunks_before_rewrite(tmp_path):
    settings = Settings(data_dir=str(tmp_path))
    init_db(settings)
    seed_kb(settings)
    source = tmp_path / "policy.md"
    source.write_text("# Policy\nUseful content.", encoding="utf-8")

    def failing_parser(path, file_type):
        raise ValueError("parser failed")

    # 第一次失败 → documents 行以 status=error 留存
    first_service = DocumentService(
        settings,
        embedder=FakeEmbedder(),
        vector_store=FakeVectorStore(),
        parser=failing_parser,
        id_factory=lambda: "doc_retry",
    )
    assert first_service.ingest_document(source, kb_id="kb_1").status is IngestStatus.ERROR

    # 重试 → add 之前应先按相同 chunk_id 删一遍，做幂等清理
    vector_store = FakeVectorStore()
    retry_service = DocumentService(
        settings,
        embedder=FakeEmbedder(),
        vector_store=vector_store,
        id_factory=lambda: "unused",
    )
    result = retry_service.ingest_document(source, kb_id="kb_1")

    assert result.status is IngestStatus.READY
    assert vector_store.delete_calls == [
        {"kb_id": "kb_1", "ids": ["doc_retry_chunk_0"]}
    ]
    assert len(vector_store.add_calls) == 1


def test_failed_document_can_be_retried_with_same_hash(tmp_path):
    settings = Settings(data_dir=str(tmp_path))
    init_db(settings)
    seed_kb(settings)
    source = tmp_path / "policy.md"
    source.write_text("# Policy\nUseful content.", encoding="utf-8")

    def failing_parser(path, file_type):
        raise ValueError("parser failed")

    first_service = DocumentService(
        settings,
        embedder=FakeEmbedder(),
        vector_store=FakeVectorStore(),
        parser=failing_parser,
        id_factory=lambda: "doc_retry",
    )
    first = first_service.ingest_document(source, kb_id="kb_1")
    assert first.status is IngestStatus.ERROR

    embedder = FakeEmbedder()
    vector_store = FakeVectorStore()
    retry_service = DocumentService(
        settings,
        embedder=embedder,
        vector_store=vector_store,
        id_factory=lambda: "doc_should_not_be_used",
    )
    retry = retry_service.ingest_document(source, kb_id="kb_1")

    assert retry.status is IngestStatus.READY
    assert retry.document_id == "doc_retry"
    assert retry.chunk_count == 1
    assert len(embedder.calls) == 1
    assert len(vector_store.add_calls) == 1
    row = fetch_document(settings, "doc_retry")
    assert row["status"] == "ready"
    assert row["error_msg"] is None
