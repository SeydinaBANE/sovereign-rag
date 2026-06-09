from __future__ import annotations

import re

_WORD = re.compile(r"\w+", re.UNICODE)


def tokenize(text: str) -> list[str]:
    return [token.lower() for token in _WORD.findall(text)]
