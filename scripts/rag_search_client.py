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

    # "내용: ..." 블록 추출 (멀티라인 — 다음 "---" 구분자까지)
    contexts = []
    lines = result.split("\n")
    i = 0
    while i < len(lines):
        if lines[i].startswith("내용: "):
            block = [lines[i][4:]]  # "내용: " 이후 첫 줄
            i += 1
            while i < len(lines) and not lines[i].startswith("--- ["):
                block.append(lines[i])
                i += 1
            contexts.append("\n".join(block).strip())
        else:
            i += 1

    return contexts if contexts else [result]
