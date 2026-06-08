from __future__ import annotations


class LocalEmbedding:
    """On-premise embedding via fastembed (data never leaves the cluster)."""

    def __init__(self, model: str = "BAAI/bge-m3", dim: int = 1024) -> None:
        from fastembed import TextEmbedding

        self._model = TextEmbedding(model_name=model)
        self._dim = dim

    @property
    def dim(self) -> int:
        return self._dim

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [vector.tolist() for vector in self._model.embed(texts)]
