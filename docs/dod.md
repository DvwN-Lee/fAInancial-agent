# Definition of Done

> **status**: current

---

## Phase 0 — FOUNDATION

### 기능 완료 기준

- [ ] "삼성전자 2024년 매출 알려줘" → DART Tool 호출 → LLM 요약 응답 확인
- [ ] `docker compose up` 한 줄로 MCP Server + Agent API 전체 기동
- [ ] README에 아키텍처 다이어그램(Mermaid) + Quick Start 포함

### 코드 품질

- [ ] 모든 Tool 함수에 단위 테스트 존재 (mocked external calls)
- [ ] `python -m pytest tests/ -v` 전체 통과
- [ ] API 키 하드코딩 없음 (모두 환경변수)
- [ ] MCP Tool 추상화 원칙 준수 (Agent에서 DART/KRX 직접 호출 없음)

### 아키텍처

- [ ] MCP Server: FastMCP + Streamable HTTP transport
- [ ] Agent Loop: while + tool_use 파싱 (프레임워크 없이 직접 구현)
- [ ] MCP Client: streamable_http_client 사용
- [ ] Docker Compose: 서비스 간 네트워크 통신 정상

### 보안

- [ ] `.env` 파일 gitignore 확인
- [ ] 코드에 API 키 하드코딩 없음
- [ ] `.env.example`에 키 형식만 포함 (실제 값 없음)

---

## Phase 2-A — Agent 고도화 (직접 구현)

> 설계 문서: [phase2-agent-enhancement.md](./plans/2026-03-11-phase2-agent-enhancement.md)
> 태스크: [phase2-tasks.md](./plans/2026-03-11-phase2-tasks.md) T1~T7

### 기능 완료 기준

- [ ] 대화 지속: "삼성전자 매출 알려줘" → "작년 대비 어떻게 변했어?" → 맥락 유지 답변
- [ ] 종합 리포트: "삼성전자 종합 분석" → 재무 + 주가 + 공시 RAG 통합 리포트 출력
- [ ] 멀티 기업: 인덱싱 대상 2개 이상 (삼성전자 + LG화학) + `search_documents(corp_name="LG화학")` 동작
- [ ] API 하위 호환: `session_id` 생략 시 단일 턴 동작 (Phase 1과 동일)
- [ ] Docker: `docker compose up` 한 줄 기동 유지

### 코드 품질

- [ ] `agent/session.py` SessionStore 단위 테스트 — CRUD + TTL 만료 + trim_history
- [ ] `agent/loop.py` history 전달/반환 테스트
- [ ] `agent/main.py` session_id 라운드트립 테스트
- [ ] `python -m pytest tests/ -v` 전체 통과
- [ ] 프레임워크 import 없음 (`langchain`, `langgraph`, `crewai` 미사용)

### 아키텍처

- [ ] SessionStore: 인메모리 dict 기반 (Redis/DB 없음)
- [ ] Agent Loop: while + tool_use 파싱 유지 (프레임워크 없이)
- [ ] API 스키마: `ChatRequest.session_id: str | None`, `ChatResponse.session_id: str`
- [ ] 히스토리 관리: 최근 20턴 유지 (trim_history)
- [ ] MCP Server 변경 없음

---

## Phase 2-B — LangGraph 마이그레이션

> 설계 문서: [phase2-agent-enhancement.md](./plans/2026-03-11-phase2-agent-enhancement.md) §3 Phase 2-B
> 태스크: [phase2-tasks.md](./plans/2026-03-11-phase2-tasks.md) T8~T12

### 기능 동등성

- [ ] Phase 2-A의 대화 지속 시나리오 동일 동작
- [ ] Phase 2-A의 종합 리포트 시나리오 동일 동작
- [ ] Phase 2-A의 멀티 기업 검색 동일 동작
- [ ] API 스키마 변경 없음 (`ChatRequest`/`ChatResponse` 동일)
- [ ] Docker: `docker compose up` 한 줄 기동 유지

### 코드 품질

- [ ] `agent/graph.py` StateGraph 단위 테스트 — agent_node, tool_node, should_continue
- [ ] `python -m pytest tests/ -v` 전체 통과
- [ ] `agent/loop.py`, `agent/session.py` 파일 보존 (비교용, import 제거)

### 아키텍처

- [ ] StateGraph: agent_node → tool_node → should_continue 그래프 정의
- [ ] MemorySaver: LangGraph Checkpoint로 대화 상태 자동 관리
- [ ] `agent/main.py`: `graph.run()` 호출로 교체
- [ ] `agent/requirements.txt`: `langgraph>=0.4.0` 추가
- [ ] MCP Server 변경 없음

### 비교 문서

- [ ] README에 loop.py vs graph.py 비교 표 포함 (코드량, 상태관리, 확장성, 의존성)
- [ ] CLAUDE.md Constitution 수정: Phase 2-B부터 `langgraph` import 허용

---

## Phase 3-A — 프로덕션화 (CI + UI + Observability)

> 설계 문서: [phase3a-productionization.md](./plans/2026-03-12-phase3a-productionization.md)
> 태스크: [phase3a-tasks.md](./plans/2026-03-12-phase3a-tasks.md) T1~T4

### T1 — GitHub Actions CI

- [ ] push/PR 시 CI 자동 트리거 (main, feat/**)
- [ ] `uv run pytest tests/ -v` 91개 전체 통과
- [ ] `uv run ruff check .` lint 통과
- [ ] GitHub Actions 탭 초록 체크 확인

### T2 — Streamlit UI

- [ ] `docker compose up` 후 `http://localhost:8501` 접속 가능
- [ ] 메시지 입력 → `/chat` API 호출 → 응답 표시
- [ ] 동일 세션 대화 지속 (session_id 유지)
- [ ] 페이지 새로고침 시 새 세션 시작

### T3 — LangFuse Observability

- [ ] `docker compose -f docker-compose.yml -f docker-compose.langfuse.yml up` 기동
- [ ] `http://localhost:3000` LangFuse 대시보드 접속
- [ ] 채팅 1회 후 LangFuse에 trace 1건 생성 확인
- [ ] `LANGFUSE_*` 미설정 시 기존 동작 유지 (graceful degradation)
- [ ] 기존 테스트 91개 이상 전체 통과

### T4 — Demo 산출물

- [ ] README에 GitHub Actions CI 뱃지 포함
- [ ] README에 Streamlit UI 스크린샷 1장 이상 포함
- [ ] Quick Start에 `:8501` UI URL 안내 추가

### 코드 품질

- [ ] `uv run pytest tests/ -v` 전체 통과
- [ ] `uv run ruff check .` lint 통과
- [ ] API 키 하드코딩 없음 (LangFuse 키 포함)

### 아키텍처

- [ ] Docker Compose: agent + mcp + ui 3서비스 `docker compose up` 한 줄 기동
- [ ] LangFuse: 별도 `docker-compose.langfuse.yml`로 선택적 활성화
- [ ] Streamlit: FastAPI `/chat` 엔드포인트만 호출 (MCP/LLM 직접 호출 없음)
- [ ] graph.py: LANGFUSE_* 없으면 CallbackHandler 미주입 (기존 동작 동일)
