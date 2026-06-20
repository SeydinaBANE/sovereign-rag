from __future__ import annotations

from sovereign_rag.adapters.retry import RetryPolicy, retry_call


class MistralEmbedding:
    """Mistral embedding adapter (`mistral-embed`)."""

    def __init__(
        self,
        api_key: str,
        model: str = "mistral-embed",
        dim: int = 1024,
        timeout: float = 30.0,
        retry: RetryPolicy | None = None,
    ) -> None:
        from mistralai import Mistral

        self._client = Mistral(api_key=api_key, timeout_ms=int(timeout * 1000))
        self._model = model
        self._dim = dim
        self._retry = retry or RetryPolicy()

    @property
    def dim(self) -> int:
        return self._dim

    def embed(self, texts: list[str]) -> list[list[float]]:
        response = retry_call(
            lambda: self._client.embeddings.create(model=self._model, inputs=texts),
            self._retry,
        )
        return [list(item.embedding) for item in response.data]
