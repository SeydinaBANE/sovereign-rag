from sovereign_rag.adapters.fakes import FakeSparseEmbedding


def test_sparse_encoding_is_deterministic():
    encoder = FakeSparseEmbedding(dim=4096)
    first = encoder.encode(["remote work policy"])[0]
    second = encoder.encode(["remote work policy"])[0]
    assert first.indices == second.indices
    assert first.values == second.values


def test_sparse_indices_are_sorted_and_aligned():
    vector = FakeSparseEmbedding(dim=4096).encode(["remote work remote"])[0]
    assert vector.indices == sorted(vector.indices)
    assert len(vector.indices) == len(vector.values)


def test_sparse_repeated_term_increases_weight():
    vector = FakeSparseEmbedding(dim=4096).encode(["remote remote remote"])[0]
    assert max(vector.values) >= 3.0


def test_sparse_empty_text_is_empty():
    vector = FakeSparseEmbedding(dim=4096).encode([""])[0]
    assert vector.indices == []
    assert vector.values == []
