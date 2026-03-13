# ADR-003: MCP(FastMCP)를 Tool 통신 프로토콜로 선택

## Status
Accepted (2026-03-10)

## Context
- Agent가 DART 전자공시와 KRX 주가 데이터를 조회해야 하며, 프로젝트 코드 규칙에 따라 "MCP 서버 없이 DART/KRX API를 Agent에서 직접 호출"하는 것이 금지됨
- Tool 추상화 계층이 필요: Agent는 Tool 이름과 파라미터만 알고, 실제 API 호출은 MCP 서버가 담당
- MCP(Model Context Protocol)는 Anthropic이 제안한 표준 프로토콜로, Tool 자동 디스커버리를 지원

## Decision
FastMCP 라이브러리를 사용하여 Streamable HTTP 기반 MCP 서버를 구현.

고려한 대안:
- **REST API 직접 호출**: Agent에서 DART/KRX HTTP 요청을 직접 수행. 단순하지만 프로젝트 코드 규칙 위반, Tool 추상화 없음
- **gRPC**: 고성능 바이너리 프로토콜이나, 이 프로젝트 규모에서는 과도한 인프라 복잡성
- **LangChain Tool 래핑**: @tool 데코레이터로 Python 함수를 직접 Tool로 등록. MCP 프로토콜 없이 동일 프로세스 내 실행되어 서비스 분리 불가

선택 근거: @mcp.tool() 데코레이터로 Tool을 선언하면 list_tools()로 자동 디스커버리되어 Agent가 런타임에 사용 가능한 Tool을 동적으로 인식한다. MCP 서버와 Agent를 별도 컨테이너로 분리하여 독립 배포/스케일링 가능. Streamable HTTP 전송으로 Docker Compose 네트워크에서 안정적 통신.

## Consequences
- 긍정: Agent-Tool 완전 분리, Tool 추가 시 MCP 서버만 수정, 자동 디스커버리로 Agent 코드 변경 불필요
- 부정: MCP 서버 장애 시 모든 Tool 호출 실패 (단일 장애점), MCP 프로토콜 학습 비용
- tool_node에서 MCP 호출 실패 시 logger.exception + 일반화된 에러 메시지로 LLM context 오염 방지
