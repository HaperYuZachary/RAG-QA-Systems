from contextlib import closing

import pytest

from app.config import Settings
from app.db.sqlite_client import get_connection, init_db
from app.services.kb_service import (
    KBService,
    KnowledgeBase,
    KnowledgeBaseNotFoundError,
)


class FakeVectorStore:
    def __init__(self):
        self.deleted_collections = []

    def delete_collection(self, kb_id):
        self.deleted_collections.append(kb_id)


class FixedIds:
    def __init__(self, values):
        self.values = iter(values)

    def __call__(self):
        return next(self.values)


def insert_document(settings, doc_id, kb_id):
    with closing(get_connection(settings)) as conn, conn:
        conn.execute(
            """
            INSERT INTO documents
                (id, kb_id, filename, file_type, file_size, file_hash, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (doc_id, kb_id, "doc.md", "md", 10, f"hash_{doc_id}", "2026-06-11T00:00:00"),
        )


def test_create_and_get_knowledge_base(tmp_path):
    settings = Settings(data_dir=str(tmp_path))
    init_db(settings)
    service = KBService(settings, id_factory=lambda: "kb_fixed")

    created = service.create(name="HR 制度", description="人事相关文档")

    assert created == KnowledgeBase(
        id="kb_fixed",
        name="HR 制度",
        description="人事相关文档",
        created_at=created.created_at,
        updated_at=created.updated_at,
        document_count=0,
    )
    assert service.get("kb_fixed").name == "HR 制度"


def test_list_includes_document_count(tmp_path):
    settings = Settings(data_dir=str(tmp_path))
    init_db(settings)
    service = KBService(settings, id_factory=FixedIds(["kb_1", "kb_2"]))

    service.create(name="第一个")
    service.create(name="第二个")
    insert_document(settings, "doc_1", "kb_1")
    insert_document(settings, "doc_2", "kb_1")

    by_id = {kb.id: kb for kb in service.list()}

    assert by_id["kb_1"].document_count == 2
    assert by_id["kb_2"].document_count == 0


def test_get_missing_raises(tmp_path):
    settings = Settings(data_dir=str(tmp_path))
    init_db(settings)
    service = KBService(settings)

    with pytest.raises(KnowledgeBaseNotFoundError):
        service.get("kb_missing")


def test_update_applies_partial_changes(tmp_path):
    settings = Settings(data_dir=str(tmp_path))
    init_db(settings)
    service = KBService(settings, id_factory=lambda: "kb_1")
    service.create(name="旧名字", description="旧描述")

    updated = service.update("kb_1", name="新名字")

    assert updated.name == "新名字"
    assert updated.description == "旧描述"  # 未传 description，保持不变


def test_delete_cascades_documents_and_drops_vector_collection(tmp_path):
    settings = Settings(data_dir=str(tmp_path))
    init_db(settings)
    vector_store = FakeVectorStore()
    service = KBService(settings, id_factory=lambda: "kb_1", vector_store=vector_store)
    service.create(name="待删除")
    insert_document(settings, "doc_1", "kb_1")

    deleted = service.delete("kb_1")

    assert deleted.id == "kb_1"
    assert vector_store.deleted_collections == ["kb_1"]
    with closing(get_connection(settings)) as conn, conn:
        remaining_docs = conn.execute(
            "SELECT COUNT(*) AS c FROM documents WHERE kb_id = ?", ("kb_1",)
        ).fetchone()["c"]
    assert remaining_docs == 0  # FK ON DELETE CASCADE 清掉了关联文档


def test_delete_missing_raises(tmp_path):
    settings = Settings(data_dir=str(tmp_path))
    init_db(settings)
    service = KBService(settings)

    with pytest.raises(KnowledgeBaseNotFoundError):
        service.delete("kb_missing")
