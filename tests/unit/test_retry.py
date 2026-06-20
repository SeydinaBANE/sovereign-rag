import pytest

from sovereign_rag.adapters.retry import RetryPolicy, retry_call

_NO_DELAY = RetryPolicy(attempts=3, base_delay=0.0)


def test_retry_call_returns_first_success():
    calls = {"n": 0}

    def _op() -> str:
        calls["n"] += 1
        return "ok"

    assert retry_call(_op, _NO_DELAY) == "ok"
    assert calls["n"] == 1


def test_retry_call_recovers_after_transient_failures():
    calls = {"n": 0}

    def _op() -> str:
        calls["n"] += 1
        if calls["n"] < 3:
            raise ConnectionError("transient")
        return "ok"

    assert retry_call(_op, _NO_DELAY) == "ok"
    assert calls["n"] == 3


def test_retry_call_reraises_after_exhausting_attempts():
    calls = {"n": 0}

    def _op() -> str:
        calls["n"] += 1
        raise ConnectionError("down")

    with pytest.raises(ConnectionError):
        retry_call(_op, _NO_DELAY)
    assert calls["n"] == 3


def test_retry_call_single_attempt_does_not_retry():
    calls = {"n": 0}

    def _op() -> str:
        calls["n"] += 1
        raise ConnectionError("down")

    with pytest.raises(ConnectionError):
        retry_call(_op, RetryPolicy(attempts=1, base_delay=0.0))
    assert calls["n"] == 1
