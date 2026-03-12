"""agent/graph.py StateGraph 단위 테스트."""

from unittest.mock import patch, AsyncMock, MagicMock

import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from graph import (
    AgentState,
    agent_node,
    tool_node,
    should_continue,
    run_graph,
    _mcp_to_tool_defs,
    SYSTEM_PROMPT,
)


# --- _mcp_to_tool_defs 테스트 ---


class TestMcpToToolDefs:
    def test_converts_mcp_tools_to_langchain_format(self):
        """MCP tool 목록이 langchain bind_tools 형식으로 변환된다."""
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
        result = _mcp_to_tool_defs(mcp_tools)
        assert len(result) == 1
        assert result[0]["function"]["name"] == "get_financials"
        assert result[0]["type"] == "function"

    def test_empty_tools_returns_empty_list(self):
        """빈 MCP tool 목록 → 빈 리스트."""
        assert _mcp_to_tool_defs([]) == []


# --- should_continue 테스트 ---


class TestShouldContinue:
    def test_no_tool_calls_returns_end(self):
        """tool_calls 없으면 END 반환."""
        state: AgentState = {
            "messages": [AIMessage(content="응답입니다.")]
        }
        assert should_continue(state) == "end"

    def test_with_tool_calls_returns_tools(self):
        """tool_calls 있으면 'tools' 반환."""
        msg = AIMessage(
            content="",
            tool_calls=[{"name": "get_financials", "args": {"corp_name": "삼성전자"}, "id": "1"}],
        )
        state: AgentState = {"messages": [msg]}
        assert should_continue(state) == "tools"


# --- tool_node 테스트 ---


class TestToolNode:
    @pytest.mark.asyncio
    @patch("graph.call_mcp_tool", new_callable=AsyncMock)
    async def test_tool_node_calls_mcp(self, mock_call):
        """tool_node가 MCP tool을 호출하고 ToolMessage를 반환한다."""
        mock_call.return_value = "삼성전자 매출: 300조"
        msg = AIMessage(
            content="",
            tool_calls=[{"name": "get_financials", "args": {"corp_name": "삼성전자"}, "id": "tc1"}],
        )
        state: AgentState = {"messages": [HumanMessage(content="매출"), msg]}

        result = await tool_node(state)

        assert len(result["messages"]) == 1
        assert isinstance(result["messages"][0], ToolMessage)
        assert "300조" in result["messages"][0].content
        assert result["messages"][0].tool_call_id == "tc1"

    @pytest.mark.asyncio
    @patch("graph.call_mcp_tool", new_callable=AsyncMock)
    async def test_tool_node_handles_exception(self, mock_call):
        """MCP 호출 실패 시 에러 문자열을 ToolMessage로 반환한다."""
        mock_call.side_effect = ConnectionError("MCP 서버 연결 실패")
        msg = AIMessage(
            content="",
            tool_calls=[{"name": "get_financials", "args": {}, "id": "tc2"}],
        )
        state: AgentState = {"messages": [msg]}

        result = await tool_node(state)

        assert "오류가 발생했습니다" in result["messages"][0].content

    @pytest.mark.asyncio
    @patch("graph.call_mcp_tool", new_callable=AsyncMock)
    async def test_tool_node_multiple_calls(self, mock_call):
        """복수 tool_calls를 모두 처리한다."""
        mock_call.side_effect = ["매출 300조", "주가 80,000원"]
        msg = AIMessage(
            content="",
            tool_calls=[
                {"name": "get_financials", "args": {}, "id": "tc1"},
                {"name": "get_stock_price", "args": {}, "id": "tc2"},
            ],
        )
        state: AgentState = {"messages": [msg]}

        result = await tool_node(state)

        assert len(result["messages"]) == 2


# --- agent_node 테스트 ---


class TestAgentNode:
    @pytest.mark.asyncio
    @patch("graph.list_mcp_tools", new_callable=AsyncMock)
    @patch("graph._get_model")
    async def test_agent_node_returns_ai_message(self, mock_get_model, mock_list_tools):
        """agent_node가 AIMessage를 반환한다."""
        mock_list_tools.return_value = []

        mock_model = AsyncMock()
        mock_model.ainvoke.return_value = AIMessage(content="안녕하세요!")
        mock_get_model.return_value = mock_model

        state: AgentState = {"messages": [HumanMessage(content="안녕")]}

        result = await agent_node(state)

        assert len(result["messages"]) == 1
        assert result["messages"][0].content == "안녕하세요!"

    @pytest.mark.asyncio
    @patch("graph.list_mcp_tools", new_callable=AsyncMock)
    @patch("graph._get_model")
    async def test_agent_node_includes_system_prompt(self, mock_get_model, mock_list_tools):
        """agent_node가 시스템 프롬프트를 포함하여 LLM에 전달한다."""
        mock_list_tools.return_value = []

        mock_model = AsyncMock()
        mock_model.ainvoke.return_value = AIMessage(content="응답")
        mock_get_model.return_value = mock_model

        state: AgentState = {"messages": [HumanMessage(content="테스트")]}
        await agent_node(state)

        call_args = mock_model.ainvoke.call_args[0][0]
        assert call_args[0].content == SYSTEM_PROMPT

    @pytest.mark.asyncio
    @patch("graph.list_mcp_tools", new_callable=AsyncMock)
    @patch("graph._get_model")
    async def test_agent_node_binds_tools_when_available(self, mock_get_model, mock_list_tools):
        """MCP tool이 있으면 bind_tools가 호출된다."""
        mock_list_tools.return_value = [
            {
                "name": "get_financials",
                "description": "재무제표 조회",
                "input_schema": {
                    "type": "object",
                    "properties": {"corp_name": {"type": "string"}},
                },
            }
        ]

        mock_bound = AsyncMock()
        mock_bound.ainvoke.return_value = AIMessage(content="응답")

        mock_model = MagicMock()
        mock_model.bind_tools.return_value = mock_bound
        mock_get_model.return_value = mock_model

        state: AgentState = {"messages": [HumanMessage(content="삼성전자 매출")]}
        result = await agent_node(state)

        mock_model.bind_tools.assert_called_once()
        tool_defs = mock_model.bind_tools.call_args[0][0]
        assert len(tool_defs) == 1
        assert tool_defs[0]["function"]["name"] == "get_financials"
        assert result["messages"][0].content == "응답"


