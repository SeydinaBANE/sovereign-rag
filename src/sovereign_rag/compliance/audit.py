from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path

from sovereign_rag.domain.models import AuditRecord

_GENESIS = "0" * 64


class FileAuditLog:
    """Append-only, hash-chained audit log for AI Act traceability."""

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def record(
        self,
        query_hash: str,
        sources: list[str],
        region: str,
        decision: str,
    ) -> AuditRecord:
        prev_hash = self._last_hash()
        timestamp = datetime.now(UTC).isoformat()
        payload = {
            "timestamp": timestamp,
            "query_hash": query_hash,
            "sources": sources,
            "region": region,
            "decision": decision,
            "prev_hash": prev_hash,
        }
        entry_hash = self._digest(payload)
        record = AuditRecord(hash=entry_hash, **payload)
        with self._path.open("a", encoding="utf-8") as handle:
            handle.write(record.model_dump_json() + "\n")
        return record

    def verify_chain(self) -> bool:
        prev_hash = _GENESIS
        for record in self._entries():
            if record.prev_hash != prev_hash:
                return False
            expected = self._digest(
                {
                    "timestamp": record.timestamp,
                    "query_hash": record.query_hash,
                    "sources": record.sources,
                    "region": record.region,
                    "decision": record.decision,
                    "prev_hash": record.prev_hash,
                }
            )
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

    @staticmethod
    def _digest(payload: Mapping[str, object]) -> str:
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()


def hash_query(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
