"""
Agent Loop — 프레임워크 없이 직접 구현
패턴: while stop_reason != "end_turn": tool_use → MCP 호출 → tool_result 주입
"""
# TODO (Task 7): 구현 예정
#
# import anthropic
# from mcp_client import call_mcp_tool, list_mcp_tools
#
# client = anthropic.Anthropic()
#
# async def run_agent(user_message: str) -> str:
#     tools = await list_mcp_tools()
#     messages = [{"role": "user", "content": user_message}]
#
#     while True:
#         response = client.messages.create(
#             model="claude-opus-4-6",
#             max_tokens=4096,
#             tools=tools,
#             messages=messages,
#         )
#
#         if response.stop_reason == "end_turn":
#             return response.content[-1].text
#
#         if response.stop_reason == "tool_use":
#             messages.append({"role": "assistant", "content": response.content})
#             tool_results = []
#             for block in response.content:
#                 if block.type == "tool_use":
#                     result = await call_mcp_tool(block.name, block.input)
#                     tool_results.append({
#                         "type": "tool_result",
#                         "tool_use_id": block.id,
#                         "content": result,
#                     })
#             messages.append({"role": "user", "content": tool_results})
