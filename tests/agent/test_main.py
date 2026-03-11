from unittest.mock import patch, AsyncMock
import pytest
from httpx import AsyncClient, ASGITransport

from main import app


@pytest.mark.asyncio
@patch("main.run_agent", new_callable=AsyncMock)
async def test_chat_endpoint(mock_run_agent):
    mock_run_agent.return_value = ("삼성전자의 2024년 매출은 300조원입니다.", [])

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/chat", json={"message": "삼성전자 매출"})

    assert resp.status_code == 200
    data = resp.json()
    assert "300조" in data["response"]


@pytest.mark.asyncio
@patch("main.run_agent", new_callable=AsyncMock)
async def test_chat_endpoint_error(mock_run_agent):
    mock_run_agent.side_effect = RuntimeError("MCP 서버 연결 실패")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/chat", json={"message": "테스트"})

    assert resp.status_code == 500
    assert "MCP 서버 연결 실패" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_health_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/health")

    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


@pytest.mark.asyncio
@patch("main.run_agent", new_callable=AsyncMock)
async def test_chat_returns_session_id(mock_run_agent):
    """session_id 없이 요청 시 새 session_id가 반환된다."""
    mock_run_agent.return_value = ("응답입니다.", [])

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/chat", json={"message": "안녕"})

    assert resp.status_code == 200
    data = resp.json()
    assert "session_id" in data
    assert len(data["session_id"]) == 36  # uuid4


@pytest.mark.asyncio
@patch("main.run_agent", new_callable=AsyncMock)
async def test_chat_session_continuity(mock_run_agent):
    """session_id를 전달하면 동일 session_id가 반환된다."""
    mock_run_agent.return_value = ("응답입니다.", [])

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 첫 요청 — 새 세션
        resp1 = await client.post("/chat", json={"message": "삼성전자 매출"})
        sid = resp1.json()["session_id"]

        # 후속 요청 — 기존 세션
        resp2 = await client.post(
            "/chat", json={"message": "작년 대비?", "session_id": sid}
        )

    assert resp2.status_code == 200
    assert resp2.json()["session_id"] == sid


@pytest.mark.asyncio
@patch("main.run_agent", new_callable=AsyncMock)
async def test_chat_without_session_id_backward_compatible(mock_run_agent):
    """session_id 없이도 정상 동작 (하위 호환성)."""
    mock_run_agent.return_value = ("응답입니다.", [])

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/chat", json={"message": "테스트"})

    assert resp.status_code == 200
    assert resp.json()["response"] == "응답입니다."
