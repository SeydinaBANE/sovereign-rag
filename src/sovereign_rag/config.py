from __future__ import annotations

from enum import StrEnum
from functools import lru_cache

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from sovereign_rag.domain.access import Role


class ApiKeyPrincipal(BaseModel):
    key: str
    subject: str
    tenant_id: str
    roles: list[Role] = Field(default_factory=list)


class LLMProvider(StrEnum):
    FAKE = "fake"
    MISTRAL = "mistral"


class EmbeddingProvider(StrEnum):
    FAKE = "fake"
    MISTRAL = "mistral"
    LOCAL = "local"


class VectorProvider(StrEnum):
    MEMORY = "memory"
    QDRANT = "qdrant"


class SparseProvider(StrEnum):
    NONE = "none"
    FASTEMBED = "fastembed"


class RetrievalMode(StrEnum):
    VECTOR = "vector"
    HYBRID = "hybrid"


class RerankerProvider(StrEnum):
    NONE = "none"
    LEXICAL = "lexical"
    CROSS_ENCODER = "cross_encoder"


class PIIPolicy(StrEnum):
    MASK = "mask"
    REFUSE = "refuse"
    ALLOW = "allow"


class FineTuningProvider(StrEnum):
    NONE = "none"
    FAKE = "fake"
    MISTRAL = "mistral"
    LOCAL = "local"


class AuthProvider(StrEnum):
    STATIC = "static"
    OIDC = "oidc"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="SRAG_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    llm_provider: LLMProvider = LLMProvider.FAKE
    mistral_api_key: str = ""
    llm_model: str = "mistral-large-latest"
    llm_temperature: float = 0.1
    llm_max_tokens: int = 1024

    embedding_provider: EmbeddingProvider = EmbeddingProvider.FAKE
    embedding_model: str = "mistral-embed"
    embedding_dim: int = 1024

    vector_provider: VectorProvider = VectorProvider.MEMORY
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "sovereign_rag"
    sparse_provider: SparseProvider = SparseProvider.FASTEMBED
    sparse_model: str = "Qdrant/bm25"

    chunk_size: int = 800
    chunk_overlap: int = 120
    top_k: int = 5
    min_score: float = 0.25

    retrieval_mode: RetrievalMode = RetrievalMode.HYBRID
    candidate_k: int = 20
    rrf_k: int = 60
    reranker_provider: RerankerProvider = RerankerProvider.LEXICAL
    rerank_candidates: int = 20
    cross_encoder_model: str = "BAAI/bge-reranker-base"

    allowed_regions: list[str] = Field(default_factory=lambda: ["eu-west", "eu-central"])
    default_region: str = "eu-west"

    auth_enabled: bool = False
    auth_provider: AuthProvider = AuthProvider.STATIC
    default_tenant: str = "default"
    api_keys: list[ApiKeyPrincipal] = Field(default_factory=list)
    oidc_issuer: str = ""
    oidc_audience: str = ""
    oidc_jwks_url: str = ""
    oidc_algorithms: list[str] = Field(default_factory=lambda: ["RS256"])
    oidc_hs256_secret: str = ""
    oidc_subject_claim: str = "sub"
    oidc_tenant_claim: str = "tenant_id"
    oidc_roles_claim: str = "roles"
    pii_policy: PIIPolicy = PIIPolicy.MASK
    pii_vault_secret: str = ""
    pii_vault_on_ingest: bool = False
    audit_path: str = "data/audit/audit.log"

    fine_tuning_provider: FineTuningProvider = FineTuningProvider.FAKE
    fine_tuning_base_model: str = "open-mistral-7b"
    fine_tuning_epochs: int = 3
    fine_tuning_learning_rate: float = 1e-4
    fine_tuning_suffix: str = "sovereign"
    fine_tuning_min_examples: int = 10
    fine_tuning_output_dir: str = "data/fine_tuning"

    langfuse_enabled: bool = False
    langfuse_host: str = "http://localhost:3000"
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
