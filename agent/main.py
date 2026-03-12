"""
fAInancial-agent FastAPI 진입점
POST /chat → LangGraph Agent 실행 (session_id로 대화 지속)
"""

import logging
import uuid

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from graph import run_graph

logger = logging.getLogger(__name__)

app = FastAPI(title="fAInancial-agent")


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None


class ChatResponse(BaseModel):
    response: str
    session_id: str
    tools_used: list[str] = []


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    try:
        session_id = req.session_id or str(uuid.uuid4())
        text, tools_used = await run_graph(req.message, session_id=session_id)
        return ChatResponse(response=text, session_id=session_id, tools_used=tools_used)
    except Exception:
        logger.exception("Agent loop failed")
        raise HTTPException(
            status_code=500,
            detail="요청 처리 중 오류가 발생했습니다.",
        )


@app.get("/health")
async def health():
    return {"status": "ok"}
