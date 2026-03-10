from scripts.chunker import chunk_text


def test_chunk_text_basic():
    text = "가" * 1000
    chunks = chunk_text(text, chunk_size=500, overlap=100)

    assert len(chunks) == 3  # 500 + 500 + 끝 (overlap 고려)
    assert all(len(c) <= 500 for c in chunks)


def test_chunk_text_short():
    text = "짧은 텍스트"
    chunks = chunk_text(text, chunk_size=500, overlap=100)

    assert len(chunks) == 1
    assert chunks[0] == "짧은 텍스트"


def test_chunk_text_overlap():
    text = "가" * 600
    chunks = chunk_text(text, chunk_size=500, overlap=100)

    assert len(chunks) == 2
    # 첫 청크 끝 100자 == 둘째 청크 앞 100자
    assert chunks[0][-100:] == chunks[1][:100]


def test_chunk_text_empty():
    chunks = chunk_text("", chunk_size=500, overlap=100)
    assert chunks == []
