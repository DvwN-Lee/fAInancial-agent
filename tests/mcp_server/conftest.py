import sys
from pathlib import Path

# mcp_server/ must be first so that `import main` resolves to mcp_server/main.py
# rather than agent/main.py (which the root conftest inserts at index 0).
_mcp_server_path = str(Path(__file__).parent.parent.parent / "mcp_server")
if _mcp_server_path in sys.path:
    sys.path.remove(_mcp_server_path)
sys.path.insert(0, _mcp_server_path)
