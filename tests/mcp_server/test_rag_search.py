import json
from pathlib import Path
from unittest.mock import patch

import faiss
import numpy as np
import pytest

from rag_search import _load_metadata, rag_search


@pytest.fixture
def fake_faiss_dir(tmp_path):
    """3개 청크를 가진 테스트용 FAISS 인덱스를 생성한다."""
    dim = 768
    vectors = np.random.rand(3, dim).astype(np.float32)
    faiss.normalize_L2(vectors)
    index = faiss.IndexFlatIP(dim)
    index.add(vectors)
    faiss.write_index(index, str(tmp_path / "index.faiss"))

    metadata = [
        {"chunk_id": 0, "corp_name": "삼성전자", "year": "2024",
         "text": "반도체 수급 변동에 따른 위험"},
        {"chunk_id": 1, "corp_name": "삼성전자", "year": "2023",
         "text": "메모리 반도체 시장 전망"},
        {"chunk_id": 2, "corp_name": "LG화학", "year": "2024",
         "text": "배터리 사업 확장 계획"},
    ]
    (tmp_path / "metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False)
    )
    return tmp_path


def test_load_metadata(fake_faiss_dir):
    meta = _load_metadata(fake_faiss_dir / "metadata.json")
    assert len(meta) == 3
    assert meta[0]["corp_name"] == "삼성전자"


def test_rag_search_filters_by_corp(fake_faiss_dir):
    """corp_name 필터가 동작하는지 확인."""
    fake_embedding = np.random.rand(768).astype(np.float32).tolist()

    with patch("rag_search.FAISS_DIR", fake_faiss_dir), \
         patch("rag_search._embed_query", return_value=fake_embedding), \
         patch("rag_search._index", None), \
         patch("rag_search._metadata", None):
        result = rag_search("위험 요인", corp_name="LG화학")

    assert "LG화학" in result
    assert "배터리" in result


def test_rag_search_no_index(tmp_path):
    """인덱스 미존재 시 명시적 에러."""
    with patch("rag_search.FAISS_DIR", tmp_path):
        result = rag_search("테스트")

    assert "인덱스" in result or "없습니다" in result
