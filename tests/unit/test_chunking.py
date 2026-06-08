import pytest

from sovereign_rag.services.chunking import chunk_text


def test_chunk_text_nominal_splits_with_overlap():
    text = " ".join(str(index) for index in range(10))
    chunks = chunk_text(text, size=4, overlap=1)
    assert chunks[0] == "0 1 2 3"
    assert chunks[1] == "3 4 5 6"
    assert all(len(chunk.split()) <= 4 for chunk in chunks)


def test_chunk_text_empty_returns_empty():
    assert chunk_text("   ", size=4, overlap=1) == []


def test_chunk_text_invalid_overlap_raises():
    with pytest.raises(ValueError):
        chunk_text("a b c", size=2, overlap=2)
