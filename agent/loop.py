"""
Agent Loop — 프레임워크 없이 직접 구현
패턴: while function_calls: MCP 호출 → function_response 주입
"""

import os

from google import genai
from google.genai import types

from mcp_client import call_mcp_tool, list_mcp_tools

_client: genai.Client | None = None


def _get_client() -> genai.Client:
    """Gemini 클라이언트를 지연 초기화한다."""
    global _client
    if _client is None:
        _client = genai.Client(api_key=os.getenv("GEMINI_API_KEY", ""))
    return _client

MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

SYSTEM_PROMPT = (
    "당신은 한국 금융 데이터 분석 AI 어시스턴트입니다. "
    "DART 전자공시와 KRX 주가 데이터를 조회하는 도구를 사용하여 "
    "사용자의 질문에 정확하게 답변하세요. "
    "데이터를 조회한 후에는 핵심 수치를 포함하여 명확하게 요약해주세요."
)

MAX_ITERATIONS = 10


def _mcp_tools_to_gemini(mcp_tools: list[dict]) -> types.Tool:
    """MCP tool 목록을 Gemini FunctionDeclaration으로 변환."""
    declarations = []
    for t in mcp_tools:
        declarations.append(
            types.FunctionDeclaration(
                name=t["name"],
                description=t["description"],
                parameters_json_schema=t["input_schema"],
            )
        )
    return types.Tool(function_declarations=declarations)


async def run_agent(user_message: str) -> str:
    """Agent Loop: Gemini API + MCP Tool 연동."""
    mcp_tools = await list_mcp_tools()
    gemini_tool = _mcp_tools_to_gemini(mcp_tools)

    contents = [
        types.Content(
            role="user",
            parts=[types.Part.from_text(text=user_message)],
        )
    ]

    config = types.GenerateContentConfig(
        tools=[gemini_tool],
        automatic_function_calling=types.AutomaticFunctionCallingConfig(
            disable=True
        ),
        system_instruction=SYSTEM_PROMPT,
    )

    for _ in range(MAX_ITERATIONS):
        response = _get_client().models.generate_content(
            model=MODEL,
            contents=contents,
            config=config,
        )

        if not response.function_calls:
            return response.text or ""

        # function_call 처리
        function_call_content = response.candidates[0].content
        contents.append(function_call_content)

        function_response_parts = []
        for fc in response.function_calls:
            try:
                result = await call_mcp_tool(fc.name, dict(fc.args))
            except Exception as exc:
                result = f"Tool '{fc.name}' 호출 실패: {exc}"

            function_response_parts.append(
                types.Part.from_function_response(
                    name=fc.name,
                    response={"result": result},
                )
            )

        contents.append(
            types.Content(role="tool", parts=function_response_parts)
        )

    return "최대 반복 횟수에 도달했습니다. 다시 시도해주세요."
