# fAInancial-agent

> 자연어로 한국 금융 데이터를 조회·분석하는 AI Agent
> MCP Tool + Claude API — 프레임워크 없이 직접 구현

---

## 아키텍처

```mermaid
graph TD
    A[사용자: 자연어 질문] --> B[FastAPI POST /chat]
    B --> C[Agent Loop<br/>while tool_use]
    C -->|tool_use| D[MCP Client]
    D --> E[DART MCP Server<br/>재무제표 · 공시 검색]
    D --> F[KRX MCP Server<br/>주가 · 시세]
    E -->|tool_result| C
    F -->|tool_result| C
    C -->|end_turn| G[LLM 최종 응답]
```

---

## 빠른 시작

```bash
# 1. 환경변수 설정
cp .env.example .env
# .env에 ANTHROPIC_API_KEY, DART_API_KEY 입력 (직접)

# 2. 실행
docker compose up

# 3. 질문
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "삼성전자 2024년 영업이익 알려줘"}'
```

---

## 구조

```
fAInancial-agent/
├── mcp_server/          # MCP 서버 (DART + KRX Tool)
│   ├── main.py          # MCP SSE 서버 진입점
│   ├── dart_tools.py    # DART OpenAPI 재무제표 · 공시 Tool
│   ├── krx_tools.py     # FinanceDataReader 주가 Tool
│   └── Dockerfile
├── agent/               # AI Agent
│   ├── main.py          # FastAPI POST /chat
│   ├── loop.py          # Agent Loop (while + tool_use 파싱 직접 구현)
│   ├── mcp_client.py    # MCP SSE 클라이언트
│   └── Dockerfile
├── docker-compose.yml
└── .env.example
```

---

## 기술 스택

| 역할 | 라이브러리 |
|------|-----------|
| LLM | Claude API (`anthropic`) |
| MCP 서버·클라이언트 | `mcp` 공식 SDK |
| DART 공시 데이터 | `requests` (OpenDART API 직접 호출) |
| 주가 데이터 | `FinanceDataReader` |
| API 서버 | `FastAPI` + `uvicorn` |
| 배포 | Docker Compose |

---

## Phase 로드맵

| Phase | 목표 | 상태 |
|-------|------|------|
| **Phase 0** | MCP Agent 즉시 동작 | 🔄 진행 중 |
| Phase 1 | RAG Tool 연동 (공시 문서 검색) | 대기 |
| Phase 2 | LangGraph vs CrewAI 비교 구현 | 대기 |
| Phase 3 | vLLM + LLMOps 프로덕션화 | 대기 |
