from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class RiskLevel(StrEnum):
    UNACCEPTABLE = "unacceptable"
    HIGH = "high"
    LIMITED = "limited"
    MINIMAL = "minimal"


class PIIEntityType(StrEnum):
    EMAIL = "EMAIL"
    PHONE = "PHONE"
    IBAN = "IBAN"
    CREDIT_CARD = "CREDIT_CARD"
    PERSON = "PERSON"
    OTHER = "OTHER"


class PIIFinding(BaseModel):
    entity_type: PIIEntityType
    start: int
    end: int


class PIIToken(BaseModel):
    token: str
    entity_type: PIIEntityType


class TokenizationResult(BaseModel):
    text: str
    tokens: list[PIIToken] = Field(default_factory=list)


class Document(BaseModel):
    id: str
    text: str
    source: str
    region: str
    tenant_id: str = "default"
    metadata: dict[str, str] = Field(default_factory=dict)


class Chunk(BaseModel):
    id: str
    document_id: str
    text: str
    source: str
    region: str
    tenant_id: str = "default"
    position: int
    metadata: dict[str, str] = Field(default_factory=dict)


class EmbeddedChunk(BaseModel):
    chunk: Chunk
    embedding: list[float]


class SparseVector(BaseModel):
    indices: list[int]
    values: list[float]


class ScoredChunk(BaseModel):
    chunk: Chunk
    score: float


class Query(BaseModel):
    text: str
    top_k: int | None = None
    regions: list[str] | None = None


class Citation(BaseModel):
    source: str
    chunk_id: str
    snippet: str


class Answer(BaseModel):
    text: str
    citations: list[Citation] = Field(default_factory=list)
    refused: bool = False
    is_ai_generated: bool = True
    model: str = ""


class GuardrailResult(BaseModel):
    allowed: bool
    sanitized_text: str
    pii: list[PIIFinding] = Field(default_factory=list)
    injection_detected: bool = False
    reason: str = ""


class AuditRecord(BaseModel):
    timestamp: str
    query_hash: str
    sources: list[str]
    region: str
    tenant_id: str = "default"
    subject: str = "system"
    decision: str
    prev_hash: str
    hash: str


class ModelCard(BaseModel):
    system_name: str
    purpose: str
    risk_level: RiskLevel
    llm_model: str
    embedding_model: str
    data_sources: list[str]
    regions: list[str]
    mitigations: list[str]
    eval_scores: dict[str, float] = Field(default_factory=dict)


class FineTuningStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ChatMessage(BaseModel):
    role: str
    content: str


class TrainingExample(BaseModel):
    messages: list[ChatMessage]


class FineTuningHyperParams(BaseModel):
    epochs: int = 3
    learning_rate: float = 1e-4
    suffix: str = "sovereign"


class FineTuningSpec(BaseModel):
    base_model: str
    examples: list[TrainingExample]
    hyperparams: FineTuningHyperParams = Field(default_factory=FineTuningHyperParams)
    tenant_id: str = "default"


class FineTuningJob(BaseModel):
    id: str
    base_model: str
    status: FineTuningStatus
    fine_tuned_model: str | None = None
    tenant_id: str = "default"
    created_at: str
    hyperparams: FineTuningHyperParams
    metrics: dict[str, float] = Field(default_factory=dict)
