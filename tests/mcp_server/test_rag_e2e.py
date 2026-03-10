"""E2E 테스트 — search_documents MCP Tool이 정상 등록되었는지 확인."""


def test_search_documents_tool_registered():
    """search_documents가 MCP Tool로 등록되어 있는지 확인."""
    from main import mcp

    tool_names = [t.name for t in mcp._tool_manager.list_tools()]
    assert "search_documents" in tool_names


def test_search_documents_tool_has_params():
    """search_documents Tool의 파라미터가 올바른지 확인."""
    import inspect
    from main import search_documents

    sig = inspect.signature(search_documents)
    params = sig.parameters
    assert "query" in params
    assert "corp_name" in params
    assert "year" in params
