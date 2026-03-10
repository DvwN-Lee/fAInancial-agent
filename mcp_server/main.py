"""
fAInancial-agent MCP Server
DART 전자공시 + KRX 주가 데이터를 MCP Tool로 제공
Transport: Streamable HTTP
"""

from mcp.server.fastmcp import FastMCP

from dart_tools import dart_financials, dart_search
from krx_tools import krx_price

mcp = FastMCP("fAInancial", stateless_http=True, host="0.0.0.0", port=8001)


@mcp.tool()
def get_financials(corp_name: str, year: str, report_type: str = "annual") -> str:
    """기업의 재무제표(매출액, 영업이익, 당기순이익 등)를 조회합니다.

    Args:
        corp_name: 기업명 (예: 삼성전자, SK하이닉스)
        year: 사업연도 (예: 2024)
        report_type: 보고서 유형 - annual(사업보고서), q1(1분기), half(반기), q3(3분기)
    """
    return dart_financials(corp_name, year, report_type)


@mcp.tool()
def search_disclosures(keyword: str) -> str:
    """DART 전자공시 시스템에서 공시를 검색합니다.

    Args:
        keyword: 검색 키워드 (기업명 또는 공시 관련 키워드)
    """
    return dart_search(keyword)


@mcp.tool()
def get_stock_price(ticker: str, start_date: str, end_date: str) -> str:
    """KRX 주가 데이터를 조회합니다.

    Args:
        ticker: 종목코드 (예: 005930)
        start_date: 조회 시작일 (YYYY-MM-DD)
        end_date: 조회 종료일 (YYYY-MM-DD)
    """
    return krx_price(ticker, start_date, end_date)


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
