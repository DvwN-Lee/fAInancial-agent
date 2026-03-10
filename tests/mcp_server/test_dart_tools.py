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
