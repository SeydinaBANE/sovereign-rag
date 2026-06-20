from __future__ import annotations

from enum import StrEnum
from functools import lru_cache

from pydantic import BaseModel, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from sovereign_rag.domain.access import Role

MIN_VAULT_SECRET_LENGTH = 32


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


class AuditProvider(StrEnum):
    FILE = "file"
    POSTGRES = "postgres"


class PIIVaultProvider(StrEnum):
    MEMORY = "memory"
    POSTGRES = "postgres"


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
    llm_timeout_seconds: float = 30.0

    embedding_provider: EmbeddingProvider = EmbeddingProvider.FAKE
    embedding_model: str = "mistral-embed"
    embedding_dim: int = 1024
    embedding_timeout_seconds: float = 30.0

    vector_provider: VectorProvider = VectorProvider.MEMORY
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "sovereign_rag"
    qdrant_timeout_seconds: float = 10.0
    sparse_provider: SparseProvider = SparseProvider.FASTEMBED
    sparse_model: str = "Qdrant/bm25"

    max_query_chars: int = 8_000
    max_document_chars: int = 200_000
    max_documents_per_request: int = 256
    max_top_k: int = 50

    retry_attempts: int = 3
    retry_base_delay: float = 0.2

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
    oidc_jwks_timeout_seconds: float = 5.0
    oidc_algorithms: list[str] = Field(default_factory=lambda: ["RS256"])
    oidc_hs256_secret: str = ""
    oidc_subject_claim: str = "sub"
    oidc_tenant_claim: str = "tenant_id"
    oidc_roles_claim: str = "roles"
    pii_policy: PIIPolicy = PIIPolicy.MASK
    pii_vault_provider: PIIVaultProvider = PIIVaultProvider.MEMORY
    pii_vault_secret: str = ""
    pii_vault_salt: str = "sovereign-rag-pii-vault"
    pii_vault_dsn: str = ""
    pii_vault_on_ingest: bool = False
    audit_provider: AuditProvider = AuditProvider.FILE
    audit_path: str = "data/audit/audit.log"
    audit_dsn: str = ""

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

    @model_validator(mode="after")
    def _validate_production_safety(self) -> Settings:
        if not self.allowed_regions:
            raise ValueError("SRAG_ALLOWED_REGIONS must list at least one region.")
        if self.llm_provider is LLMProvider.MISTRAL and not self.mistral_api_key:
            raise ValueError("SRAG_LLM_PROVIDER=mistral requires SRAG_MISTRAL_API_KEY.")
        if self.embedding_provider is EmbeddingProvider.MISTRAL and not self.mistral_api_key:
            raise ValueError("SRAG_EMBEDDING_PROVIDER=mistral requires SRAG_MISTRAL_API_KEY.")
        if self.fine_tuning_provider is FineTuningProvider.MISTRAL and not self.mistral_api_key:
            raise ValueError("SRAG_FINE_TUNING_PROVIDER=mistral requires SRAG_MISTRAL_API_KEY.")
        if self.pii_vault_on_ingest and len(self.pii_vault_secret) < MIN_VAULT_SECRET_LENGTH:
            raise ValueError(
                "SRAG_PII_VAULT_ON_INGEST requires SRAG_PII_VAULT_SECRET of at least "
                f"{MIN_VAULT_SECRET_LENGTH} characters."
            )
        if self.audit_provider is AuditProvider.POSTGRES and not self.audit_dsn:
            raise ValueError("SRAG_AUDIT_PROVIDER=postgres requires SRAG_AUDIT_DSN.")
        if self.pii_vault_provider is PIIVaultProvider.POSTGRES and not self.pii_vault_dsn:
            raise ValueError("SRAG_PII_VAULT_PROVIDER=postgres requires SRAG_PII_VAULT_DSN.")
        self._validate_auth()
        return self

    def _validate_auth(self) -> None:
        if not self.auth_enabled:
            return
        if self.auth_provider is AuthProvider.STATIC and not self.api_keys:
            raise ValueError("SRAG_AUTH_ENABLED with static auth requires SRAG_API_KEYS.")
        if self.auth_provider is AuthProvider.OIDC:
            if not (self.oidc_issuer or self.oidc_jwks_url):
                raise ValueError("OIDC auth requires SRAG_OIDC_ISSUER or SRAG_OIDC_JWKS_URL.")
            if not self.oidc_audience:
                raise ValueError(
                    "OIDC auth requires SRAG_OIDC_AUDIENCE (audience verification is mandatory)."
                )
            if any(alg.startswith("HS") for alg in self.oidc_algorithms) and (
                not self.oidc_hs256_secret
            ):
                raise ValueError("OIDC HS* algorithms require SRAG_OIDC_HS256_SECRET.")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
