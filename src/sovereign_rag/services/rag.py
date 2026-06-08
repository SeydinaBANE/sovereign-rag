from __future__ import annotations

from sovereign_rag.compliance.audit import hash_query
from sovereign_rag.config import Settings
from sovereign_rag.domain.models import Answer, Citation, Query, ScoredChunk
from sovereign_rag.observability.tracing import Tracer, estimate_cost
from sovereign_rag.ports.audit import AuditPort
from sovereign_rag.ports.guardrail import GuardrailPort
from sovereign_rag.ports.llm import LLMPort
from sovereign_rag.services.retrieval import RetrievalService

_SYSTEM = (
    "You are a sovereign enterprise assistant. Answer the question using ONLY the "
    "provided context. Cite sources with their bracketed index. If the answer is not "
    "in the context, reply that the information is not available."
)
_REFUSAL = "The information requested is not available in the authorised sources."
_SNIPPET_LEN = 160


class RAGService:
    def __init__(
        self,
        llm: LLMPort,
        retrieval: RetrievalService,
        guardrail: GuardrailPort,
        audit: AuditPort,
        settings: Settings,
        tracer: Tracer | None = None,
    ) -> None:
        self._llm = llm
        self._retrieval = retrieval
        self._guardrail = guardrail
        self._audit = audit
        self._settings = settings
        self._tracer = tracer or Tracer()

    def answer(self, query: Query) -> Answer:
        query_hash = hash_query(query.text)
        region = self._settings.default_region

        guard = self._guardrail.scan_input(query.text)
        if not guard.allowed:
            self._audit.record(query_hash, [], region, f"blocked:{guard.reason}")
            return Answer(text=_REFUSAL, refused=True, model=self._settings.llm_model)

        sanitized = Query(text=guard.sanitized_text, top_k=query.top_k, regions=query.regions)
        scored = self._retrieval.retrieve(sanitized)
        if not scored:
            self._audit.record(query_hash, [], region, "refused:no_context")
            return Answer(text=_REFUSAL, refused=True, model=self._settings.llm_model)

        with self._tracer.span("rag.generate", query_hash=query_hash) as span:
            response = self._llm.complete(_SYSTEM, _build_prompt(sanitized.text, scored))
            output_guard = self._guardrail.scan_output(response.text)
            span.attributes["input_tokens"] = response.input_tokens
            span.attributes["output_tokens"] = response.output_tokens
            span.attributes["cost_usd"] = estimate_cost(
                response.model or self._settings.llm_model,
                response.input_tokens,
                response.output_tokens,
            )

        sources = sorted({item.chunk.source for item in scored})
        self._audit.record(query_hash, sources, region, "answered")
        return Answer(
            text=output_guard.sanitized_text,
            citations=_build_citations(scored),
            refused=False,
            model=response.model or self._settings.llm_model,
        )


def _build_prompt(question: str, scored: list[ScoredChunk]) -> str:
    lines = [
        f"[{index + 1}] ({item.chunk.source}) {item.chunk.text}"
        for index, item in enumerate(scored)
    ]
    context = "\n".join(lines)
    return f"Context:\n{context}\n\nQuestion: {question}\n\nAnswer with citations:"


def _build_citations(scored: list[ScoredChunk]) -> list[Citation]:
    return [
        Citation(
            source=item.chunk.source,
            chunk_id=item.chunk.id,
            snippet=item.chunk.text[:_SNIPPET_LEN],
        )
        for item in scored
    ]
