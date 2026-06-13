from pathlib import Path

from app.config import Settings, settings


def get_vector_db_path(app_settings: Settings | None = None) -> Path:
    active_settings = app_settings or settings
    return Path(active_settings.data_dir) / "vector_db"


class VectorStore:
    def __init__(self, app_settings: Settings | None = None, client=None):
        self.settings = app_settings or settings
        self.path = get_vector_db_path(self.settings)
        self.path.mkdir(parents=True, exist_ok=True)
        self.client = client or self._create_client()

    def _create_client(self):
        import chromadb
        from chromadb.config import Settings as ChromaSettings

        return chromadb.PersistentClient(
            path=str(self.path),
            settings=ChromaSettings(anonymized_telemetry=False),
        )

    def get_collection(self, kb_id: str):
        # 必须在创建时指定 cosine：Chroma 默认 L2，且度量一旦建好不可更改
        return self.client.get_or_create_collection(
            name=f"kb_{kb_id}",
            metadata={"hnsw:space": "cosine"},
        )

    def add(
        self,
        kb_id: str,
        ids: list[str],
        embeddings: list[list[float]],
        documents: list[str],
        metadatas: list[dict],
    ) -> None:
        collection = self.get_collection(kb_id)
        collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
        )

    def delete(self, kb_id: str, ids: list[str]) -> None:
        if not ids:
            return

        collection = self.get_collection(kb_id)
        collection.delete(ids=ids)

    def delete_collection(self, kb_id: str) -> None:
        try:
            self.client.delete_collection(name=f"kb_{kb_id}")
        except Exception:
            # 该知识库从未上传过文档时 collection 不存在，删除属幂等清理，忽略即可
            pass

    def delete_document(self, kb_id: str, document_id: str) -> None:
        # 按 document_id 元数据过滤删除该文档的全部分块
        collection = self.get_collection(kb_id)
        collection.delete(where={"document_id": document_id})

    def list_chunks(self, kb_id: str) -> list[dict]:
        collection = self.get_collection(kb_id)
        result = collection.get(include=["documents", "metadatas"])
        ids = result.get("ids") or []
        documents = result.get("documents") or []
        metadatas = result.get("metadatas") or []

        chunks = []
        for index, chunk_id in enumerate(ids):
            document = documents[index] if index < len(documents) else ""
            metadata = metadatas[index] if index < len(metadatas) else {}
            chunks.append(
                {
                    "id": chunk_id,
                    "text": document or "",
                    "metadata": metadata or {},
                }
            )
        return chunks

    def query(
        self,
        kb_id: str,
        query_embedding: list[float],
        top_k: int = 20,
    ):
        collection = self.get_collection(kb_id)
        return collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            include=["documents", "metadatas", "distances"],
        )
