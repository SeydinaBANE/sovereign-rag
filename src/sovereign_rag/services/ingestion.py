from __future__ import annotations

from sovereign_rag.compliance import pii
from sovereign_rag.compliance.data_residency import ensure_allowed
from sovereign_rag.config import Settings
from sovereign_rag.domain.exceptions import EmptyCorpusError
from sovereign_rag.domain.models import Chunk, Document, EmbeddedChunk
from sovereign_rag.ports.embeddings import EmbeddingPort
from sovereign_rag.ports.lexical import LexicalIndexPort
from sovereign_rag.ports.vault import PIIVaultPort
from sovereign_rag.ports.vector_store import VectorStorePort
from sovereign_rag.services.chunking import chunk_text


class IngestionService:
    def __init__(
        self,
        embedder: EmbeddingPort,
        store: VectorStorePort,
        lexical: LexicalIndexPort,
        settings: Settings,
        vault: PIIVaultPort | None = None,
    ) -> None:
        self._embedder = embedder
        self._store = store
        self._lexical = lexical
        self._settings = settings
        self._vault = vault

    def ingest(self, documents: list[Document], tenant_id: str | None = None) -> int:
        if not documents:
            raise EmptyCorpusError("No documents provided for ingestion.")
        tenant = tenant_id or self._settings.default_tenant
        chunks = self._build_chunks(documents, tenant)
        if not chunks:
            raise EmptyCorpusError("Documents produced no usable text after processing.")
        embeddings = self._embedder.embed([chunk.text for chunk in chunks])
        items = [
            EmbeddedChunk(chunk=chunk, embedding=embedding)
            for chunk, embedding in zip(chunks, embeddings, strict=True)
        ]
        self._store.upsert(items)
        self._lexical.index(chunks)
        return len(items)

    def _build_chunks(self, documents: list[Document], tenant_id: str) -> list[Chunk]:
        allowed = self._settings.allowed_regions
        chunks: list[Chunk] = []
        for document in documents:
            ensure_allowed(document.region, allowed)
            sanitized = self._sanitize(document.text, tenant_id)
            pieces = chunk_text(
                sanitized,
                self._settings.chunk_size,
                self._settings.chunk_overlap,
            )
            for position, piece in enumerate(pieces):
                chunks.append(
                    Chunk(
                        id=f"{tenant_id}:{document.id}:{position}",
                        document_id=document.id,
                        text=piece,
                        source=document.source,
                        region=document.region,
                        tenant_id=tenant_id,
                        position=position,
                        metadata=document.metadata,
                    )
                )
        return chunks

    def _sanitize(self, text: str, tenant_id: str) -> str:
        if self._settings.pii_vault_on_ingest and self._vault is not None:
            return self._vault.tokenize(text, tenant_id).text
        masked, _ = pii.mask(text)
        return masked