# --- run_graph 테스트 ---


class TestRunGraph:
    @pytest.mark.asyncio
    @patch("graph.list_mcp_tools", new_callable=AsyncMock)
    @patch("graph._get_model")
    async def test_run_graph_returns_string(self, mock_get_model, mock_list_tools):
        """run_graph가 문자열을 반환한다."""
        mock_list_tools.return_value = []

        mock_model = AsyncMock()
        mock_model.ainvoke.return_value = AIMessage(content="삼성전자 매출은 300조원입니다.")
        mock_get_model.return_value = mock_model

        result = await run_graph("삼성전자 매출", session_id="test-session-1")

        assert isinstance(result, str)
        assert "300조" in result

    @pytest.mark.asyncio
    @patch("graph.list_mcp_tools", new_callable=AsyncMock)
    @patch("graph._get_model")
    async def test_run_graph_session_continuity(self, mock_get_model, mock_list_tools):
        """동일 session_id로 대화 히스토리가 유지된다."""
        mock_list_tools.return_value = []

        mock_model = AsyncMock()
        mock_model.ainvoke.side_effect = [
            AIMessage(content="매출은 300조원입니다."),
            AIMessage(content="전년 대비 10% 증가했습니다."),
        ]
        mock_get_model.return_value = mock_model

        sid = "test-session-continuity"
        await run_graph("삼성전자 매출", session_id=sid)
        result = await run_graph("작년 대비?", session_id=sid)

        assert "10%" in result
        # 두 번째 호출 시 이전 메시지가 포함되어 전달
        second_call_messages = mock_model.ainvoke.call_args_list[1][0][0]
        # system + human1 + ai1 + human2 = 4개 이상
        assert len(second_call_messages) >= 4

    @pytest.mark.asyncio
    @patch("graph.list_mcp_tools", new_callable=AsyncMock)
    @patch("graph._get_model")
    async def test_run_graph_empty_content(self, mock_get_model, mock_list_tools):
        """AIMessage.content가 빈 문자열이면 빈 문자열을 반환한다."""
        mock_list_tools.return_value = []

        mock_model = AsyncMock()
        mock_model.ainvoke.return_value = AIMessage(content="")
        mock_get_model.return_value = mock_model

        result = await run_graph("테스트", session_id="test-empty")

        assert result == ""

    @pytest.mark.asyncio
    @patch("graph.graph")
    async def test_run_graph_recursion_error(self, mock_graph):
        """GraphRecursionError 발생 시 사용자 친화적 메시지를 반환한다."""
        from langgraph.errors import GraphRecursionError

        mock_graph.ainvoke = AsyncMock(
            side_effect=GraphRecursionError("Recursion limit reached")
        )

        result = await run_graph("테스트", session_id="test-recursion")

        assert "최대 반복" in result

    @pytest.mark.asyncio
    @patch("graph._get_langfuse_handler")
    @patch("graph.list_mcp_tools", new_callable=AsyncMock)
    @patch("graph._get_model")
    async def test_run_graph_without_langfuse(self, mock_get_model, mock_list_tools, mock_langfuse):
        """LANGFUSE 미설정 시 callbacks 없이 정상 실행."""
        mock_langfuse.return_value = None
        mock_list_tools.return_value = []
        mock_model = AsyncMock()
        mock_model.ainvoke.return_value = AIMessage(content="응답")
        mock_get_model.return_value = mock_model

        result = await run_graph("테스트", session_id="no-langfuse")
        assert result == "응답"

    @pytest.mark.asyncio
    @patch("graph._get_langfuse_handler")
    @patch("graph.list_mcp_tools", new_callable=AsyncMock)
    @patch("graph._get_model")
    async def test_run_graph_with_langfuse(self, mock_get_model, mock_list_tools, mock_langfuse):
        """LANGFUSE 설정 시 callbacks에 handler가 포함된다."""
        mock_handler = MagicMock()
        mock_langfuse.return_value = mock_handler
        mock_list_tools.return_value = []
        mock_model = AsyncMock()
        mock_model.ainvoke.return_value = AIMessage(content="응답")
        mock_get_model.return_value = mock_model

        result = await run_graph("테스트", session_id="with-langfuse")
        assert result == "응답"
        # handler가 _get_langfuse_handler로 반환되었는지 확인
        mock_langfuse.assert_called_once_with("with-langfuse")
