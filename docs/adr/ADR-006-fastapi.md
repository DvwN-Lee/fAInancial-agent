# ADR-006: FastAPI를 Agent API 프레임워크로 선택

## Status
Accepted (2026-03-10)

## Context
- LangGraph Agent를 HTTP API로 서빙하여 UI 및 외부 클라이언트에서 호출 가능해야 함
- async 지원 필수 (LangGraph의 ainvoke, MCP 클라이언트의 비동기 호출)
- 요청/응답 스키마 자동 검증 및 OpenAPI 문서 자동 생성 필요

## Decision
FastAPI + Pydantic v2 + Uvicorn을 Agent API 프레임워크로 선택.

고려한 대안:
- **Flask**: 성숙한 생태계이나, async 지원이 네이티브가 아님 (Flask 2.x에서 부분 지원)
- **Django**: 풀스택 프레임워크로 이 프로젝트에서는 과도한 기능 (ORM, 템플릿 등 불필요)
- **LangServe**: LangChain 공식 서빙 도구이나, LangGraph StateGraph와의 통합이 제한적이며 커스텀 엔드포인트 유연성 부족

선택 근거: FastAPI는 async/await 네이티브 지원으로 LangGraph의 ainvoke와 자연스럽게 통합된다. Pydantic v2 기반 요청/응답 모델(ChatRequest, ChatResponse)로 자동 검증되며, /docs 엔드포인트에서 OpenAPI 스펙이 자동 생성된다. Uvicorn ASGI 서버로 Docker 컨테이너 내에서 안정적으로 운용된다.

## Consequences
- 긍정: async 네이티브, Pydantic 자동 검증, OpenAPI 자동 생성, 경량
- 부정: WebSocket 등 고급 실시간 기능 필요 시 추가 설정 필요
- /chat 단일 엔드포인트 + /health 헬스체크로 시작, 향후 필요 시 엔드포인트 확장 용이
- ChatResponse에 tools_used 필드 추가로 API 계약을 하위 호환 방식으로 확장한 사례 있음
