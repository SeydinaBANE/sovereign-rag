from sovereign_rag.observability.evals import (
    EvalCase,
    groundedness,
    keyword_recall,
    score_case,
    summarize,
)


def test_groundedness_full_when_answer_in_context():
    assert groundedness("remote work allowed", "remote work is allowed here") == 1.0


def test_groundedness_low_when_unsupported():
    assert groundedness("quantum teleportation", "remote work policy") == 0.0


def test_keyword_recall_counts_hits():
    assert keyword_recall("three days per week", ["three", "week"]) == 1.0
    assert keyword_recall("three days", ["three", "week"]) == 0.5


def test_summarize_reports_refusal_accuracy():
    case = EvalCase(question="q", expected_keywords=[], must_refuse=True)
    result = score_case(case, "", "", refused=True)
    summary = summarize([result])
    assert summary.refusal_accuracy == 1.0


def test_summarize_empty_is_zero():
    summary = summarize([])
    assert summary.groundedness == 0.0
