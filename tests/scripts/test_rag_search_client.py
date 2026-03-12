"""search_documents_local / _parse_contexts 단위 테스트."""

from unittest.mock import patch

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))

from rag_search_client import _parse_contexts, search_documents_local


# --- _parse_contexts 테스트 ---


class TestParseContexts:
    def test_single_result(self):
        result = (
            "'삼성전자' 관련 공시 내용 (1건):\n"
            "\n"
            "--- [1] 유사도: 0.850 ---\n"
            "기업: 삼성전자\n"
            "연도: 2024\n"
            "보고서: 사업보고서\n"
            "출처: doc.html\n"
            "내용: 반도체 사업부문 매출 현황입니다."
        )
        contexts = _parse_contexts(result)
        assert len(contexts) == 1
        assert "반도체 사업부문 매출 현황" in contexts[0]

    def test_multiline_content(self):
        result = (
            "'질문' 관련 공시 내용 (1건):\n"
            "\n"
            "--- [1] 유사도: 0.900 ---\n"
            "기업: 삼성전자\n"
            "내용: 첫 번째 줄\n"
            "두 번째 줄\n"
            "세 번째 줄"
        )
        contexts = _parse_contexts(result)
        assert len(contexts) == 1
        assert "두 번째 줄" in contexts[0]
        assert "세 번째 줄" in contexts[0]

    def test_multiple_results(self):
        result = (
            "'질문' 관련 공시 내용 (2건):\n"
            "\n"
            "--- [1] 유사도: 0.900 ---\n"
            "내용: 첫 번째 청크\n"
            "\n"
            "--- [2] 유사도: 0.800 ---\n"
            "내용: 두 번째 청크"
        )
        contexts = _parse_contexts(result)
        assert len(contexts) == 2
        assert "첫 번째 청크" in contexts[0]
        assert "두 번째 청크" in contexts[1]

    def test_no_content_blocks(self):
        result = "아무런 내용이 없는 문자열"
        contexts = _parse_contexts(result)
        assert contexts == []

    def test_empty_string(self):
        assert _parse_contexts("") == []


# --- search_documents_local 테스트 ---


class TestSearchDocumentsLocal:
    @patch("rag_search_client._rag_search")
    def test_error_prefix_returns_empty(self, mock_rag):
        mock_rag.return_value = "검색 오류: VOYAGE_API_KEY 환경변수가 설정되지 않았습니다"
        result = search_documents_local("삼성전자 매출")
        assert result == []

    @patch("rag_search_client._rag_search")
    def test_no_results_returns_empty(self, mock_rag):
        mock_rag.return_value = "검색 결과 없음 (기업: 삼성전자)"
        result = search_documents_local("삼성전자 매출", corp_name="삼성전자")
        assert result == []

    @patch("rag_search_client._rag_search")
    def test_normal_result_parses_contexts(self, mock_rag):
        mock_rag.return_value = (
            "'매출' 관련 공시 내용 (1건):\n"
            "\n"
            "--- [1] 유사도: 0.850 ---\n"
            "기업: 삼성전자\n"
            "내용: 매출액은 225조원입니다."
        )
        result = search_documents_local("매출")
        assert len(result) == 1
        assert "225조원" in result[0]

    @patch("rag_search_client._rag_search")
    def test_file_not_found_error_returns_empty(self, mock_rag):
        """FileNotFoundError는 _ERROR_PREFIXES로 시작하지 않지만, 파싱 결과 빈 리스트."""
        mock_rag.return_value = "FAISS 인덱스가 없습니다. scripts/index_documents.py를 먼저 실행하세요."
        result = search_documents_local("삼성전자")
        assert result == []
