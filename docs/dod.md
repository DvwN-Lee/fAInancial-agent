# Definition of Done — Phase 0

> **status**: current

## 기능 완료 기준

- [ ] "삼성전자 2024년 매출 알려줘" → DART Tool 호출 → LLM 요약 응답 확인
- [ ] `docker compose up` 한 줄로 MCP Server + Agent API 전체 기동
- [ ] README에 아키텍처 다이어그램(Mermaid) + Quick Start 포함

## 코드 품질

- [ ] 모든 Tool 함수에 단위 테스트 존재 (mocked external calls)
- [ ] `python -m pytest tests/ -v` 전체 통과
- [ ] API 키 하드코딩 없음 (모두 환경변수)
- [ ] MCP Tool 추상화 원칙 준수 (Agent에서 DART/KRX 직접 호출 없음)

## 아키텍처

- [ ] MCP Server: FastMCP + Streamable HTTP transport
- [ ] Agent Loop: while + tool_use 파싱 (프레임워크 없이 직접 구현)
- [ ] MCP Client: streamable_http_client 사용
- [ ] Docker Compose: 서비스 간 네트워크 통신 정상

## 보안

- [ ] `.env` 파일 gitignore 확인
- [ ] 코드에 API 키 하드코딩 없음
- [ ] `.env.example`에 키 형식만 포함 (실제 값 없음)
