import os

import pytest

pytest.importorskip("psycopg")

from sovereign_rag.adapters.postgres_audit import PostgresAuditLog
from sovereign_rag.compliance.audit import hash_query

pytestmark = pytest.mark.integration


@pytest.fixture
def dsn() -> str:
    value = os.environ.get("SRAG_AUDIT_DSN")
    if not value:
        pytest.skip("SRAG_AUDIT_DSN not set")
    _reset(value)
    return value


def _reset(dsn: str) -> None:
    import psycopg

    with psycopg.connect(dsn) as conn:
        conn.execute("DROP TABLE IF EXISTS audit_log")
        conn.commit()


def test_postgres_audit_chain_round_trip(dsn: str) -> None:
    log = PostgresAuditLog(dsn=dsn)
    log.record(hash_query("q1"), ["a.md"], "eu-west", "answered", "acme", "alice")
    log.record(hash_query("q2"), ["b.md"], "eu-west", "refused:no_context", "acme", "alice")
    assert log.verify_chain() is True


def test_postgres_audit_chain_consistent_across_instances(dsn: str) -> None:
    first = PostgresAuditLog(dsn=dsn)
    second = PostgresAuditLog(dsn=dsn)
    first.record(hash_query("q1"), [], "eu-west", "answered")
    second.record(hash_query("q2"), [], "eu-west", "answered")
    assert second.verify_chain() is True
    assert first.verify_chain() is True


def test_postgres_audit_detects_tampering(dsn: str) -> None:
    import psycopg

    log = PostgresAuditLog(dsn=dsn)
    log.record(hash_query("q1"), ["a.md"], "eu-west", "answered")
    with psycopg.connect(dsn) as conn:
        conn.execute("UPDATE audit_log SET decision = 'deleted'")
        conn.commit()
    assert log.verify_chain() is False
