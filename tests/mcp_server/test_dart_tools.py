from unittest.mock import patch, MagicMock
import pytest

from dart_tools import resolve_corp_code


SAMPLE_CORP_XML = """<?xml version="1.0" encoding="UTF-8"?>
<result>
  <list>
    <corp_code>00126380</corp_code>
    <corp_name>삼성전자</corp_name>
    <stock_code>005930</stock_code>
    <modify_date>20231215</modify_date>
  </list>
  <list>
    <corp_code>00164779</corp_code>
    <corp_name>SK하이닉스</corp_name>
    <stock_code>000660</stock_code>
    <modify_date>20231215</modify_date>
  </list>
</result>"""


def test_resolve_corp_code_exact_match():
    with patch("dart_tools._load_corp_codes") as mock_load:
        mock_load.return_value = {
            "삼성전자": "00126380",
            "SK하이닉스": "00164779",
        }
        assert resolve_corp_code("삼성전자") == "00126380"


def test_resolve_corp_code_partial_match():
    with patch("dart_tools._load_corp_codes") as mock_load:
        mock_load.return_value = {
            "삼성전자": "00126380",
            "삼성SDI": "00126389",
        }
        # "삼성전자" exact match should win even though "삼성" partial matches 2
        assert resolve_corp_code("삼성전자") == "00126380"


def test_resolve_corp_code_not_found():
    with patch("dart_tools._load_corp_codes") as mock_load:
        mock_load.return_value = {"삼성전자": "00126380"}
        with pytest.raises(ValueError, match="기업을 찾을 수 없습니다"):
            resolve_corp_code("없는회사")


from dart_tools import dart_financials

SAMPLE_FINANCIAL_RESPONSE = {
    "status": "000",
    "message": "정상",
    "list": [
        {
            "account_nm": "매출액",
            "thstrm_amount": "300,000,000,000",
            "frmtrm_amount": "250,000,000,000",
            "bfefrmtrm_amount": "200,000,000,000",
        },
        {
            "account_nm": "영업이익",
            "thstrm_amount": "50,000,000,000",
            "frmtrm_amount": "40,000,000,000",
            "bfefrmtrm_amount": "30,000,000,000",
        },
    ],
}


@patch("dart_tools.resolve_corp_code", return_value="00126380")
@patch("dart_tools.requests.get")
def test_dart_financials_success(mock_get, mock_resolve):
    mock_resp = MagicMock()
    mock_resp.json.return_value = SAMPLE_FINANCIAL_RESPONSE
    mock_resp.raise_for_status = MagicMock()
    mock_get.return_value = mock_resp

    result = dart_financials("삼성전자", "2024")
    assert "매출액" in result
    assert "300,000,000,000" in result
    mock_resolve.assert_called_once_with("삼성전자")


@patch("dart_tools.resolve_corp_code", return_value="00126380")
@patch("dart_tools.requests.get")
def test_dart_financials_api_error(mock_get, mock_resolve):
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"status": "013", "message": "조회된 데이터가 없습니다."}
    mock_resp.raise_for_status = MagicMock()
    mock_get.return_value = mock_resp

    result = dart_financials("삼성전자", "2024")
    assert "조회된 데이터가 없습니다" in result


from dart_tools import dart_search

SAMPLE_SEARCH_RESPONSE = {
    "status": "000",
    "message": "정상",
    "total_count": 2,
    "list": [
        {
            "corp_name": "삼성전자",
            "report_nm": "사업보고서 (2024.12)",
            "rcept_dt": "20250401",
            "rcept_no": "20250401000123",
        },
        {
            "corp_name": "삼성전자",
            "report_nm": "분기보고서 (2025.03)",
            "rcept_dt": "20250515",
            "rcept_no": "20250515000456",
        },
    ],
}


@patch("dart_tools.requests.get")
def test_dart_search_success(mock_get):
    mock_resp = MagicMock()
    mock_resp.json.return_value = SAMPLE_SEARCH_RESPONSE
    mock_resp.raise_for_status = MagicMock()
    mock_get.return_value = mock_resp

    result = dart_search("삼성전자")
    assert "사업보고서" in result
    assert "2건" in result


@patch("dart_tools.requests.get")
def test_dart_search_no_results(mock_get):
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"status": "013", "message": "조회된 데이터가 없습니다."}
    mock_resp.raise_for_status = MagicMock()
    mock_get.return_value = mock_resp

    result = dart_search("없는회사")
    assert "오류" in result or "없습니다" in result
