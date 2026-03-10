from unittest.mock import patch, MagicMock, AsyncMock
import pytest

from mcp_client import list_mcp_tools, call_mcp_tool, MCP_SERVER_URL


def test_mcp_server_url_default():
    assert "localhost" in MCP_SERVER_URL or "mcp-server" in MCP_SERVER_URL


@pytest.mark.asyncio
async def test_list_mcp_tools_returns_list():
    mock_tool = MagicMock()
    mock_tool.name = "get_financials"
    mock_tool.description = "재무제표 조회"
    mock_tool.inputSchema = {
        "type": "object",
        "properties": {"corp_name": {"type": "string"}},
        "required": ["corp_name"],
    }

    mock_tools_result = MagicMock()
    mock_tools_result.tools = [mock_tool]

    mock_session = AsyncMock()
    mock_session.initialize = AsyncMock()
    mock_session.list_tools = AsyncMock(return_value=mock_tools_result)

    with patch("mcp_client.streamable_http_client") as mock_client, \
         patch("mcp_client.ClientSession") as mock_session_cls:
        mock_client.return_value.__aenter__ = AsyncMock(
            return_value=(MagicMock(), MagicMock(), MagicMock())
        )
        mock_client.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        tools = await list_mcp_tools()
        assert len(tools) == 1
        assert tools[0]["name"] == "get_financials"
        assert "input_schema" in tools[0]
