import importlib
import importlib.util
import sys
from pathlib import Path


def _load_mcp_server_main():
    """Load mcp_server/main.py directly by file path, bypassing sys.modules cache."""
    mcp_main_path = Path(__file__).parent.parent.parent / "mcp_server" / "main.py"
    spec = importlib.util.spec_from_file_location("mcp_server_main", mcp_main_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_mcp_server_has_tools():
    """서버 모듈이 정상 임포트되고 tools가 등록되어 있는지 확인."""
    mod = _load_mcp_server_main()

    assert mod.mcp.name == "fAInancial"

    # FastMCP의 내부 tool registry 확인
    # FastMCP stores tools internally - we verify by checking the tool functions exist
    assert callable(mod.get_financials)
    assert callable(mod.search_disclosures)
    assert callable(mod.get_stock_price)
