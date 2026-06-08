from __future__ import annotations

from typing import Any

from sovereign_rag.domain.models import Chunk, ScoredChunk


def chunk_payload(chunk: Chunk) -> dict[str, object]:
    data = chunk.model_dump()
    data.pop("id", None)
    data["chunk_id"] = chunk.id
    return data


def chunk_from_payload(payload: dict[str, Any]) -> Chunk:
    metadata = {key: str(value) for key, value in dict(payload.get("metadata", {})).items()}
    return Chunk(
        id=str(payload.get("chunk_id", "")),
        document_id=str(payload.get("document_id", "")),
        text=str(payload.get("text", "")),
        source=str(payload.get("source", "")),
        region=str(payload.get("region", "")),
        tenant_id=str(payload.get("tenant_id", "default")),
        position=int(payload.get("position", 0)),
        metadata=metadata,
    )


def scored_from_hit(hit: object) -> ScoredChunk:
    payload = dict(getattr(hit, "payload", {}) or {})
    return ScoredChunk(
        chunk=chunk_from_payload(payload),
        score=float(getattr(hit, "score", 0.0)),
    )


def build_filter(tenant_id: str, regions: list[str] | None) -> object:
    from qdrant_client.models import FieldCondition, Filter, MatchAny, MatchValue

    must: list[object] = [FieldCondition(key="tenant_id", match=MatchValue(value=tenant_id))]
    if regions is not None:
        must.append(FieldCondition(key="region", match=MatchAny(any=regions)))
    return Filter(must=must)
