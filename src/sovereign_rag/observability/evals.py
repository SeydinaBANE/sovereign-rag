from __future__ import annotations

import re

from pydantic import BaseModel, Field

_WORD = re.compile(r"\w+", re.UNICODE)


class EvalCase(BaseModel):
    question: str
    expected_keywords: list[str]
    must_refuse: bool = False


class EvalResult(BaseModel):
    question: str
    groundedness: float
    keyword_recall: float
    refusal_correct: bool


class EvalSummary(BaseModel):
    groundedness: float
    keyword_recall: float
    refusal_accuracy: float
    results: list[EvalResult] = Field(default_factory=list)


def groundedness(answer: str, context: str) -> float:
    answer_tokens = set(_tokens(answer))
    if not answer_tokens:
        return 1.0
    context_tokens = set(_tokens(context))
    grounded = answer_tokens & context_tokens
    return len(grounded) / len(answer_tokens)


def keyword_recall(answer: str, expected_keywords: list[str]) -> float:
    if not expected_keywords:
        return 1.0
    answer_tokens = set(_tokens(answer))
    hits = sum(1 for keyword in expected_keywords if keyword.lower() in answer_tokens)
    return hits / len(expected_keywords)


def score_case(
    case: EvalCase,
    answer: str,
    context: str,
    refused: bool,
) -> EvalResult:
    return EvalResult(
        question=case.question,
        groundedness=groundedness(answer, context),
        keyword_recall=keyword_recall(answer, case.expected_keywords),
        refusal_correct=(refused == case.must_refuse),
    )


def summarize(results: list[EvalResult]) -> EvalSummary:
    if not results:
        return EvalSummary(groundedness=0.0, keyword_recall=0.0, refusal_accuracy=0.0)
    count = len(results)
    return EvalSummary(
        groundedness=sum(result.groundedness for result in results) / count,
        keyword_recall=sum(result.keyword_recall for result in results) / count,
        refusal_accuracy=sum(1 for result in results if result.refusal_correct) / count,
        results=results,
    )


def _tokens(text: str) -> list[str]:
    return [token.lower() for token in _WORD.findall(text)]
