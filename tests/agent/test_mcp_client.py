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


@pytest.mark.asyncio
async def test_call_mcp_tool_returns_text():
    mock_block = MagicMock()
    mock_block.text = "삼성전자 2024 재무 결과"

    mock_result = MagicMock()
    mock_result.content = [mock_block]

    mock_session = AsyncMock()
    mock_session.initialize = AsyncMock()
    mock_session.call_tool = AsyncMock(return_value=mock_result)

    with patch("mcp_client.streamable_http_client") as mock_client, \
         patch("mcp_client.ClientSession") as mock_session_cls:
        mock_client.return_value.__aenter__ = AsyncMock(
            return_value=(MagicMock(), MagicMock(), MagicMock())
        )
        mock_client.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await call_mcp_tool("get_financials", {"corp_name": "삼성전자", "year": "2024"})
        assert "삼성전자" in result
        mock_session.call_tool.assert_called_once_with(
            "get_financials", {"corp_name": "삼성전자", "year": "2024"}
        )
