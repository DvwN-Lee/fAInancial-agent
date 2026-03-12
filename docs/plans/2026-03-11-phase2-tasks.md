# Phase 2 Tasks — Agent 고도화 + LangGraph 마이그레이션

> **status**: current
> **date**: 2026-03-11
> **design doc**: [phase2-agent-enhancement.md](./2026-03-11-phase2-agent-enhancement.md)

---

## 의존성 그래프

```
Phase 2-A:
  T1 (SessionStore) ─→ T2 (loop.py history) ─→ T3 (main.py session_id)
                                                       ↓
                                               T4 (시스템 프롬프트)
                                                       ↓
                                               T5 (멀티 기업 인덱싱)
                                                       ↓
                                               T6 (테스트)
                                                       ↓
                                               T7 (Docker + Steady State)

Phase 2-B (T7 완료 후):
  T8 (graph.py StateGraph) ─→ T9 (main.py 연결) ─→ T10 (테스트)
                                                         ↓
                                                  T11 (CLAUDE.md + README 비교)
                                                         ↓
                                                  T12 (Docker + Steady State)
```

순환 의존 없음.

---

## Phase 2-A: Agent 고도화

### T1: SessionStore 모듈 생성

- **파일**: `agent/session.py` (신규)
- **내용**: 인메모리 dict 기반 세션 저장소
  - `create() → str` (uuid4)
  - `get(session_id) → list[Content]`
  - `save(session_id, messages)`
  - TTL 기반 만료 (30분)
  - `trim_history()` — 최근 20턴 유지
- **테스트**: `tests/agent/test_session.py` (신규)
- **의존**: 없음

### T2: loop.py 히스토리 지원

- **파일**: `agent/loop.py` (변경)
- **내용**: `run_agent(message, history=None)` → `tuple[str, list[Content]]`
  - `contents = history + [새 user message]`
  - 반환: `(응답 텍스트, 전체 contents)`
- **테스트**: `tests/agent/test_loop.py` (변경)
- **의존**: T1

### T3: main.py session_id 파라미터

- **파일**: `agent/main.py` (변경)
- **내용**:
  - `ChatRequest.session_id: str | None = None`
  - `ChatResponse.session_id: str`
  - SessionStore 연동 (get → run_agent → save)
- **테스트**: `tests/agent/test_main.py` (변경)
- **의존**: T1, T2

### T4: 시스템 프롬프트 강화

- **파일**: `agent/loop.py` (변경 — SYSTEM_PROMPT)
- **내용**: 종합 분석 요청 시 멀티 Tool 활용 안내 추가
- **테스트**: 수동 확인 (Steady State)
- **의존**: T3

### T5: 멀티 기업 인덱싱

- **파일**: 코드 변경 없음
- **내용**: `index_documents.py --corps "삼성전자,LG화학" --years "2024"` 실행
- **테스트**: 인덱스 생성 확인 + `search_documents(corp_name="LG화학")` 동작
- **의존**: T3

### T6: 단위 테스트 보강

- **파일**:
  - `tests/agent/test_session.py` (신규)
  - `tests/agent/test_loop.py` (변경)
  - `tests/agent/test_main.py` (변경)
- **내용**:
  - SessionStore CRUD + TTL + trim
  - loop.py history 전달/반환
  - main.py session_id 라운드트립
- **의존**: T1, T2, T3

### T7: Docker + Steady State 검증

- **파일**: 변경 없음 (Docker 설정 기존 유지)
- **내용**:
  - `docker compose up` 정상 기동
  - Steady State 확인:
    - "삼성전자 매출 알려줘" → "작년 대비?" → 맥락 유지 답변
    - "삼성전자 종합 분석" → 재무+주가+공시 통합 리포트
    - LG화학 검색 동작
  - `pytest tests/ -v` 전체 통과
- **의존**: T4, T5, T6

---

## Phase 2-B: LangGraph 마이그레이션

### T8: graph.py StateGraph 구현

- **파일**: `agent/graph.py` (신규)
- **내용**:
  - StateGraph 정의 (State: messages, session_id)
  - agent_node: Gemini API 호출
  - tool_node: MCP Tool 실행
  - should_continue: function_call 여부 판단
  - MemorySaver: 대화 상태 자동 관리
- **테스트**: `tests/agent/test_graph.py` (신규)
- **의존**: T7 (Phase 2-A 완료)

### T9: main.py LangGraph 연결

- **파일**: `agent/main.py` (변경)
- **내용**:
  - `graph.run()` 호출로 교체
  - loop.py import 제거 (파일은 보존)
  - session.py 미사용 (LangGraph MemorySaver 대체)
- **테스트**: `tests/agent/test_main.py` (변경)
- **의존**: T8

### T10: 테스트 + 기능 동등성 검증

- **파일**:
  - `tests/agent/test_graph.py` (신규)
  - `tests/agent/test_main.py` (변경)
- **내용**:
  - StateGraph 단위 테스트
  - Phase 2-A 동일 시나리오 통과 확인
  - `pytest tests/ -v` 전체 통과
- **의존**: T8, T9

### T11: CLAUDE.md + README 비교 문서

- **파일**:
  - `CLAUDE.md` 또는 `.claude/CLAUDE.md` (변경 — langgraph 허용)
  - `README.md` (변경 — Before/After 비교 표)
- **내용**:
  - Constitution 프레임워크 금지 조항 Phase 범위 수정
  - loop.py vs graph.py 비교 표 (코드량, 상태관리, 확장성, 의존성)
- **의존**: T10

### T12: Docker + Steady State 최종 검증

- **파일**: `agent/requirements.txt` (변경 — langgraph 추가)
- **내용**:
  - `docker compose build && docker compose up` 정상 기동
  - Phase 2-A 동일 Steady State 전 항목 재확인
  - README 비교 표 완성
- **의존**: T10, T11
