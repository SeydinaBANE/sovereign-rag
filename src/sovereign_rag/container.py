from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from sovereign_rag.adapters.fakes import FakeEmbedding, FakeLLM, InMemoryVectorStore
from sovereign_rag.adapters.regex_guardrail import RegexGuardrail
from sovereign_rag.compliance.audit import FileAuditLog
from sovereign_rag.config import (
    EmbeddingProvider,
    LLMProvider,
    Settings,
    VectorProvider,
    get_settings,
)
from sovereign_rag.observability.tracing import Tracer
from sovereign_rag.ports.audit import AuditPort
from sovereign_rag.ports.embeddings import EmbeddingPort
from sovereign_rag.ports.guardrail import GuardrailPort
from sovereign_rag.ports.llm import LLMPort
from sovereign_rag.ports.vector_store import VectorStorePort
from sovereign_rag.services.ingestion import IngestionService
from sovereign_rag.services.rag import RAGService
from sovereign_rag.services.retrieval import RetrievalService


@dataclass
class Container:
    settings: Settings
    embedder: EmbeddingPort
    store: VectorStorePort
    guardrail: GuardrailPort
    audit: AuditPort
    llm: LLMPort
    ingestion: IngestionService
    retrieval: RetrievalService
    rag: RAGService


def build_embedder(settings: Settings) -> EmbeddingPort:
    if settings.embedding_provider is EmbeddingProvider.MISTRAL:
        from sovereign_rag.adapters.mistral_embeddings import MistralEmbedding

        return MistralEmbedding(
            api_key=settings.mistral_api_key,
            model=settings.embedding_model,
            dim=settings.embedding_dim,
        )
    if settings.embedding_provider is EmbeddingProvider.LOCAL:
        from sovereign_rag.adapters.local_embeddings import LocalEmbedding

        return LocalEmbedding(model=settings.embedding_model, dim=settings.embedding_dim)
    return FakeEmbedding(dim=settings.embedding_dim)


def build_store(settings: Settings, embedder: EmbeddingPort) -> VectorStorePort:
    if settings.vector_provider is VectorProvider.QDRANT:
        from sovereign_rag.adapters.qdrant_store import QdrantStore

        return QdrantStore(
            url=settings.qdrant_url,
            collection=settings.qdrant_collection,
            dim=embedder.dim,
        )
    return InMemoryVectorStore()


def build_llm(settings: Settings) -> LLMPort:
    if settings.llm_provider is LLMProvider.MISTRAL:
        from sovereign_rag.adapters.mistral_llm import MistralLLM

        return MistralLLM(
            api_key=settings.mistral_api_key,
            model=settings.llm_model,
            temperature=settings.llm_temperature,
            max_tokens=settings.llm_max_tokens,
        )
    return FakeLLM(model=settings.llm_model)


def build_tracer(settings: Settings) -> Tracer:
    if not settings.langfuse_enabled:
        return Tracer()
    from langfuse import Langfuse

    client = Langfuse(
        host=settings.langfuse_host,
        public_key=settings.langfuse_public_key,
        secret_key=settings.langfuse_secret_key,
    )
    return Tracer(enabled=True, client=client)


def build_container(settings: Settings) -> Container:
    embedder = build_embedder(settings)
    store = build_store(settings, embedder)
    guardrail: GuardrailPort = RegexGuardrail(pii_policy=settings.pii_policy)
    audit: AuditPort = FileAuditLog(settings.audit_path)
    llm = build_llm(settings)
    tracer = build_tracer(settings)

    ingestion = IngestionService(embedder, store, settings)
    retrieval = RetrievalService(embedder, store, settings)
    rag = RAGService(llm, retrieval, guardrail, audit, settings, tracer)
    return Container(
        settings=settings,
        embedder=embedder,
        store=store,
        guardrail=guardrail,
        audit=audit,
        llm=llm,
        ingestion=ingestion,
        retrieval=retrieval,
        rag=rag,
    )


@lru_cache(maxsize=1)
def get_container() -> Container:
    return build_container(get_settings())
