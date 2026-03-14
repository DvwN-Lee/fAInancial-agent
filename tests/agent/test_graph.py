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
    _get_langfuse_handler,
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

        text, tools_used = result
        assert isinstance(text, str)
        assert "300조" in text
        assert isinstance(tools_used, list)

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

        text, tools_used = result
        assert "10%" in text
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

        text, tools_used = result
        assert text == ""
        assert tools_used == []

    @pytest.mark.asyncio
    @patch("graph.graph")
    async def test_run_graph_recursion_error(self, mock_graph):
        """GraphRecursionError 발생 시 사용자 친화적 메시지를 반환한다."""
        from langgraph.errors import GraphRecursionError

        mock_graph.ainvoke = AsyncMock(
            side_effect=GraphRecursionError("Recursion limit reached")
        )

        result = await run_graph("테스트", session_id="test-recursion")

        text, tools_used = result
        assert "최대 반복" in text
        assert tools_used == []

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

        text, tools_used = await run_graph("테스트", session_id="no-langfuse")
        assert text == "응답"

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

        text, tools_used = await run_graph("테스트", session_id="with-langfuse")
        assert text == "응답"
        # handler가 _get_langfuse_handler로 반환되었는지 확인
        mock_langfuse.assert_called_once_with("with-langfuse")


# --- _get_langfuse_handler 단위 테스트 ---


class TestGetLangfuseHandler:
    def test_returns_none_when_langfuse_not_available(self):
        """langfuse 미설치 시 None 반환."""
        import graph
        original = graph._LANGFUSE_AVAILABLE
        try:
            graph._LANGFUSE_AVAILABLE = False
            result = _get_langfuse_handler("session-1")
            assert result is None
        finally:
            graph._LANGFUSE_AVAILABLE = original

    def test_returns_none_when_keys_missing(self):
        """LANGFUSE_PUBLIC_KEY/SECRET_KEY 미설정 시 None 반환."""
        with patch.dict("os.environ", {}, clear=False):
            # 환경변수에서 키 제거
            import os
            env_backup = {k: os.environ.pop(k) for k in ["LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY"] if k in os.environ}
            try:
                result = _get_langfuse_handler("session-2")
                assert result is None
            finally:
                os.environ.update(env_backup)

    def test_initializes_langfuse_singleton_before_handler(self):
        """v3: Langfuse() 싱글턴을 초기화한 후 CallbackHandler()를 생성한다."""
        import graph
        original_available = graph._LANGFUSE_AVAILABLE
        mock_langfuse_cls = MagicMock()
        mock_handler_cls = MagicMock()
        original_handler = getattr(graph, "LangfuseCallbackHandler", None)
        try:
            graph._LANGFUSE_AVAILABLE = True
            graph.LangfuseCallbackHandler = mock_handler_cls
            with patch.dict("os.environ", {"LANGFUSE_PUBLIC_KEY": "pk", "LANGFUSE_SECRET_KEY": "sk", "LANGFUSE_HOST": "http://langfuse:3000"}), \
                 patch("graph.Langfuse", mock_langfuse_cls):
                _get_langfuse_handler("session-init")
                mock_langfuse_cls.assert_called_once()
                mock_handler_cls.assert_called_once()
        finally:
            graph._LANGFUSE_AVAILABLE = original_available
            if original_handler is None:
                delattr(graph, "LangfuseCallbackHandler")
            else:
                graph.LangfuseCallbackHandler = original_handler

    def test_passes_session_id_via_metadata(self):
        """v3: session_id가 config metadata의 langfuse_session_id로 전달된다."""
        import asyncio

        async def _run():
            mock_handler = MagicMock()
            captured_config = {}

            async def fake_ainvoke(inputs, config=None):
                captured_config.update(config or {})
                return {"messages": [AIMessage(content="응답")]}

            with patch("graph._get_langfuse_handler", return_value=mock_handler), \
                 patch("graph.graph") as mock_graph:
                mock_graph.ainvoke = fake_ainvoke
                await run_graph("테스트", session_id="sess-abc-123")

            metadata = captured_config.get("metadata", {})
            assert metadata.get("langfuse_session_id") == "sess-abc-123"

        asyncio.get_event_loop().run_until_complete(_run())

    def test_returns_none_when_constructor_raises(self):
        """LangfuseCallbackHandler 생성자 예외 시 None 반환 (graceful degradation)."""
        import graph
        original_available = graph._LANGFUSE_AVAILABLE
        mock_handler_cls = MagicMock(side_effect=Exception("connection error"))
        original_cls = getattr(graph, "LangfuseCallbackHandler", None)
        try:
            graph._LANGFUSE_AVAILABLE = True
            graph.LangfuseCallbackHandler = mock_handler_cls
            with patch.dict("os.environ", {"LANGFUSE_PUBLIC_KEY": "pk", "LANGFUSE_SECRET_KEY": "sk"}):
                result = _get_langfuse_handler("session-3")
                assert result is None
        finally:
            graph._LANGFUSE_AVAILABLE = original_available
            if original_cls is None:
                delattr(graph, "LangfuseCallbackHandler")
            else:
                graph.LangfuseCallbackHandler = original_cls

    def test_injects_callbacks_into_config(self):
        """LangFuse handler 반환 시 run_graph config에 callbacks가 주입된다."""
        import asyncio

        async def _run():
            mock_handler = MagicMock()
            captured_config = {}

            async def fake_ainvoke(inputs, config=None):
                captured_config.update(config or {})
                return {"messages": [AIMessage(content="응답")]}

            with patch("graph._get_langfuse_handler", return_value=mock_handler), \
                 patch("graph.graph") as mock_graph, \
                 patch("graph.list_mcp_tools", new_callable=AsyncMock, return_value=[]), \
                 patch("graph._get_model") as mock_get_model:
                mock_graph.ainvoke = fake_ainvoke
                mock_model = AsyncMock()
                mock_model.ainvoke.return_value = AIMessage(content="응답")
                mock_get_model.return_value = mock_model

                await run_graph("테스트", session_id="cb-test")

            assert "callbacks" in captured_config
            assert captured_config["callbacks"] == [mock_handler]

        asyncio.get_event_loop().run_until_complete(_run())
