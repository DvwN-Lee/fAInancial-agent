"""RAG 검색 — FAISS 인덱스 기반 시맨틱 검색."""

import json
import os
from pathlib import Path

import faiss
import numpy as np
import voyageai

FAISS_DIR = Path(__file__).parent.parent / "data" / "faiss"
EMBEDDING_MODEL = "voyage-finance-2"
TOP_K = 5
SEARCH_MULTIPLIER = 3  # post-filter용 오버페칭 배수

_index: faiss.Index | None = None
_metadata: list[dict] | None = None
_voyage_client: voyageai.Client | None = None


def _get_voyage_client() -> voyageai.Client:
    global _voyage_client
    if _voyage_client is None:
        api_key = os.getenv("VOYAGE_API_KEY", "")
        if not api_key:
            raise ValueError("VOYAGE_API_KEY 환경변수가 설정되지 않았습니다")
        _voyage_client = voyageai.Client(api_key=api_key)
    return _voyage_client


def _get_index() -> faiss.Index:
    """FAISS 인덱스를 lazy load한다. 1회 로드 후 메모리 유지."""
    global _index
    if _index is None:
        index_path = FAISS_DIR / "index.faiss"
        if not index_path.exists():
            raise FileNotFoundError(
                "FAISS 인덱스가 없습니다. "
                "scripts/index_documents.py를 먼저 실행하세요."
            )
        _index = faiss.read_index(str(index_path))
    return _index


def _load_metadata(path: Path | None = None) -> list[dict]:
    """메타데이터를 로드한다."""
    global _metadata
    if _metadata is None:
        meta_path = path or (FAISS_DIR / "metadata.json")
        if not meta_path.exists():
            raise FileNotFoundError("metadata.json이 없습니다.")
        _metadata = json.loads(meta_path.read_text())
    return _metadata


def _embed_query(query: str) -> list[float]:
    """쿼리를 임베딩한다."""
    client = _get_voyage_client()
    result = client.embed(
        [query],
        model=EMBEDDING_MODEL,
        input_type="query",
    )
    return result.embeddings[0]


def rag_search(
    query: str,
    corp_name: str | None = None,
    year: str | None = None,
    top_k: int = TOP_K,
) -> str:
    """공시 문서에서 시맨틱 검색을 수행한다."""
    try:
        index = _get_index()
        metadata = _load_metadata()
        query_vec = np.array([_embed_query(query)], dtype=np.float32)
    except FileNotFoundError as e:
        return str(e)
    except Exception as e:
        return f"검색 오류: {e}"

    faiss.normalize_L2(query_vec)

    # 오버페칭 후 post-filter
    search_k = min(top_k * SEARCH_MULTIPLIER, index.ntotal)
    distances, indices = index.search(query_vec, search_k)

    results = []
    for dist, idx in zip(distances[0], indices[0]):
        if idx == -1 or idx >= len(metadata):
            continue
        meta = metadata[idx]

        # post-filter
        if corp_name and meta.get("corp_name") != corp_name:
            continue
        if year and meta.get("year") != year:
            continue

        results.append((dist, meta))
        if len(results) >= top_k:
            break

    if not results:
        filters = []
        if corp_name:
            filters.append(f"기업: {corp_name}")
        if year:
            filters.append(f"연도: {year}")
        filter_str = ", ".join(filters) if filters else "전체"
        return f"검색 결과 없음 ({filter_str})"

    lines = [f"'{query}' 관련 공시 내용 ({len(results)}건):"]
    for i, (score, meta) in enumerate(results, 1):
        lines.append(f"\n--- [{i}] 유사도: {score:.3f} ---")
        lines.append(f"기업: {meta.get('corp_name', '')}")
        lines.append(f"연도: {meta.get('year', '')}")
        lines.append(f"보고서: {meta.get('report_nm', '')}")
        lines.append(f"출처: {meta.get('source_file', '')}")
        lines.append(f"내용: {meta.get('text', '')}")

    return "\n".join(lines)
