from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sovereign_rag.compliance.audit import GENESIS_HASH, chain_digest
from sovereign_rag.domain.models import AuditRecord

if TYPE_CHECKING:
    from psycopg import Connection

_CHAIN_LOCK_KEY = 815_237_001

_SCHEMA = """
CREATE TABLE IF NOT EXISTS audit_log (
    seq BIGSERIAL PRIMARY KEY,
    timestamp TEXT NOT NULL,
    query_hash TEXT NOT NULL,
    sources JSONB NOT NULL,
    region TEXT NOT NULL,
    tenant_id TEXT NOT NULL,
    subject TEXT NOT NULL,
    decision TEXT NOT NULL,
    prev_hash TEXT NOT NULL,
    hash TEXT NOT NULL
)
"""


class PostgresAuditLog:
    """Shared, hash-chained audit log backed by Postgres for multi-replica HA.

    A transaction-scoped advisory lock serialises appends across all replicas, so
    the global chain stays consistent under concurrent writers. The SDK is imported
    lazily to keep the package importable without ``psycopg`` installed.
    """

    def __init__(self, dsn: str) -> None:
        self._dsn = dsn
        with self._open() as conn:
            conn.execute(_SCHEMA)
            conn.commit()

    def _open(self) -> Connection:
        import psycopg

        return psycopg.connect(self._dsn)

    def record(
        self,
        query_hash: str,
        sources: list[str],
        region: str,
        decision: str,
        tenant_id: str = "default",
        subject: str = "system",
    ) -> AuditRecord:
        from psycopg.types.json import Json

        timestamp = datetime.now(UTC).isoformat()
        with self._open() as conn:
            conn.execute("SELECT pg_advisory_xact_lock(%s)", (_CHAIN_LOCK_KEY,))
            prev_hash = self._tip(conn)
            payload = {
                "timestamp": timestamp,
                "query_hash": query_hash,
                "sources": sources,
                "region": region,
                "tenant_id": tenant_id,
                "subject": subject,
                "decision": decision,
                "prev_hash": prev_hash,
            }
            entry_hash = chain_digest(payload)
            conn.execute(
                "INSERT INTO audit_log (timestamp, query_hash, sources, region, "
                "tenant_id, subject, decision, prev_hash, hash) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
                (
                    timestamp,
                    query_hash,
                    Json(sources),
                    region,
                    tenant_id,
                    subject,
                    decision,
                    prev_hash,
                    entry_hash,
                ),
            )
            conn.commit()
        return AuditRecord(hash=entry_hash, **payload)

    def verify_chain(self) -> bool:
        prev_hash = GENESIS_HASH
        with self._open() as conn:
            rows = conn.execute(
                "SELECT timestamp, query_hash, sources, region, tenant_id, subject, "
                "decision, prev_hash, hash FROM audit_log ORDER BY seq"
            ).fetchall()
        for row in rows:
            payload = {
                "timestamp": row[0],
                "query_hash": row[1],
                "sources": list(row[2]),
                "region": row[3],
                "tenant_id": row[4],
                "subject": row[5],
                "decision": row[6],
                "prev_hash": row[7],
            }
            if payload["prev_hash"] != prev_hash or chain_digest(payload) != row[8]:
                return False
            prev_hash = str(row[8])
        return True

    def _tip(self, conn: Connection) -> str:
        row = conn.execute("SELECT hash FROM audit_log ORDER BY seq DESC LIMIT 1").fetchone()
        return str(row[0]) if row else GENESIS_HASH
