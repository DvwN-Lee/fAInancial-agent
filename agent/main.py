"""
fAInancial-agent FastAPI 진입점
POST /chat → Agent Loop 실행
"""

import logging

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from loop import run_agent

logger = logging.getLogger(__name__)

app = FastAPI(title="fAInancial-agent")


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    response: str


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    try:
        result = await run_agent(req.message)
        return ChatResponse(response=result)
    except Exception as e:
        logger.exception("Agent loop failed")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health():
    return {"status": "ok"}
