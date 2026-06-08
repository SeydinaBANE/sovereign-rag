import pytest

from sovereign_rag.compliance.data_residency import ensure_allowed, filter_regions
from sovereign_rag.domain.exceptions import ResidencyError


def test_ensure_allowed_passes_for_allowed_region():
    assert ensure_allowed("eu-west", ["eu-west", "eu-central"]) == "eu-west"


def test_ensure_allowed_rejects_foreign_region():
    with pytest.raises(ResidencyError):
        ensure_allowed("us-east", ["eu-west"])


def test_filter_regions_defaults_to_all_allowed():
    assert filter_regions(None, ["eu-west", "eu-central"]) == ["eu-west", "eu-central"]


def test_filter_regions_rejects_disallowed_request():
    with pytest.raises(ResidencyError):
        filter_regions(["us-east"], ["eu-west"])
