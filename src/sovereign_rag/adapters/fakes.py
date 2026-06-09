from __future__ import annotations

import hashlib
import math
import re
from datetime import UTC, datetime

from sovereign_rag.domain.exceptions import FineTuningJobNotFound
from sovereign_rag.domain.models import (
    EmbeddedChunk,
    FineTuningJob,
    FineTuningSpec,
    FineTuningStatus,
    ScoredChunk,
    SparseVector,
)
from sovereign_rag.ports.llm import LLMResponse

_WORD = re.compile(r"\w+", re.UNICODE)
_CONTEXT = re.compile(r"Context:\n(.*?)\n\nQuestion:", re.DOTALL)


class FakeLLM:
    """Deterministic offline LLM: grounds its answer in the prompt context."""

    def __init__(self, model: str = "fake-llm") -> None:
        self._model = model

    def complete(self, system: str, prompt: str) -> LLMResponse:
        match = _CONTEXT.search(prompt)
        context = match.group(1).strip() if match else ""
        snippet = context.splitlines()[0].strip() if context else ""
        text = (
            f"Based on the retrieved sources: {snippet[:240]}"
            if snippet
            else "I could not find this information in the provided sources."
        )
        return LLMResponse(
            text=text,
            input_tokens=_count_tokens(prompt) + _count_tokens(system),
            output_tokens=_count_tokens(text),
            model=self._model,
        )


class FakeEmbedding:
    """Deterministic hashing embedding; cosine similarity tracks token overlap."""

    def __init__(self, dim: int = 256) -> None:
        self._dim = dim

    @property
    def dim(self) -> int:
        return self._dim

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._embed_one(text) for text in texts]

    def _embed_one(self, text: str) -> list[float]:
        vector = [0.0] * self._dim
        for token in _WORD.findall(text.lower()):
            index = int(hashlib.md5(token.encode("utf-8")).hexdigest(), 16) % self._dim
            vector[index] += 1.0
        norm = math.sqrt(sum(value * value for value in vector))
        if norm == 0.0:
            return vector
        return [value / norm for value in vector]


class FakeSparseEmbedding:
    """Deterministic hashing sparse encoder; overlap tracks shared terms."""

    def __init__(self, dim: int = 4096) -> None:
        self._dim = dim

    def encode(self, texts: list[str]) -> list[SparseVector]:
        return [self._encode_one(text) for text in texts]

    def _encode_one(self, text: str) -> SparseVector:
        counts: dict[int, float] = {}
        for token in _WORD.findall(text.lower()):
            index = int(hashlib.md5(token.encode("utf-8")).hexdigest(), 16) % self._dim
            counts[index] = counts.get(index, 0.0) + 1.0
        indices = sorted(counts)
        return SparseVector(indices=indices, values=[counts[index] for index in indices])


class InMemoryVectorStore:
    """Sovereign, dependency-free vector store for tests and offline demos."""

    def __init__(self) -> None:
        self._items: list[EmbeddedChunk] = []

    def upsert(self, items: list[EmbeddedChunk]) -> None:
        existing = {item.chunk.id for item in items}
        self._items = [item for item in self._items if item.chunk.id not in existing]
        self._items.extend(items)

    def search(
        self,
        embedding: list[float],
        top_k: int,
        tenant_id: str,
        regions: list[str] | None = None,
    ) -> list[ScoredChunk]:
        scored: list[ScoredChunk] = []
        for item in self._items:
            if item.chunk.tenant_id != tenant_id:
                continue
            if regions is not None and item.chunk.region not in regions:
                continue
            scored.append(ScoredChunk(chunk=item.chunk, score=_cosine(embedding, item.embedding)))
        scored.sort(key=lambda item: item.score, reverse=True)
        return scored[:top_k]

    def delete_by_source(self, source: str) -> int:
        before = len(self._items)
        self._items = [item for item in self._items if item.chunk.source != source]
        return before - len(self._items)

    def count(self) -> int:
        return len(self._items)


class FakeFineTuner:
    """Deterministic offline fine-tuning provider for tests and demos."""

    def __init__(self) -> None:
        self._jobs: dict[str, FineTuningJob] = {}
        self._counter = 0

    def create_job(self, spec: FineTuningSpec) -> FineTuningJob:
        self._counter += 1
        job_id = f"ftjob-fake-{self._counter:04d}"
        suffix = spec.hyperparams.suffix or "custom"
        job = FineTuningJob(
            id=job_id,
            base_model=spec.base_model,
            status=FineTuningStatus.SUCCEEDED,
            fine_tuned_model=f"{spec.base_model}:{suffix}",
            tenant_id=spec.tenant_id,
            created_at=datetime.now(UTC).isoformat(),
            hyperparams=spec.hyperparams,
            metrics={"train_examples": float(len(spec.examples)), "train_loss": 0.1},
        )
        self._jobs[job_id] = job
        return job

    def get_job(self, job_id: str) -> FineTuningJob:
        job = self._jobs.get(job_id)
        if job is None:
            raise FineTuningJobNotFound(job_id)
        return job

    def list_jobs(self, tenant_id: str) -> list[FineTuningJob]:
        return [job for job in self._jobs.values() if job.tenant_id == tenant_id]

    def cancel_job(self, job_id: str) -> FineTuningJob:
        job = self.get_job(job_id)
        cancelled = job.model_copy(update={"status": FineTuningStatus.CANCELLED})
        self._jobs[job_id] = cancelled
        return cancelled


def _cosine(left: list[float], right: list[float]) -> float:
    if len(left) != len(right):
        return 0.0
    dot = sum(a * b for a, b in zip(left, right, strict=True))
    norm_left = math.sqrt(sum(a * a for a in left))
    norm_right = math.sqrt(sum(b * b for b in right))
    if norm_left == 0.0 or norm_right == 0.0:
        return 0.0
    return dot / (norm_left * norm_right)


def _count_tokens(text: str) -> int:
    return len(_WORD.findall(text))
