# Phase 0 구현 설계

> **status**: current
> **작성일**: 2026-03-10
> **Phase**: 0 — MCP Server + Agent Loop

---

## 목표

"삼성전자 2025년 매출 알려줘" → DART Tool 호출 → LLM 요약이 터미널에서 확인되는 End-to-End 동작.

## 아키텍처

```
POST /chat {"message": "삼성전자 2025년 매출 알려줘"}
       ↓
  FastAPI (agent/main.py)
       ↓
  Agent Loop (agent/loop.py)
  └─ while stop_reason != "end_turn":
       ↓ Claude API tool_use
  MCP Client (agent/mcp_client.py)
       ↓ Streamable HTTP
  FastMCP Server (mcp_server/main.py)
  ├─ dart_financials(corp_name, year, report_type)
  ├─ dart_search(keyword)
  └─ krx_price(ticker, start_date, end_date)
       ↓ tool_result
  LLM 최종 응답 → JSON 반환
```

## 설계 결정

| 결정 | 선택 | 근거 |
|------|------|------|
| MCP Transport | Streamable HTTP | 최신 MCP 스펙 권장, Docker 서비스 분리와 자연스럽게 호환 |
| MCP Server API | FastMCP | 데코레이터 기반으로 코드 최소화. MCP SDK는 Constitution의 "프레임워크 금지" 대상 아님 |
| Agent Loop | while + Anthropic SDK | CLAUDE.md 명시 패턴 준수 |
| DART 기업코드 | XML 다운로드 + 메모리 캐싱 | 기업명→corp_code 동적 매핑 필수 |

## 컴포넌트 상세

### MCP Server

**mcp_server/main.py**
- `FastMCP("fAInancial", stateless_http=True)` 인스턴스 생성
- dart_tools, krx_tools에서 정의한 함수를 `@mcp.tool()`로 등록
- `mcp.run(transport="streamable-http", host="0.0.0.0", port=8001)`

**mcp_server/dart_tools.py**
- `get_corp_code(corp_name: str) -> str`: DART 기업코드 XML에서 기업명→corp_code 조회 (서버 시작 시 XML 다운로드, 메모리 캐싱)
- `dart_financials(corp_name: str, year: str, report_type: str) -> dict`: DART API로 재무제표 조회
- `dart_search(keyword: str) -> list`: DART 공시 검색

**mcp_server/krx_tools.py**
- `krx_price(ticker: str, start_date: str, end_date: str) -> dict`: FinanceDataReader로 주가 데이터 조회

### Agent

**agent/mcp_client.py**
- `list_mcp_tools(server_url: str) -> list`: MCP 서버에서 Tool 목록 조회
- `call_mcp_tool(server_url: str, name: str, arguments: dict) -> str`: MCP Tool 호출

**agent/loop.py**
- `run_agent(user_message: str) -> str`: 핵심 Agent Loop
  1. MCP tools 조회 → Claude API tools 스키마로 변환
  2. while stop_reason != "end_turn" (max 10 iterations)
  3. tool_use → MCP call_tool → tool_result 주입
  4. 최종 text 응답 반환

**agent/main.py**
- `POST /chat` 엔드포인트 → `run_agent()` 호출 → JSON 응답

### Docker Compose

기존 docker-compose.yml 유지. 환경변수 `MCP_SERVER_URL` 값을 `/mcp` 경로 포함으로 변경.

## 구현 순서

1. mcp_server/dart_tools.py — DART API 통합
2. mcp_server/krx_tools.py — KRX 주가 조회
3. mcp_server/main.py — FastMCP 서버 부팅
4. agent/mcp_client.py — Streamable HTTP 클라이언트
5. agent/loop.py — Agent Loop
6. agent/main.py — FastAPI 엔드포인트
7. docker-compose.yml 환경변수 업데이트
8. End-to-End 테스트
