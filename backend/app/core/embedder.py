import time
from collections.abc import Callable, Sequence
from pathlib import Path

from app.config import Settings, settings


class EmbeddingError(RuntimeError):
    pass


class Embedder:
    def __init__(
        self,
        app_settings: Settings | None = None,
        client=None,
        sleep: Callable[[float], None] = time.sleep,
    ):
        self.settings = app_settings or settings
        self._client = client
        self.sleep = sleep

    @property
    def client(self):
        if self._client is None:
            self._client = self._create_client()
        return self._client

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        if not texts:
            return []

        embeddings: list[list[float]] = []
        for batch in self._batches(list(texts)):
            embeddings.extend(self._embed_batch(batch))
        return embeddings

    def _create_client(self):
        if self.settings.embedding_provider == "fastembed":
            try:
                from fastembed import TextEmbedding
            except ImportError as exc:
                raise EmbeddingError(
                    "fastembed is required for local embeddings. Install it with: pip install fastembed"
                ) from exc

            cache_dir = Path(self.settings.embedding_cache_dir)
            cache_dir.mkdir(parents=True, exist_ok=True)
            return TextEmbedding(
                model_name=self.settings.embedding_model,
                cache_dir=str(cache_dir),
            )

        if not self.settings.openai_api_key:
            raise EmbeddingError("OPENAI_API_KEY is required for OpenAI embeddings")

        from openai import OpenAI

        return OpenAI(api_key=self.settings.openai_api_key)

    def _batches(self, texts: list[str]):
        batch_size = self.settings.embedding_batch_size
        for start in range(0, len(texts), batch_size):
            yield texts[start:start + batch_size]

    def _embed_batch(self, batch: list[str]) -> list[list[float]]:
        last_error: Exception | None = None
        for attempt in range(self.settings.embedding_max_retries):
            try:
                if self.settings.embedding_provider == "fastembed":
                    return self._embed_fastembed_batch(batch)
                return self._embed_openai_batch(batch)
            except EmbeddingError:
                raise
            except Exception as exc:
                last_error = exc
                is_last_attempt = attempt == self.settings.embedding_max_retries - 1
                if is_last_attempt:
                    break
                self.sleep(float(2 ** attempt))

        raise EmbeddingError("Embedding request failed after retries") from last_error

    def _embed_openai_batch(self, batch: list[str]) -> list[list[float]]:
        response = self.client.embeddings.create(
            model=self.settings.embedding_model,
            input=batch,
        )
        return [item.embedding for item in response.data]

    def _embed_fastembed_batch(self, batch: list[str]) -> list[list[float]]:
        embeddings = self.client.embed(
            batch,
            batch_size=self.settings.embedding_batch_size,
        )
        return [self._to_float_list(embedding) for embedding in embeddings]

    @staticmethod
    def _to_float_list(embedding) -> list[float]:
        if hasattr(embedding, "tolist"):
            embedding = embedding.tolist()
        return [float(value) for value in embedding]
