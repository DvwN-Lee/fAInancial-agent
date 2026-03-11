from unittest.mock import patch, AsyncMock, MagicMock
import pytest

from google.genai import types

from loop import run_agent, _mcp_tools_to_gemini


def _make_text_response(text):
    """function_calls 없이 텍스트만 반환하는 Gemini 응답 mock."""
    response = MagicMock()
    response.function_calls = None
    response.text = text
    return response


def _make_function_call_response(name, args):
    """function_call을 포함하는 Gemini 응답 mock."""
    fc = MagicMock()
    fc.name = name
    fc.args = args

    candidate = MagicMock()
    candidate.content = MagicMock()

    response = MagicMock()
    response.function_calls = [fc]
    response.candidates = [candidate]
    return response


def _mock_client_with(generate_content_mock):
    """_get_client()가 반환할 mock client를 생성."""
    mock_client = MagicMock()
    mock_client.models.generate_content = generate_content_mock
    return MagicMock(return_value=mock_client)


def test_mcp_tools_to_gemini():
    """MCP tool 목록이 Gemini FunctionDeclaration으로 변환되는지 확인."""
    mcp_tools = [
        {
            "name": "get_financials",
            "description": "재무제표 조회",
            "input_schema": {
                "type": "object",
                "properties": {"corp_name": {"type": "string"}},
                "required": ["corp_name"],
            },
        }
    ]
    gemini_tool = _mcp_tools_to_gemini(mcp_tools)
    assert len(gemini_tool.function_declarations) == 1
    assert gemini_tool.function_declarations[0].name == "get_financials"


@pytest.mark.asyncio
@patch("loop.call_mcp_tool", new_callable=AsyncMock)
@patch("loop.list_mcp_tools", new_callable=AsyncMock)
@patch("loop._get_client")
async def test_run_agent_simple_response(mock_get_client, mock_list_tools, mock_call_tool):
    """function_call 없이 바로 텍스트 응답하는 케이스."""
    mock_list_tools.return_value = []
    mock_client = MagicMock()
    mock_client.models.generate_content = MagicMock(
        return_value=_make_text_response("안녕하세요!")
    )
    mock_get_client.return_value = mock_client

    text, contents = await run_agent("안녕")
    assert text == "안녕하세요!"


@pytest.mark.asyncio
@patch("loop.call_mcp_tool", new_callable=AsyncMock)
@patch("loop.list_mcp_tools", new_callable=AsyncMock)
@patch("loop._get_client")
async def test_run_agent_with_tool_call(mock_get_client, mock_list_tools, mock_call_tool):
    """function_call → function_response → 텍스트 응답 흐름."""
    mock_list_tools.return_value = [
        {"name": "get_financials", "description": "재무제표", "input_schema": {}}
    ]
    mock_call_tool.return_value = "삼성전자 매출: 300조"

    fc_response = _make_function_call_response(
        "get_financials", {"corp_name": "삼성전자", "year": "2024"}
    )
    final_response = _make_text_response("삼성전자의 2024년 매출은 300조원입니다.")

    mock_client = MagicMock()
    mock_client.models.generate_content = MagicMock(
        side_effect=[fc_response, final_response]
    )
    mock_get_client.return_value = mock_client

    text, contents = await run_agent("삼성전자 매출 알려줘")
    assert "300조" in text
    mock_call_tool.assert_called_once_with(
        "get_financials", {"corp_name": "삼성전자", "year": "2024"}
    )


@pytest.mark.asyncio
@patch("loop.call_mcp_tool", new_callable=AsyncMock)
@patch("loop.list_mcp_tools", new_callable=AsyncMock)
@patch("loop._get_client")
async def test_run_agent_empty_text(mock_get_client, mock_list_tools, mock_call_tool):
    """response.text가 None인 경우 빈 문자열 반환."""
    mock_list_tools.return_value = []
    mock_client = MagicMock()
    mock_client.models.generate_content = MagicMock(
        return_value=_make_text_response(None)
    )
    mock_get_client.return_value = mock_client

    text, contents = await run_agent("테스트")
    assert text == ""


