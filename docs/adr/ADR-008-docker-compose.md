# ADR-008: Docker Compose를 배포 단위로 선택

## Status
Accepted (2026-03-10)

## Context
- 프로젝트 원칙: "로컬 실행은 항상 docker compose up 한 줄로 가능해야 한다"
- 3개 서비스(MCP 서버, Agent API, Streamlit UI)를 독립 컨테이너로 분리하되 단일 명령으로 기동
- 선택적 LangFuse Observability 스택 추가 가능해야 함

## Decision
Docker Compose로 3서비스 기본 배포 + optional LangFuse 오버라이드 파일.

고려한 대안:
- **Kubernetes**: 프로덕션 오케스트레이션 표준이나, 로컬 개발/포트폴리오 프로젝트에는 과도한 인프라 복잡성
- **단일 컨테이너**: 모든 서비스를 하나의 컨테이너에 패키징. 서비스 분리 불가, 독립 스케일링 불가
- **로컬 프로세스**: Docker 없이 직접 실행. 환경 재현성 없음, 의존성 충돌 위험

선택 근거: Docker Compose는 docker-compose.yml 하나로 서비스 간 네트워크, 의존 관계(depends_on + healthcheck), 환경변수를 선언적으로 관리한다. docker-compose.langfuse.yml 오버라이드 파일로 LangFuse + PostgreSQL을 선택적으로 추가할 수 있다.

시크릿 관리 전략: .env 파일 + Docker env_file로 API 키를 주입한다. 이는 개발/데모 목적의 의도적 선택이며, 프로덕션 격상 시 Docker Secrets 또는 외부 시크릿 관리자(Vault, AWS Secrets Manager)로 전환이 필요하다. 프로젝트 규칙에서 ".env 파일 직접 수정 또는 생성은 Human 전용"으로 명시하여 자동화 도구의 시크릿 접근을 차단한다.

## Consequences
- 긍정: 한 줄 기동, 서비스 독립 배포, 환경 재현성, 선택적 LangFuse 추가
- 부정: Docker Desktop 필요, 이미지 빌드 시간, 프로덕션 수준의 오케스트레이션에는 부족
- healthcheck: mcp-server에 TCP 소켓 검사, agent는 mcp-server:service_healthy 대기. ui → agent 간 healthcheck는 미적용 (Streamlit 재시도로 충분)
- 시크릿: .env 파일 기반 (개발 목적). 프로덕션 전환 시 이 ADR을 Superseded로 변경하고 새 ADR 작성
