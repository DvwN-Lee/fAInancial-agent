"""E2E 테스트 — search_documents MCP Tool이 정상 등록되었는지 확인."""

import importlib.util
import inspect
from pathlib import Path


def _load_mcp_main():
    """mcp_server/main.py를 파일 경로로 직접 로드한다."""
    path = Path(__file__).parent.parent.parent / "mcp_server" / "main.py"
    spec = importlib.util.spec_from_file_location("mcp_server_main", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_search_documents_tool_registered():
    """search_documents가 MCP Tool로 등록되어 있는지 확인."""
    mod = _load_mcp_main()
    tool_names = [t.name for t in mod.mcp._tool_manager.list_tools()]
    assert "search_documents" in tool_names


def test_search_documents_tool_has_params():
    """search_documents Tool의 파라미터가 올바른지 확인."""
    mod = _load_mcp_main()
    sig = inspect.signature(mod.search_documents)
    params = sig.parameters
    assert "query" in params
    assert "corp_name" in params
    assert "year" in params
