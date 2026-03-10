from unittest.mock import patch, AsyncMock, MagicMock
import pytest

from loop import run_agent


def _make_text_block(text):
    block = MagicMock()
    block.type = "text"
    block.text = text
    return block


def _make_tool_block(tool_id, name, input_data):
    block = MagicMock()
    block.type = "tool_use"
    block.id = tool_id
    block.name = name
    block.input = input_data
    return block


@pytest.mark.asyncio
@patch("loop.call_mcp_tool", new_callable=AsyncMock)
@patch("loop.list_mcp_tools", new_callable=AsyncMock)
@patch("loop.client")
async def test_run_agent_simple_response(mock_client, mock_list_tools, mock_call_tool):
    """tool_use 없이 바로 end_turn하는 케이스."""
    mock_list_tools.return_value = []

    mock_response = MagicMock()
    mock_response.stop_reason = "end_turn"
    mock_response.content = [_make_text_block("안녕하세요!")]
    mock_client.messages.create = MagicMock(return_value=mock_response)

    result = await run_agent("안녕")
    assert result == "안녕하세요!"


@pytest.mark.asyncio
@patch("loop.call_mcp_tool", new_callable=AsyncMock)
@patch("loop.list_mcp_tools", new_callable=AsyncMock)
@patch("loop.client")
async def test_run_agent_with_tool_call(mock_client, mock_list_tools, mock_call_tool):
    """tool_use → tool_result → end_turn 흐름."""
    mock_list_tools.return_value = [
        {"name": "get_financials", "description": "재무제표", "input_schema": {}}
    ]
    mock_call_tool.return_value = "삼성전자 매출: 300조"

    tool_response = MagicMock()
    tool_response.stop_reason = "tool_use"
    tool_response.content = [
        _make_tool_block("tool_1", "get_financials", {"corp_name": "삼성전자", "year": "2024"})
    ]

    final_response = MagicMock()
    final_response.stop_reason = "end_turn"
    final_response.content = [_make_text_block("삼성전자의 2024년 매출은 300조원입니다.")]

    mock_client.messages.create = MagicMock(side_effect=[tool_response, final_response])

    result = await run_agent("삼성전자 매출 알려줘")
    assert "300조" in result
    mock_call_tool.assert_called_once_with("get_financials", {"corp_name": "삼성전자", "year": "2024"})


@pytest.mark.asyncio
@patch("loop.call_mcp_tool", new_callable=AsyncMock)
@patch("loop.list_mcp_tools", new_callable=AsyncMock)
@patch("loop.client")
async def test_run_agent_unexpected_stop_reason(mock_client, mock_list_tools, mock_call_tool):
    """stop_reason이 end_turn도 tool_use도 아닌 경우 (max_tokens 등)."""
    mock_list_tools.return_value = []

    mock_response = MagicMock()
    mock_response.stop_reason = "max_tokens"
    mock_response.content = [_make_text_block("잘린 응답입니다")]
    mock_client.messages.create = MagicMock(return_value=mock_response)

    result = await run_agent("긴 질문")
    assert result == "잘린 응답입니다"


@pytest.mark.asyncio
@patch("loop.call_mcp_tool", new_callable=AsyncMock)
@patch("loop.list_mcp_tools", new_callable=AsyncMock)
@patch("loop.client")
async def test_run_agent_tool_call_exception(mock_client, mock_list_tools, mock_call_tool):
    """MCP tool 호출 시 예외 발생 → tool_result에 에러 문자열 주입."""
    mock_list_tools.return_value = [
        {"name": "get_financials", "description": "재무제표", "input_schema": {}}
    ]
    mock_call_tool.side_effect = ConnectionError("MCP 서버 연결 실패")

    tool_response = MagicMock()
    tool_response.stop_reason = "tool_use"
    tool_response.content = [
        _make_tool_block("tool_1", "get_financials", {"corp_name": "삼성전자", "year": "2024"})
    ]

    final_response = MagicMock()
    final_response.stop_reason = "end_turn"
    final_response.content = [_make_text_block("도구 호출 중 오류가 발생했습니다.")]

    mock_client.messages.create = MagicMock(side_effect=[tool_response, final_response])

    result = await run_agent("삼성전자 매출")
    assert "오류" in result


@pytest.mark.asyncio
@patch("loop.call_mcp_tool", new_callable=AsyncMock)
@patch("loop.list_mcp_tools", new_callable=AsyncMock)
@patch("loop.client")
async def test_run_agent_max_iterations(mock_client, mock_list_tools, mock_call_tool):
    """무한 루프 방지 — max iterations 도달."""
    mock_list_tools.return_value = [
        {"name": "get_financials", "description": "재무제표", "input_schema": {}}
    ]
    mock_call_tool.return_value = "데이터"

    # Always return tool_use (never end_turn)
    tool_response = MagicMock()
    tool_response.stop_reason = "tool_use"
    tool_response.content = [
        _make_tool_block("tool_1", "get_financials", {"corp_name": "테스트", "year": "2024"})
    ]
    mock_client.messages.create = MagicMock(return_value=tool_response)

    result = await run_agent("테스트")
    assert "최대 반복" in result
