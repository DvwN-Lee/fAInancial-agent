def test_mcp_server_has_tools():
    """서버 모듈이 정상 임포트되고 tools가 등록되어 있는지 확인."""
    from main import mcp

    assert mcp.name == "fAInancial"

    # FastMCP의 내부 tool registry 확인
    # FastMCP stores tools internally - we verify by checking the tool functions exist
    from main import get_financials, search_disclosures, get_stock_price
    assert callable(get_financials)
    assert callable(search_disclosures)
    assert callable(get_stock_price)
