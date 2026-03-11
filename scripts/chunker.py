"""텍스트 청킹 — 고정 크기 + 오버랩."""


def chunk_text(
    text: str, chunk_size: int = 500, overlap: int = 100
) -> list[str]:
    """텍스트를 고정 크기 청크로 분할한다.

    Args:
        text: 분할할 텍스트
        chunk_size: 청크 최대 길이 (글자 수)
        overlap: 청크 간 오버랩 길이 (글자 수)
    """
    if not text:
        return []

    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - overlap

    return chunks
