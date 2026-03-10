from unittest.mock import patch, AsyncMock
import pytest
from httpx import AsyncClient, ASGITransport

from main import app


@pytest.mark.asyncio
@patch("main.run_agent", new_callable=AsyncMock)
async def test_chat_endpoint(mock_run_agent):
    mock_run_agent.return_value = "삼성전자의 2024년 매출은 300조원입니다."

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/chat", json={"message": "삼성전자 매출"})

    assert resp.status_code == 200
    data = resp.json()
    assert "300조" in data["response"]


@pytest.mark.asyncio
async def test_health_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/health")

    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
