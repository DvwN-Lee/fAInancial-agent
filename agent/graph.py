"""Agent Graph — LangGraph StateGraph 기반 Agent.

Phase 2-B: loop.py의 while 루프를 StateGraph + nodes + edges로 교체.
MemorySaver가 SessionStore를 대체하여 대화 상태를 자동 관리.
"""

import logging
import os
from typing import Annotated

try:
    from langfuse.callback import CallbackHandler as LangfuseCallbackHandler
    _LANGFUSE_AVAILABLE = True
except ImportError:
    _LANGFUSE_AVAILABLE = False

from langchain_core.messages import AIMessage, SystemMessage, ToolMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.errors import GraphRecursionError
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict

from mcp_client import call_mcp_tool, list_mcp_tools

logger = logging.getLogger(__name__)

MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

SYSTEM_PROMPT = (
    "당신은 한국 금융 데이터 분석 AI 어시스턴트입니다. "
    "DART 전자공시와 KRX 주가 데이터를 조회하는 도구를 사용하여 "
    "사용자의 질문에 정확하게 답변하세요. "
    "데이터를 조회한 후에는 핵심 수치를 포함하여 명확하게 요약해주세요.\n\n"
    "종합 분석을 요청받으면 다음 도구를 모두 활용하세요:\n"
    "1. get_financials — 재무제표 데이터\n"
    "2. get_stock_price — 최근 주가 동향\n"
    "3. search_documents — 공시 원문에서 사업 위험, 전망 등\n"
    "결과를 [재무 현황], [주가 동향], [주요 공시 내용] 섹션으로 구분하여 리포트를 작성하세요."
)

MAX_ITERATIONS = 10

_model_instance = None


class AgentState(TypedDict):
    messages: Annotated[list, add_messages]


def _get_model():
    """ChatGoogleGenerativeAI를 지연 초기화한다."""
    global _model_instance
    if _model_instance is None:
        api_key = os.getenv("GEMINI_API_KEY", "")
        if not api_key:
            raise ValueError("GEMINI_API_KEY 환경변수가 설정되지 않았습니다.")
        _model_instance = ChatGoogleGenerativeAI(
            model=MODEL,
            google_api_key=api_key,
        )
    return _model_instance


def _mcp_to_tool_defs(mcp_tools: list[dict]) -> list[dict]:
    """MCP tool 목록을 langchain bind_tools 호환 형식으로 변환."""
    return [
        {
            "type": "function",
            "function": {
                "name": t["name"],
                "description": t["description"],
                "parameters": t["input_schema"],
            },
        }
        for t in mcp_tools
    ]


async def agent_node(state: AgentState) -> dict:
    """Gemini LLM을 호출하여 응답 또는 tool_calls를 생성한다."""
    mcp_tools = await list_mcp_tools()
    tool_defs = _mcp_to_tool_defs(mcp_tools)

    model = _get_model()
    bound = model.bind_tools(tool_defs) if tool_defs else model

    messages = [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"]
    response = await bound.ainvoke(messages)

    return {"messages": [response]}


async def tool_node(state: AgentState) -> dict:
    """AIMessage의 tool_calls를 MCP로 실행하고 ToolMessage를 반환한다."""
    last_message = state["messages"][-1]
    tool_messages = []

    for tc in last_message.tool_calls:
        try:
            result = await call_mcp_tool(tc["name"], tc["args"])
        except Exception:
            logger.exception("MCP tool '%s' 호출 실패", tc["name"])
            result = f"Tool '{tc['name']}' 호출 중 오류가 발생했습니다."

        tool_messages.append(
            ToolMessage(content=result, tool_call_id=tc["id"])
        )

    return {"messages": tool_messages}


def should_continue(state: AgentState) -> str:
    """마지막 메시지에 tool_calls가 있으면 'tools', 없으면 END."""
    last_message = state["messages"][-1]
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"
    return "end"


# --- Graph 구성 ---
_builder = StateGraph(AgentState)
_builder.add_node("agent", agent_node)
_builder.add_node("tools", tool_node)
_builder.add_edge(START, "agent")
_builder.add_conditional_edges(
    "agent",
    should_continue,
    {"tools": "tools", "end": END},
)
_builder.add_edge("tools", "agent")

checkpointer = InMemorySaver()
graph = _builder.compile(checkpointer=checkpointer)


def _get_langfuse_handler(session_id: str):
    """LANGFUSE_* 환경변수 미설정 또는 langfuse 미설치 시 None 반환."""
    if not _LANGFUSE_AVAILABLE:
        return None
    public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
    secret_key = os.getenv("LANGFUSE_SECRET_KEY")
    if not public_key or not secret_key:
        return None
    host = os.getenv("LANGFUSE_HOST", "http://langfuse:3000")
    return LangfuseCallbackHandler(
        public_key=public_key,
        secret_key=secret_key,
        host=host,
        session_id=session_id,
    )


async def run_graph(message: str, session_id: str) -> str:
    """StateGraph를 실행하고 최종 응답 텍스트를 반환한다."""
    langfuse_handler = _get_langfuse_handler(session_id)
    config = {
        "configurable": {"thread_id": session_id},
        "recursion_limit": MAX_ITERATIONS * 2 + 5,
    }
    if langfuse_handler:
        config["callbacks"] = [langfuse_handler]

    try:
        result = await graph.ainvoke(
            {"messages": [("human", message)]},
            config=config,
        )
    except GraphRecursionError:
        logger.warning("GraphRecursionError: session_id=%s", session_id)
        return "최대 반복 횟수에 도달했습니다. 다시 시도해주세요."

    last = result["messages"][-1]
    if isinstance(last, AIMessage):
        return last.content or ""
    return str(last.content) if hasattr(last, "content") else ""
