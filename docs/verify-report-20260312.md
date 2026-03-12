# PR #3 Verify Report — Phase 4 교차 검증

> **PR**: feat: Phase 2 Agent 고도화 + LangGraph 마이그레이션
> **브랜치**: `feat/phase2a-agent-enhancement` → `main`
> **변경 규모**: 23 files, +1,878/-65, 4 commits
> **테스트**: 89/89 pass
> **검증일**: 2026-03-12
> **트랙**: Feature (Phase 2 → 3 → 4)

---

## 검증 방법

3개 병렬 리뷰 에이전트 실행 후, Lead가 실제 코드 대조·교차 검증·중복 제거·오탐 필터링.

| 에이전트 | 역할 | 원시 발견 |
|----------|------|----------|
| code-reviewer | 코드 품질·보안·CLAUDE.md 준수 | C-3, M-6 |
| pr-test-analyzer | 테스트 커버리지 품질 | C-3, M-6 |
| silent-failure-hunter | 에러 핸들링·무음 실패 | C-3, H-4, M-3, N-2 |

---

## 교차 검증 결과 요약

| 심각도 | 건수 | Gate 기준 |
|--------|------|----------|
| **CRITICAL** | **1** | 0건이어야 Merge 가능 |
| MAJOR | 5 | — |
| MINOR | 7 | — |

**Gate 판정: CONDITIONAL MERGE — CRITICAL 1건 해소 필요. Phase 3 회귀.**

---

## CRITICAL (1건)

### C-1: tool_node 예외 처리 무로깅 — 운영 사각지대

**파일**: `agent/graph.py:88-91`
**발견 에이전트**: silent-failure-hunter (C-1) + code-reviewer (M-3)

```python
for tc in last_message.tool_calls:
    try:
        result = await call_mcp_tool(tc["name"], tc["args"])
    except Exception as exc:
        result = f"Tool '{tc['name']}' 호출 실패: {exc}"
```

**문제**:
1. **무로깅**: MCP 서버 장애(ConnectionError, Timeout) 시 운영자가 인지할 수 있는 로그가 전혀 없음
2. **광범위 catch**: `Exception` 전체를 잡아 문자열로 변환 → 버그(KeyError, TypeError)도 조용히 삼킴
3. **내부 정보 누출**: `str(exc)`가 MCP 서버 URL, 파일 경로 등을 포함할 수 있고 이것이 LLM 컨텍스트에 주입됨

**영향 시나리오**: MCP 서버 다운 → tool_node가 에러를 문자열로 변환 → LLM이 에러 문자열을 기반으로 그럴듯한 오답 생성 → 사용자는 잘못된 답변을 받음 → 운영자는 로그에서 문제를 발견할 수 없음.

**수정 방향**:
- `import logging` + `logger.exception(...)` 추가
- 에러 메시지에서 내부 정보 제거 (일반화된 메시지 사용)

---

## MAJOR (5건)

### M-1: 버전 피닝 불일치 — requirements.txt vs pyproject.toml

**파일**: `agent/requirements.txt:2-3` vs `pyproject.toml:17-18`
**발견 에이전트**: code-reviewer (C-1)

| 패키지 | requirements.txt (Docker) | pyproject.toml (uv) |
|--------|--------------------------|---------------------|
| langgraph | `>=0.4.0` | `>=1.0.10` |
| langchain-google-genai | `>=2.0.0` | `>=4.2.1` |

**검증**: `agent/Dockerfile:6`에서 `pip install -r requirements.txt` 사용. 현재 pip은 최신 버전을 설치하므로 즉시 장애는 아니지만, 의존성 충돌 시 하위 호환 버전이 설치될 위험 존재. `from langgraph.checkpoint.memory import InMemorySaver` 등의 import는 0.4.x에 존재하지 않을 가능성 높음.

**수정**: `agent/requirements.txt`의 버전을 `pyproject.toml`과 동기화.

---

### M-2: HTTPException(detail=str(e)) 내부 정보 노출

**파일**: `agent/main.py:35-37`
**발견 에이전트**: code-reviewer (C-2) + silent-failure-hunter (H-1)

```python
except Exception as e:
    logger.exception("Agent loop failed")
    raise HTTPException(status_code=500, detail=str(e))
```

**문제**: `str(e)`에 MCP 서버 URL, 파일 경로, API 키 에러 메시지가 포함될 수 있고 이것이 HTTP 응답으로 클라이언트에 노출됨.

**수정**: 일반화된 에러 메시지로 교체. 상세 정보는 서버 로그에만 기록 (이미 `logger.exception` 있음).

---

### M-3: Empty API key deferred failure

**파일**: `agent/graph.py:48`
**발견 에이전트**: code-reviewer (M-5) + silent-failure-hunter (H-2)

```python
google_api_key=os.getenv("GEMINI_API_KEY", ""),
```

**문제**: `GEMINI_API_KEY` 미설정 시 앱이 정상 기동되고, `/health` OK 응답 후 첫 `/chat` 요청에서 불투명한 SDK 에러 발생. 동일 프로젝트 내 `scripts/evaluate_rag.py`와 `scripts/index_documents.py`는 이미 빈 키 검증 패턴을 사용 중.

**수정**: `_get_model()`에서 빈 API 키 시 명시적 `ValueError` raise.

---

### M-4: GraphRecursionError 미처리 — loop.py 대비 행동 회귀

**파일**: `agent/graph.py:124-139`
**발견 에이전트**: pr-test-analyzer (C-1)

**문제**: `loop.py`는 `MAX_ITERATIONS` 초과 시 `"최대 반복 횟수에 도달했습니다. 다시 시도해주세요."` 반환. `graph.py`는 `GraphRecursionError`가 미처리 상태로 `main.py`까지 전파 → 500 에러 + 내부 에러 메시지 노출 (M-2와 결합).

