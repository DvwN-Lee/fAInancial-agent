"""RAGAS 평가용 — MCP 없이 rag_search를 직접 호출하는 래퍼."""

import sys
from pathlib import Path

# mcp_server/ 모듈 경로 추가
sys.path.insert(0, str(Path(__file__).parent.parent / "mcp_server"))

from rag_search import rag_search as _rag_search


def search_documents_local(
    query: str,
    corp_name: str | None = None,
    year: str | None = None,
) -> list[str]:
    """rag_search를 호출하고 청크 텍스트 리스트로 반환한다."""
    result = _rag_search(query, corp_name, year)

    # "내용: ..." 라인만 추출하여 contexts 리스트로 반환
    contexts = []
    for line in result.split("\n"):
        if line.startswith("내용: "):
            contexts.append(line[4:])

    return contexts if contexts else [result]
