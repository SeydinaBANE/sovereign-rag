from sovereign_rag.compliance import pii
from sovereign_rag.domain.models import PIIEntityType


def test_mask_redacts_email():
    masked, findings = pii.mask("Contact me at jane.doe@example.com please.")
    assert "jane.doe@example.com" not in masked
    assert "[REDACTED:EMAIL]" in masked
    assert any(f.entity_type is PIIEntityType.EMAIL for f in findings)


def test_mask_without_pii_is_noop():
    text = "This sentence has no personal data."
    masked, findings = pii.mask(text)
    assert masked == text
    assert findings == []


def test_detect_iban():
    findings = pii.detect("IBAN FR7630006000011234567890189 on file")
    assert any(f.entity_type is PIIEntityType.IBAN for f in findings)
