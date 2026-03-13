# ADR-009: LangFuse를 Observability 도구로 선택

## Status
Accepted (2026-03-12)

## Context
- LLM Agent의 호출 추적, 비용 모니터링, 디버깅을 위한 Observability 도구 필요
- self-hosted 가능해야 함 (외부 SaaS 의존 최소화)
- Agent의 핵심 기능(채팅)을 차단하지 않는 graceful degradation 필수

## Decision
LangFuse를 self-hosted(docker-compose.langfuse.yml)로 운용하며, graceful degradation 패턴 적용.

고려한 대안:
- **LangSmith**: LangChain 공식 Observability. 기능 풍부하나 SaaS 전용, self-hosted 불가
- **Phoenix Arize**: 오픈소스 LLM Observability이나, LangGraph 통합 성숙도가 LangFuse 대비 낮음
- **자체 로깅**: logger + 파일 기반. 구현 단순하나, 트레이스 시각화 및 세션별 추적 불가

선택 근거: LangFuse는 오픈소스이며 Docker Compose로 self-hosted 가능하다(PostgreSQL + LangFuse 웹). LangfuseCallbackHandler를 LangGraph config["callbacks"]에 주입하는 방식으로 통합하며, 미설치/미설정 시 None을 반환하여 핵심 채팅 기능에 영향을 주지 않는다.

graceful degradation 구현: (1) try/except ImportError로 _LANGFUSE_AVAILABLE 플래그 설정 (2) 환경변수(LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY) 미설정 시 None 반환 (3) CallbackHandler 생성자 예외 시 logger.warning(exc_info=True) + None 반환.

## Consequences
- 긍정: self-hosted, 오픈소스, graceful degradation으로 핵심 기능 미차단
- 부정: PostgreSQL 추가 운용 필요, LangFuse 서비스 자체의 모니터링은 별도 필요
- docker-compose.langfuse.yml은 opt-in 파일로, 기본 docker compose up에는 포함되지 않음
