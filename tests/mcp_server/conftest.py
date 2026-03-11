import sys
from pathlib import Path

_root = Path(__file__).parent.parent.parent

# mcp_server/ must be first so that `import main` resolves to mcp_server/main.py
# rather than agent/main.py (which the root conftest and tests/agent/conftest insert).
_mcp_server_path = str(_root / "mcp_server")
_agent_path = str(_root / "agent")

# Remove both paths then re-insert in the correct order:
# mcp_server at 0 so its main.py wins, agent after it.
for _p in [_mcp_server_path, _agent_path]:
    while _p in sys.path:
        sys.path.remove(_p)

sys.path.insert(0, _agent_path)
sys.path.insert(0, _mcp_server_path)
