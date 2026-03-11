# Phase 0 Tasks — 의존성 그래프

> **status**: current
> **Feature Track**: Phase 2 산출물

## 의존성 다이어그램

```
T1 (Test Infra)
 ├──→ T2 (DART Corp Code)
 │     ├──→ T3 (DART Financials)
 │     └──→ T4 (DART Search)
 └──→ T5 (KRX Price)
        │
  T3 + T4 + T5 ──→ T6 (MCP Server)
                     └──→ T7 (MCP Client)
                           └──→ T8 (Agent Loop)
                                 └──→ T9 (FastAPI)
                                       └──→ T10 (Docker/Deps)
                                             └──→ T11 (E2E)
```

## Wave 분할 (max 3 concurrent subagents)

| Wave | Tasks | 병렬 가능 | 비고 |
|------|-------|----------|------|
| W1 | T1 | 1 | Lead 직접 수행 (소규모) |
| W2 | T2, T5 | 2 | DART corp code + KRX price 병렬 |
| W3 | T3, T4 | 2 | DART financials + search 병렬 |
| W4 | T6 | 1 | MCP Server (T3,T4,T5 통합) |
| W5 | T7 → T8 → T9 | 순차 | Client → Loop → API (순차 의존) |
| W6 | T10, T11 | 순차 | Docker 업데이트 → E2E |

## Task 상세

| ID | 제목 | 파일 | 의존 | 상태 |
|----|------|------|------|:----:|
| T1 | Test infrastructure | tests/conftest.py, requirements | — | - |
| T2 | DART corp code resolver | mcp_server/dart_tools.py | T1 | - |
| T3 | DART financial statements | mcp_server/dart_tools.py | T2 | - |
| T4 | DART disclosure search | mcp_server/dart_tools.py | T2 | - |
| T5 | KRX stock price | mcp_server/krx_tools.py | T1 | - |
| T6 | MCP Server (FastMCP) | mcp_server/main.py | T3,T4,T5 | - |
| T7 | MCP Client (Streamable HTTP) | agent/mcp_client.py | T6 | - |
| T8 | Agent Loop (while+tool_use) | agent/loop.py | T7 | - |
| T9 | FastAPI endpoint | agent/main.py | T8 | - |
| T10 | Docker Compose & deps | docker-compose.yml, requirements | T9 | - |
| T11 | E2E smoke test | manual | T10 | - |