**수정**: `run_graph`에서 `GraphRecursionError` catch → 사용자 친화적 메시지 반환. 또는 테스트 추가로 행동 문서화.

---

### M-5: agent_node bind_tools 경로 미테스트

**파일**: `tests/agent/test_graph.py`
**발견 에이전트**: pr-test-analyzer (C-3)

**문제**: 모든 `TestAgentNode` 테스트에서 `mock_list_tools.return_value = []` 설정 → `bind_tools`가 한 번도 호출되지 않음. 이것이 실제 운영의 주 경로 (MCP 서버에 항상 tool이 있음). `_mcp_to_tool_defs`가 `bind_tools`와 호환되지 않는 형식을 반환해도 테스트에서 포착 불가.

**수정**: `list_mcp_tools`가 tool 정의를 반환하는 테스트 케이스 추가.

---

## MINOR (7건)

| ID | 파일 | 내용 | 근거 |
|----|------|------|------|
| m-1 | `graph.py:136-139` | `run_graph` non-AIMessage fallback에 로깅 없음 | Error-handler 발견. 엣지 케이스이나 디버깅 어려움 |
| m-2 | `graph.py:120` | `InMemorySaver` 무제한 메모리 성장 | 프로토타입 단계에서 허용. 설계 문서에 명시 |
| m-3 | `graph.py:109-121` | 모듈 수준 graph compilation | LangGraph 표준 패턴. 의도적 설계 |
| m-4 | `graph.py:70` | `list_mcp_tools()` 매 agent_node 호출마다 실행 | PR #1 M-7에서 `stateless_http=True` 설계 의도 확인 완료 |
| m-5 | `loop.py:100-101` | 동일한 bare except — 참조 코드 | 활성 코드 경로 아님 (main.py는 graph.py만 import) |
| m-6 | `test_graph.py` | Mixed tool success/failure 미테스트 | 부분 실패 복원력 미검증 |
| m-7 | `test_graph.py` | `should_continue`에 non-AIMessage 입력 미테스트 | `hasattr` 가드가 있으나 테스트 누락 |

---

## 오탐 필터링 (에이전트 발견 → 제외)

| 원시 ID | 에이전트 | 내용 | 제외 사유 |
|---------|----------|------|----------|
| Code-C-3 | code-reviewer | `_model_instance` 글로벌 싱글턴 thread-safety | Python GIL 보호. `ChatGoogleGenerativeAI`는 stateless. 중복 초기화해도 동등 인스턴스 |
| Code-M-6 | code-reviewer | `SessionStore` thread-safety | 참조 코드. 활성 코드 경로 아님 |
| Error-C-2 | silent-failure-hunter | `loop.py` 동일 패턴 | 참조 코드. `main.py`는 `graph.py`만 사용 → m-5로 다운그레이드 |
| Error-M-1 | silent-failure-hunter | `session.py` 만료 시 무로깅 | 참조 코드. InMemorySaver가 대체 |
| Error-M-3 | silent-failure-hunter | `mcp_client.py` 에러 핸들링 없음 | thin client 설계. 호출자(graph.py)에서 처리 |
| Test-C-2 | pr-test-analyzer | `run_graph` non-AIMessage fallback 미테스트 | m-1로 다운그레이드 (엣지 케이스, 로깅 부재가 주 문제) |
| Test-M-1 | pr-test-analyzer | `_get_model` 싱글턴 직접 테스트 없음 | mock으로 우회 중. 실질적 위험 낮음 |
| Test-M-4 | pr-test-analyzer | SessionStore TTL 내부 dict 삭제 미검증 | 참조 코드 |
| Test-M-5 | pr-test-analyzer | 빈 message body 미테스트 | Pydantic 기본 동작. 빈 문자열은 유효한 입력 |

---

## 긍정적 관찰

1. **LangGraph 마이그레이션 구조**: StateGraph → agent_node → should_continue → tool_node 패턴이 명확하고 loop.py와 1:1 대응
2. **세션 연속성 테스트**: `test_run_graph_session_continuity`가 InMemorySaver 통합을 실증적으로 검증
3. **tool_node 부분 실패 복원**: 개별 tool_call의 예외가 다른 tool_call에 영향 안 줌 (독립적 try/except)
4. **SYSTEM_PROMPT 포함 검증**: `test_agent_node_includes_system_prompt`로 시스템 프롬프트 전달 확인
5. **후방 호환성 테스트**: `test_chat_without_session_id_backward_compatible`로 Phase 0 API 호환 보장
6. **loop.py + session.py 참조 보존**: Phase 0 코드를 삭제하지 않고 보존하여 비교 가능

---

## Gate 판정

| 기준 | 결과 |
|------|------|
| CRITICAL 0건 | **미충족** (C-1: 1건) |
| 테스트 전체 통과 | 89/89 ✅ |
| Constitution 준수 | Phase 2-B 프레임워크 허용 ✅ |

**판정: Phase 3 회귀 — CRITICAL 1건 + MAJOR 5건 수정 후 재검증 필요.**

---

## 수정 우선순위

| 순서 | ID | 작업량 | 설명 |
|------|----|--------|------|
| 1 | C-1 | ~10줄 | `graph.py`에 logging 추가 + 에러 메시지 일반화 |
| 2 | M-1 | ~2줄 | `requirements.txt` 버전 동기화 |
| 3 | M-2 | ~2줄 | `main.py` HTTPException 메시지 일반화 |
| 4 | M-3 | ~5줄 | `_get_model()`에 빈 API 키 검증 |
| 5 | M-4 | ~10줄 | `run_graph`에 GraphRecursionError 처리 |
| 6 | M-5 | ~20줄 | bind_tools 경로 테스트 추가 |
