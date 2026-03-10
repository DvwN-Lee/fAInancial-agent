"""
MCP SSE 클라이언트
MCP 서버에서 Tool 목록 조회 + Tool 호출
"""
# TODO (Task 7): 구현 예정
# from mcp import ClientSession
# from mcp.client.sse import sse_client
# import os
#
# MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://localhost:8001")
#
# async def list_mcp_tools() -> list:
#     async with sse_client(f"{MCP_SERVER_URL}/sse") as (read, write):
#         async with ClientSession(read, write) as session:
#             await session.initialize()
#             tools = await session.list_tools()
#             return [t.model_dump() for t in tools.tools]
#
# async def call_mcp_tool(name: str, arguments: dict) -> str:
#     async with sse_client(f"{MCP_SERVER_URL}/sse") as (read, write):
#         async with ClientSession(read, write) as session:
#             await session.initialize()
#             result = await session.call_tool(name, arguments)
#             return str(result.content)
