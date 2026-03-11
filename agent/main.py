"""
fAInancial-agent FastAPI 진입점
POST /chat → Agent Loop 실행 (session_id로 대화 지속)
"""

import logging

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from loop import run_agent
from session import SessionStore

logger = logging.getLogger(__name__)

app = FastAPI(title="fAInancial-agent")
store = SessionStore()


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None


class ChatResponse(BaseModel):
    response: str
    session_id: str


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    try:
        # 세션 조회 또는 생성
        if req.session_id:
            session_id = req.session_id
            history = store.get(session_id)
        else:
            session_id = store.create()
            history = []

        text, contents = await run_agent(req.message, history=history)

        # 히스토리 트림 후 저장
        trimmed = store.trim_history(contents)
        store.save(session_id, trimmed)

        return ChatResponse(response=text, session_id=session_id)
    except Exception as e:
        logger.exception("Agent loop failed")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health():
    return {"status": "ok"}
