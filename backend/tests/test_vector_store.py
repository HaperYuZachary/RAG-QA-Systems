from app.config import Settings
from app.core.vector_store import VectorStore, get_vector_db_path


class FakeCollection:
    def __init__(self):
        self.ids = []
        self.documents = []
        self.metadatas = []
        self.embeddings = []

    def add(self, ids, embeddings, documents, metadatas):
        self.ids.extend(ids)
        self.embeddings.extend(embeddings)
        self.documents.extend(documents)
        self.metadatas.extend(metadatas)

    def delete(self, ids):
        for chunk_id in ids:
            if chunk_id not in self.ids:
                continue
            index = self.ids.index(chunk_id)
            del self.ids[index]
            del self.embeddings[index]
            del self.documents[index]
            del self.metadatas[index]

    def get(self, include):
        return {
            "ids": list(self.ids),
            "documents": list(self.documents),
            "metadatas": list(self.metadatas),
        }

    def query(self, query_embeddings, n_results, include):
        query_embedding = query_embeddings[0]
        scored = sorted(
            enumerate(self.embeddings),
            key=lambda item: sum(
                a * b for a, b in zip(query_embedding, item[1], strict=True)
            ),
            reverse=True,
        )[:n_results]
        indexes = [index for index, _ in scored]
        return {
            "ids": [[self.ids[index] for index in indexes]],
            "documents": [[self.documents[index] for index in indexes]],
            "metadatas": [[self.metadatas[index] for index in indexes]],
            "distances": [[0.0 for _ in indexes]],
        }


class FakeClient:
    def __init__(self):
        self.collections = {}

    def get_or_create_collection(self, name, metadata=None):
        self.last_metadata = metadata
        self.collections.setdefault(name, FakeCollection())
        return self.collections[name]


def test_vector_db_path_uses_configured_data_dir(tmp_path):
    settings = Settings(data_dir=str(tmp_path))

    assert get_vector_db_path(settings) == tmp_path / "vector_db"


def test_vector_store_adds_and_queries_chunks(tmp_path):
    settings = Settings(data_dir=str(tmp_path))
    client = FakeClient()
    store = VectorStore(settings, client=client)

    store.add(
        kb_id="kb_1",
        ids=["chunk_1", "chunk_2"],
        embeddings=[[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]],
        documents=["semantic chunk text", "other content"],
        metadatas=[
            {"document_id": "doc_1", "chunk_index": 0},
            {"document_id": "doc_2", "chunk_index": 1},
        ],
    )

    result = store.query("kb_1", query_embedding=[1.0, 0.0, 0.0], top_k=1)

    assert "kb_kb_1" in client.collections
    assert client.last_metadata == {"hnsw:space": "cosine"}
    assert result["ids"][0] == ["chunk_1"]
    assert result["documents"][0] == ["semantic chunk text"]
    assert result["metadatas"][0][0]["document_id"] == "doc_1"


def test_vector_store_deletes_chunks(tmp_path):
    settings = Settings(data_dir=str(tmp_path))
    client = FakeClient()
    store = VectorStore(settings, client=client)
    store.add(
        kb_id="kb_1",
        ids=["chunk_1", "chunk_2"],
        embeddings=[[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]],
        documents=["first", "second"],
        metadatas=[
            {"document_id": "doc_1", "chunk_index": 0},
            {"document_id": "doc_1", "chunk_index": 1},
        ],
    )

    store.delete(kb_id="kb_1", ids=["chunk_1"])

    collection = client.collections["kb_kb_1"]
    assert collection.ids == ["chunk_2"]
    assert collection.documents == ["second"]


def test_vector_store_lists_chunks_for_keyword_search(tmp_path):
    settings = Settings(data_dir=str(tmp_path))
    client = FakeClient()
    store = VectorStore(settings, client=client)
    store.add(
        kb_id="kb_1",
        ids=["chunk_1", "chunk_2"],
        embeddings=[[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]],
        documents=["first text", "second text"],
        metadatas=[
            {"document_id": "doc_1", "chunk_index": 0},
            {"document_id": "doc_1", "chunk_index": 1},
        ],
    )

    chunks = store.list_chunks("kb_1")

    assert chunks == [
        {
            "id": "chunk_1",
            "text": "first text",
            "metadata": {"document_id": "doc_1", "chunk_index": 0},
        },
        {
            "id": "chunk_2",
            "text": "second text",
            "metadata": {"document_id": "doc_1", "chunk_index": 1},
        },
    ]


def test_vector_store_persists_with_real_chroma_client(tmp_path):
    settings = Settings(data_dir=str(tmp_path))
    store = VectorStore(settings)

    store.add(
        kb_id="kb_real",
        ids=["chunk_real_1"],
        embeddings=[[0.25, 0.75, 0.0]],
        documents=["persisted chunk text"],
        metadatas=[{"document_id": "doc_real", "chunk_index": 0}],
    )

    reloaded_store = VectorStore(settings)
    result = reloaded_store.query(
        "kb_real",
        query_embedding=[0.25, 0.75, 0.0],
        top_k=1,
    )

    assert result["ids"][0] == ["chunk_real_1"]
    assert result["documents"][0] == ["persisted chunk text"]
    assert reloaded_store.list_chunks("kb_real") == [
        {
            "id": "chunk_real_1",
            "text": "persisted chunk text",
            "metadata": {"document_id": "doc_real", "chunk_index": 0},
        }
    ]
    assert (tmp_path / "vector_db").exists()
