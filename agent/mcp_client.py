"""
MCP Streamable HTTP 클라이언트
MCP 서버에서 Tool 목록 조회 + Tool 호출
"""

import os

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://localhost:8001")


async def list_mcp_tools() -> list[dict]:
    """MCP 서버에서 Tool 목록을 조회하여 Claude API 호환 형식으로 반환."""
    async with streamable_http_client(f"{MCP_SERVER_URL}/mcp") as (
        read_stream,
        write_stream,
        _,
    ):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            result = await session.list_tools()
            return [
                {
                    "name": tool.name,
                    "description": tool.description or "",
                    "input_schema": tool.inputSchema,
                }
                for tool in result.tools
            ]


async def call_mcp_tool(name: str, arguments: dict) -> str:
    """MCP 서버의 Tool을 호출하고 결과를 문자열로 반환."""
    async with streamable_http_client(f"{MCP_SERVER_URL}/mcp") as (
        read_stream,
        write_stream,
        _,
    ):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            result = await session.call_tool(name, arguments)
            texts = []
            for block in result.content:
                if hasattr(block, "text"):
                    texts.append(block.text)
                else:
                    texts.append(str(block))
            return "\n".join(texts)
