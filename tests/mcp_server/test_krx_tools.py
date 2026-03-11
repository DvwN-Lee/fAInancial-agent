from unittest.mock import patch, MagicMock
import pandas as pd
import pytest

from krx_tools import krx_price


@patch("krx_tools.fdr.DataReader")
def test_krx_price_success(mock_reader):
    mock_df = pd.DataFrame(
        {
            "Open": [70000, 71000],
            "High": [72000, 73000],
            "Low": [69000, 70000],
            "Close": [71000, 72000],
            "Volume": [1000000, 1200000],
        },
        index=pd.to_datetime(["2025-01-02", "2025-01-03"]),
    )
    mock_reader.return_value = mock_df

    result = krx_price("005930", "2025-01-02", "2025-01-03")
    assert "005930" in result
    assert "2거래일" in result


@patch("krx_tools.fdr.DataReader")
def test_krx_price_empty(mock_reader):
    mock_reader.return_value = pd.DataFrame()

    result = krx_price("999999", "2025-01-02", "2025-01-03")
    assert "데이터가 없습니다" in result


@patch("krx_tools.fdr.DataReader")
def test_krx_price_exception(mock_reader):
    mock_reader.side_effect = Exception("네트워크 오류")

    result = krx_price("005930", "2025-01-02", "2025-01-03")
    assert "조회 실패" in result
    assert "005930" in result
