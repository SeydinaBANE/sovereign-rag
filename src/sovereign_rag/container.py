from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from sovereign_rag.adapters.bm25 import BM25Index
from sovereign_rag.adapters.fakes import (
    FakeEmbedding,
    FakeFineTuner,
    FakeLLM,
    InMemoryVectorStore,
)
from sovereign_rag.adapters.lexical_reranker import LexicalReranker
from sovereign_rag.adapters.principals import StaticPrincipalResolver
from sovereign_rag.adapters.regex_guardrail import RegexGuardrail
from sovereign_rag.compliance.audit import FileAuditLog
from sovereign_rag.config import (
    AuthProvider,
    EmbeddingProvider,
    FineTuningProvider,
    LLMProvider,
    RerankerProvider,
    Settings,
    SparseProvider,
    VectorProvider,
    get_settings,
)
from sovereign_rag.observability.tracing import Tracer
from sovereign_rag.ports.audit import AuditPort
from sovereign_rag.ports.auth import PrincipalResolverPort
from sovereign_rag.ports.embeddings import EmbeddingPort
from sovereign_rag.ports.fine_tuning import FineTuningPort
from sovereign_rag.ports.guardrail import GuardrailPort
from sovereign_rag.ports.lexical import LexicalIndexPort
from sovereign_rag.ports.llm import LLMPort
from sovereign_rag.ports.reranker import RerankerPort
from sovereign_rag.ports.vault import PIIVaultPort
from sovereign_rag.ports.vector_store import VectorStorePort
from sovereign_rag.services.fine_tuning import FineTuningService
from sovereign_rag.services.ingestion import IngestionService
from sovereign_rag.services.rag import RAGService
from sovereign_rag.services.retrieval import RetrievalService


@dataclass
class Container:
    settings: Settings
    embedder: EmbeddingPort
    store: VectorStorePort
    lexical: LexicalIndexPort
    reranker: RerankerPort | None
    principals: PrincipalResolverPort
    guardrail: GuardrailPort
    audit: AuditPort
    llm: LLMPort
    ingestion: IngestionService
    retrieval: RetrievalService
    rag: RAGService
    fine_tuning: FineTuningService | None
    vault: PIIVaultPort


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


def build_stores(
    settings: Settings,
    embedder: EmbeddingPort,
) -> tuple[VectorStorePort, LexicalIndexPort]:
    if settings.vector_provider is VectorProvider.QDRANT:
        if settings.sparse_provider is SparseProvider.FASTEMBED:
            from sovereign_rag.adapters.qdrant_hybrid import QdrantHybridStore
            from sovereign_rag.adapters.sparse_embeddings import FastEmbedSparse

            hybrid = QdrantHybridStore(
                url=settings.qdrant_url,
                collection=settings.qdrant_collection,
                dim=embedder.dim,
                sparse=FastEmbedSparse(model=settings.sparse_model),
            )
            return hybrid, hybrid.lexical()

        from sovereign_rag.adapters.qdrant_store import QdrantStore

        store = QdrantStore(
            url=settings.qdrant_url,
            collection=settings.qdrant_collection,
            dim=embedder.dim,
        )
        return store, BM25Index()
    return InMemoryVectorStore(), BM25Index()


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


def build_reranker(settings: Settings) -> RerankerPort | None:
    if settings.reranker_provider is RerankerProvider.LEXICAL:
        return LexicalReranker()
    if settings.reranker_provider is RerankerProvider.CROSS_ENCODER:
        from sovereign_rag.adapters.cross_encoder_reranker import CrossEncoderReranker

        return CrossEncoderReranker(model=settings.cross_encoder_model)
    return None


def build_vault(settings: Settings) -> PIIVaultPort:
    from sovereign_rag.adapters.pii_vault import InMemoryPIIVault

    return InMemoryPIIVault(secret=settings.pii_vault_secret)


def build_principals(settings: Settings) -> PrincipalResolverPort:
    if settings.auth_provider is AuthProvider.OIDC:
        from sovereign_rag.adapters.oidc_principals import OidcPrincipalResolver

        return OidcPrincipalResolver(
            issuer=settings.oidc_issuer,
            audience=settings.oidc_audience,
            jwks_url=settings.oidc_jwks_url,
            algorithms=settings.oidc_algorithms,
            hs256_secret=settings.oidc_hs256_secret,
            subject_claim=settings.oidc_subject_claim,
            tenant_claim=settings.oidc_tenant_claim,
            roles_claim=settings.oidc_roles_claim,
            default_tenant=settings.default_tenant,
        )
    return StaticPrincipalResolver(settings.api_keys)


def build_fine_tuner(settings: Settings) -> FineTuningPort | None:
    if settings.fine_tuning_provider is FineTuningProvider.MISTRAL:
        from sovereign_rag.adapters.mistral_fine_tuning import MistralFineTuner

        return MistralFineTuner(api_key=settings.mistral_api_key)
    if settings.fine_tuning_provider is FineTuningProvider.LOCAL:
        from sovereign_rag.adapters.local_lora import LocalLoRAFineTuner

        return LocalLoRAFineTuner(output_dir=settings.fine_tuning_output_dir)
    if settings.fine_tuning_provider is FineTuningProvider.FAKE:
        return FakeFineTuner()
    return None


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
    store, lexical = build_stores(settings, embedder)
    reranker = build_reranker(settings)
    principals: PrincipalResolverPort = build_principals(settings)
    guardrail: GuardrailPort = RegexGuardrail(pii_policy=settings.pii_policy)
    audit: AuditPort = FileAuditLog(settings.audit_path)
    llm = build_llm(settings)
    tracer = build_tracer(settings)

    vault = build_vault(settings)
    ingestion = IngestionService(embedder, store, lexical, settings, vault)
    retrieval = RetrievalService(embedder, store, lexical, settings, reranker)
    rag = RAGService(llm, retrieval, guardrail, audit, settings, tracer, vault)
    fine_tuner = build_fine_tuner(settings)
    fine_tuning = (
        FineTuningService(fine_tuner, audit, settings, tracer) if fine_tuner is not None else None
    )
    return Container(
        settings=settings,
        embedder=embedder,
        store=store,
        lexical=lexical,
        reranker=reranker,
        principals=principals,
        guardrail=guardrail,
        audit=audit,
        llm=llm,
        ingestion=ingestion,
        retrieval=retrieval,
        rag=rag,
        fine_tuning=fine_tuning,
        vault=vault,
    )


@lru_cache(maxsize=1)
def get_container() -> Container:
    return build_container(get_settings())
