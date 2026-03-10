"""
Agent Loop — 프레임워크 없이 직접 구현
패턴: while stop_reason != "end_turn": tool_use → MCP 호출 → tool_result 주입
"""

import os

import anthropic

from mcp_client import call_mcp_tool, list_mcp_tools

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY", ""))

SYSTEM_PROMPT = (
    "당신은 한국 금융 데이터 분석 AI 어시스턴트입니다. "
    "DART 전자공시와 KRX 주가 데이터를 조회하는 도구를 사용하여 "
    "사용자의 질문에 정확하게 답변하세요. "
    "데이터를 조회한 후에는 핵심 수치를 포함하여 명확하게 요약해주세요."
)

MAX_ITERATIONS = 10


async def run_agent(user_message: str) -> str:
    """Agent Loop: Claude API + MCP Tool 연동."""
    tools = await list_mcp_tools()
    messages = [{"role": "user", "content": user_message}]

    for _ in range(MAX_ITERATIONS):
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            tools=tools,
            messages=messages,
        )

        if response.stop_reason == "end_turn":
            for block in reversed(response.content):
                if block.type == "text":
                    return block.text
            return ""

        if response.stop_reason != "tool_use":
            # max_tokens, stop_sequence 등 예상치 못한 종료
            for block in reversed(response.content):
                if block.type == "text":
                    return block.text
            return f"응답이 중단되었습니다 (사유: {response.stop_reason})"

        # tool_use 처리
        messages.append({"role": "assistant", "content": response.content})
        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                result = await call_mcp_tool(block.name, block.input)
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result,
                    }
                )
        messages.append({"role": "user", "content": tool_results})

    return "최대 반복 횟수에 도달했습니다. 다시 시도해주세요."
