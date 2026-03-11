"""
KRX 주가 Tool
주가 시세 조회 via FinanceDataReader
"""

import FinanceDataReader as fdr


def krx_price(ticker: str, start_date: str, end_date: str) -> str:
    """KRX 주가 데이터를 조회한다."""
    try:
        df = fdr.DataReader(ticker, start_date, end_date)
    except Exception as e:
        return f"주가 데이터 조회 실패 ({ticker}): {e}"

    if df.empty:
        return f"'{ticker}' 종목의 해당 기간 데이터가 없습니다"

    lines = [f"[{ticker}] 주가 ({start_date} ~ {end_date}), {len(df)}거래일"]
    lines.append(f"  시작가: {df['Close'].iloc[0]:,.0f}")
    lines.append(f"  종가:   {df['Close'].iloc[-1]:,.0f}")
    lines.append(f"  최고가: {df['High'].max():,.0f}")
    lines.append(f"  최저가: {df['Low'].min():,.0f}")
    lines.append(f"  평균거래량: {df['Volume'].mean():,.0f}")

    return "\n".join(lines)
