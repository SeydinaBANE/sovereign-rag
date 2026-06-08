from pathlib import Path

from sovereign_rag.compliance.audit import FileAuditLog, hash_query


def test_audit_chain_is_valid_after_records(tmp_path: Path):
    log = FileAuditLog(tmp_path / "audit.log")
    log.record(hash_query("q1"), ["a.md"], "eu-west", "answered")
    log.record(hash_query("q2"), ["b.md"], "eu-west", "refused:no_context")
    assert log.verify_chain() is True


def test_audit_chain_detects_tampering(tmp_path: Path):
    path = tmp_path / "audit.log"
    log = FileAuditLog(path)
    log.record(hash_query("q1"), ["a.md"], "eu-west", "answered")
    tampered = path.read_text(encoding="utf-8").replace("answered", "deleted")
    path.write_text(tampered, encoding="utf-8")
    assert log.verify_chain() is False


def test_empty_audit_chain_is_valid(tmp_path: Path):
    assert FileAuditLog(tmp_path / "audit.log").verify_chain() is True
