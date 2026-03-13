# Architecture Decision Records

fAInancial-agent 프로젝트의 핵심 아키텍처 결정을 기록합니다.

## ADR 목록

| ADR | 제목 | 상태 |
|-----|------|------|
| [001](ADR-001-langgraph.md) | LangGraph를 Agent 프레임워크로 선택 | Accepted |
| [002](ADR-002-gemini.md) | Gemini를 LLM으로 선택 | Accepted |
| [003](ADR-003-mcp-fastmcp.md) | MCP(FastMCP)를 Tool 통신 프로토콜로 선택 | Accepted |
| [004](ADR-004-voyage-ai.md) | Voyage AI를 임베딩 모델로 선택 | Accepted |
| [005](ADR-005-faiss.md) | FAISS를 벡터 저장소로 선택 | Accepted |
| [006](ADR-006-fastapi.md) | FastAPI를 Agent API 프레임워크로 선택 | Accepted |
| [007](ADR-007-streamlit.md) | Streamlit을 UI 프레임워크로 선택 | Accepted |
| [008](ADR-008-docker-compose.md) | Docker Compose를 배포 단위로 선택 | Accepted |
| [009](ADR-009-langfuse.md) | LangFuse를 Observability 도구로 선택 | Accepted |
| [010](ADR-010-dart-krx.md) | DART/KRX를 금융 데이터 소스로 선택 | Accepted |

## 범위

- 핵심 아키텍처: Agent, LLM, Tool 통신, 임베딩, 벡터 DB, 데이터 소스
- 프레임워크/인프라: API, UI, 배포, Observability

도구/DX(uv, Ruff, pytest, GitHub Actions)는 이 ADR 세트의 범위에 포함되지 않습니다.

## 템플릿

[Michael Nygard 표준](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions)을 따릅니다:

- **Status**: Accepted / Superseded
- **Context**: 배경과 제약 조건
- **Decision**: 선택과 근거
- **Consequences**: 긍정적/부정적 결과
