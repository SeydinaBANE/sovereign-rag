from __future__ import annotations

from sovereign_rag.domain.exceptions import ResidencyError


def ensure_allowed(region: str, allowed: list[str]) -> str:
    if region not in allowed:
        raise ResidencyError(region, allowed)
    return region


def filter_regions(requested: list[str] | None, allowed: list[str]) -> list[str]:
    if requested is None:
        return list(allowed)
    invalid = [region for region in requested if region not in allowed]
    if invalid:
        raise ResidencyError(invalid[0], allowed)
    return requested
