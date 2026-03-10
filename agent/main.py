"""
fAInancial-agent FastAPI 진입점
POST /chat → Agent Loop 실행
"""

from fastapi import FastAPI
from pydantic import BaseModel

from loop import run_agent

app = FastAPI(title="fAInancial-agent")


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    response: str


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    result = await run_agent(req.message)
    return ChatResponse(response=result)


@app.get("/health")
async def health():
    return {"status": "ok"}
