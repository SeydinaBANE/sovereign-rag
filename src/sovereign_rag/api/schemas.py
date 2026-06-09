from __future__ import annotations

from pydantic import BaseModel, Field


class IngestDocument(BaseModel):
    id: str
    text: str
    source: str
    region: str | None = None
    metadata: dict[str, str] = Field(default_factory=dict)


class IngestRequest(BaseModel):
    documents: list[IngestDocument]


class IngestResponse(BaseModel):
    chunks_indexed: int
    total_chunks: int


class QueryRequest(BaseModel):
    text: str
    top_k: int | None = None
    regions: list[str] | None = None


class HealthResponse(BaseModel):
    status: str
    vector_count: int
    audit_chain_valid: bool


class CardRequest(BaseModel):
    system_name: str = "sovereign-rag-demo"
    purpose: str = "Enterprise document question answering assistant (RAG)"


class ChatMessageSchema(BaseModel):
    role: str
    content: str


class TrainingExampleSchema(BaseModel):
    messages: list[ChatMessageSchema]


class FineTuningRequest(BaseModel):
    examples: list[TrainingExampleSchema]
    epochs: int | None = None
    learning_rate: float | None = None
    suffix: str | None = None
