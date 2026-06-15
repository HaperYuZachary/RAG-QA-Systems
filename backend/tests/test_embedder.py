import pytest

from app.config import Settings
from app.core.embedder import Embedder, EmbeddingError


class FakeEmbeddingItem:
    def __init__(self, embedding):
        self.embedding = embedding


class FakeEmbeddingResponse:
    def __init__(self, embeddings):
        self.data = [FakeEmbeddingItem(embedding) for embedding in embeddings]


class FakeEmbeddingsAPI:
    def __init__(self, failures_before_success=0):
        self.failures_before_success = failures_before_success
        self.calls = []

    def create(self, model, input):
        self.calls.append({"model": model, "input": list(input)})
        if self.failures_before_success > 0:
            self.failures_before_success -= 1
            raise RuntimeError("temporary embedding outage")
        return FakeEmbeddingResponse(
            [[float(len(self.calls)), float(index)] for index, _ in enumerate(input)]
        )


class FakeOpenAIClient:
    def __init__(self, failures_before_success=0):
        self.embeddings = FakeEmbeddingsAPI(failures_before_success)


class FakeLocalEmbedding:
    def __init__(self, values):
        self.values = values

    def tolist(self):
        return self.values


class FakeLocalEmbeddingClient:
    def __init__(self):
        self.calls = []

    def embed(self, documents, batch_size):
        self.calls.append({"documents": list(documents), "batch_size": batch_size})
        return [
            FakeLocalEmbedding([float(len(text)), float(index)])
            for index, text in enumerate(documents)
        ]


def test_embed_batches_texts_and_preserves_order():
    texts = [f"text-{index}" for index in range(45)]
    client = FakeOpenAIClient()
    embedder = Embedder(
        Settings(
            embedding_provider="openai",
            openai_api_key="test-key",
            embedding_model="test-embedding-model",
            embedding_batch_size=20,
        ),
        client=client,
    )

    embeddings = embedder.embed(texts)

    assert [len(call["input"]) for call in client.embeddings.calls] == [20, 20, 5]
    assert all(call["model"] == "test-embedding-model" for call in client.embeddings.calls)
    assert len(embeddings) == 45
    assert embeddings[0] == [1.0, 0.0]
    assert embeddings[20] == [2.0, 0.0]
    assert embeddings[40] == [3.0, 0.0]


def test_embed_returns_empty_list_without_calling_client():
    client = FakeOpenAIClient()
    embedder = Embedder(Settings(openai_api_key="test-key"), client=client)

    assert embedder.embed([]) == []
    assert client.embeddings.calls == []


def test_embed_retries_failed_batches_without_sleeping():
    client = FakeOpenAIClient(failures_before_success=2)
    sleep_calls = []
    embedder = Embedder(
        Settings(
            embedding_provider="openai",
            openai_api_key="test-key",
            embedding_max_retries=3,
        ),
        client=client,
        sleep=sleep_calls.append,
    )

    embeddings = embedder.embed(["retry me"])

    assert embeddings == [[3.0, 0.0]]
    assert len(client.embeddings.calls) == 3
    assert sleep_calls == [1.0, 2.0]


def test_embed_raises_after_retry_budget_is_exhausted():
    client = FakeOpenAIClient(failures_before_success=10)
    embedder = Embedder(
        Settings(
            embedding_provider="openai",
            openai_api_key="test-key",
            embedding_max_retries=3,
        ),
        client=client,
        sleep=lambda seconds: None,
    )

    with pytest.raises(EmbeddingError, match="Embedding request failed"):
        embedder.embed(["will fail"])

    assert len(client.embeddings.calls) == 3


def test_embed_requires_api_key_when_default_client_is_used():
    embedder = Embedder(Settings(embedding_provider="openai", openai_api_key=""))

    with pytest.raises(EmbeddingError, match="OPENAI_API_KEY"):
        embedder.embed(["needs a real client"])


def test_embed_uses_fastembed_provider_without_openai_key():
    client = FakeLocalEmbeddingClient()
    embedder = Embedder(
        Settings(
            embedding_provider="fastembed",
            openai_api_key="",
            embedding_model="BAAI/bge-small-zh-v1.5",
            embedding_batch_size=2,
        ),
        client=client,
    )

    embeddings = embedder.embed(["你好", "本地 embedding", "检索"])

    assert [call["documents"] for call in client.calls] == [["你好", "本地 embedding"], ["检索"]]
    assert [call["batch_size"] for call in client.calls] == [2, 2]
    assert embeddings == [[2.0, 0.0], [12.0, 1.0], [2.0, 0.0]]
