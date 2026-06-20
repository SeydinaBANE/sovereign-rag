from __future__ import annotations

import hashlib
import json
import threading
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path

from sovereign_rag.domain.models import AuditRecord

GENESIS_HASH = "0" * 64
_GENESIS = GENESIS_HASH


def chain_digest(payload: Mapping[str, object]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


class FileAuditLog:
    """Append-only, hash-chained audit log for AI Act traceability.

    The tip of the chain is cached in memory and writes are serialised by a lock,
    so appending is O(1) and the chain stays consistent under concurrent requests
    (within a single process). For multi-replica deployments use a shared backend
    such as ``PostgresAuditLog`` (``SRAG_AUDIT_PROVIDER=postgres``).
    """

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._tip = self._last_hash()

    def record(
        self,
        query_hash: str,
        sources: list[str],
        region: str,
        decision: str,
        tenant_id: str = "default",
        subject: str = "system",
    ) -> AuditRecord:
        with self._lock:
            timestamp = datetime.now(UTC).isoformat()
            payload = {
                "timestamp": timestamp,
                "query_hash": query_hash,
                "sources": sources,
                "region": region,
                "tenant_id": tenant_id,
                "subject": subject,
                "decision": decision,
                "prev_hash": self._tip,
            }
            entry_hash = chain_digest(payload)
            record = AuditRecord(hash=entry_hash, **payload)
            with self._path.open("a", encoding="utf-8") as handle:
                handle.write(record.model_dump_json() + "\n")
            self._tip = entry_hash
            return record

    def verify_chain(self) -> bool:
        prev_hash = _GENESIS
        for record in self._entries():
            if record.prev_hash != prev_hash:
                return False
            expected = chain_digest(record_payload(record))
            if expected != record.hash:
                return False
            prev_hash = record.hash
        return True

    def _entries(self) -> list[AuditRecord]:
        if not self._path.exists():
            return []
        records: list[AuditRecord] = []
        for line in self._path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                records.append(AuditRecord.model_validate_json(line))
        return records

    def _last_hash(self) -> str:
        entries = self._entries()
        return entries[-1].hash if entries else _GENESIS


def record_payload(record: AuditRecord) -> dict[str, object]:
    return {
        "timestamp": record.timestamp,
        "query_hash": record.query_hash,
        "sources": record.sources,
        "region": record.region,
        "tenant_id": record.tenant_id,
        "subject": record.subject,
        "decision": record.decision,
        "prev_hash": record.prev_hash,
    }


def hash_query(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