@pytest.mark.asyncio
@patch("loop.call_mcp_tool", new_callable=AsyncMock)
@patch("loop.list_mcp_tools", new_callable=AsyncMock)
@patch("loop._get_client")
async def test_run_agent_tool_call_exception(mock_get_client, mock_list_tools, mock_call_tool):
    """MCP tool 호출 시 예외 발생 → function_response에 에러 문자열 주입."""
    mock_list_tools.return_value = [
        {"name": "get_financials", "description": "재무제표", "input_schema": {}}
    ]
    mock_call_tool.side_effect = ConnectionError("MCP 서버 연결 실패")

    fc_response = _make_function_call_response(
        "get_financials", {"corp_name": "삼성전자", "year": "2024"}
    )
    final_response = _make_text_response("도구 호출 중 오류가 발생했습니다.")

    mock_client = MagicMock()
    mock_client.models.generate_content = MagicMock(
        side_effect=[fc_response, final_response]
    )
    mock_get_client.return_value = mock_client

    text, contents = await run_agent("삼성전자 매출")
    assert "오류" in text


@pytest.mark.asyncio
@patch("loop.call_mcp_tool", new_callable=AsyncMock)
@patch("loop.list_mcp_tools", new_callable=AsyncMock)
@patch("loop._get_client")
async def test_run_agent_max_iterations(mock_get_client, mock_list_tools, mock_call_tool):
    """무한 루프 방지 — max iterations 도달."""
    mock_list_tools.return_value = [
        {"name": "get_financials", "description": "재무제표", "input_schema": {}}
    ]
    mock_call_tool.return_value = "데이터"

    fc_response = _make_function_call_response(
        "get_financials", {"corp_name": "테스트", "year": "2024"}
    )
    mock_client = MagicMock()
    mock_client.models.generate_content = MagicMock(return_value=fc_response)
    mock_get_client.return_value = mock_client

    text, contents = await run_agent("테스트")
    assert "최대 반복" in text


@pytest.mark.asyncio
@patch("loop.call_mcp_tool", new_callable=AsyncMock)
@patch("loop.list_mcp_tools", new_callable=AsyncMock)
@patch("loop._get_client")
async def test_run_agent_with_history(mock_get_client, mock_list_tools, mock_call_tool):
    """history를 전달하면 contents에 포함되어 Gemini에 전달된다."""
    mock_list_tools.return_value = []
    mock_client = MagicMock()
    mock_client.models.generate_content = MagicMock(
        return_value=_make_text_response("작년 대비 10% 증가했습니다.")
    )
    mock_get_client.return_value = mock_client

    history = [
        types.Content(role="user", parts=[types.Part.from_text(text="삼성전자 매출 알려줘")]),
        types.Content(role="model", parts=[types.Part.from_text(text="300조원입니다.")]),
    ]

    text, contents = await run_agent("작년 대비 어떻게 변했어?", history=history)

    assert "10%" in text
    # contents = history(2) + new user(1) + model response(1) = 4
    assert len(contents) >= 3  # 최소 history + new user message
    # Gemini에 전달된 contents의 첫 항목이 history의 첫 항목
    call_args = mock_client.models.generate_content.call_args
    passed_contents = call_args.kwargs.get("contents") or call_args[1].get("contents")
    assert len(passed_contents) >= 3


@pytest.mark.asyncio
@patch("loop.call_mcp_tool", new_callable=AsyncMock)
@patch("loop.list_mcp_tools", new_callable=AsyncMock)
@patch("loop._get_client")
async def test_run_agent_returns_tuple(mock_get_client, mock_list_tools, mock_call_tool):
    """run_agent가 (text, contents) 튜플을 반환한다."""
    mock_list_tools.return_value = []
    mock_client = MagicMock()
    mock_client.models.generate_content = MagicMock(
        return_value=_make_text_response("응답입니다.")
    )
    mock_get_client.return_value = mock_client

    result = await run_agent("테스트")

    assert isinstance(result, tuple)
    assert len(result) == 2
    text, contents = result
    assert text == "응답입니다."
    assert isinstance(contents, list)
