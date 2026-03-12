# Phase 2 설계 — Agent 고도화 + LangGraph 마이그레이션

> **status**: current
> **date**: 2026-03-11
> **track**: Phase 2-A (직접 구현 고도화) → Phase 2-B (LangGraph 마이그레이션)
> **SAGA phase**: Phase 2 SPECIFICATION

---

## 1. 배경: Phase 1 완료 상태

### 달성 수치

| 항목 | 결과 |
|------|------|
| faithfulness | **1.000** (목표 ≥ 0.7) |
| context_precision | **0.963** (목표 ≥ 0.6) |
| 인덱싱 청크 수 | 1,494 (삼성전자 사업보고서) |
| MCP Tools | 4개 (get_financials, search_disclosures, get_stock_price, search_documents) |

### 현재 Agent Loop 능력 (loop.py, 102줄)

| 능력 | 지원 | 비고 |
|------|------|------|
| 멀티 Tool 호출 | O | 한 턴에서 여러 Tool 순차 호출 |
| 멀티스텝 추론 | O | Tool 결과 기반 후속 Tool 호출 |
| Tool 선택/조합 | O | Gemini가 질문에 맞는 Tool 자동 선택 |
| 대화 히스토리 | **X** | 매 요청이 독립. "작년 대비?" 맥락 유실 |
| 병렬 Tool 호출 | **X** | 순차 처리만 가능 |
| 조건 분기 | **X** | Tool 실패 시 폴백 없음 |
| 상태 저장/복원 | **X** | 분석 중단 → 재개 불가 |

### 핵심 한계

**대화 히스토리 부재가 유일한 실질적 UX 문제.**
나머지 3개(병렬/분기/상태)는 현 규모(1,494 청크, 단일 사용자)에서 문제되지 않음.

---

## 2. 목표

### Phase 2-A: Agent 고도화 (LangGraph 없이)

현재 while 루프를 유지하면서 실질적 기능 향상.

| 항목 | 기준 |
|------|------|
| 대화 지속 | "삼성전자 매출 알려줘" → "작년 대비 어떻게 변했어?" → 맥락 유지 답변 |
| 종합 리포트 | "삼성전자 종합 분석" → 재무 + 주가 + 공시 RAG 통합 리포트 출력 |
| 멀티 기업 | 인덱싱 대상 2개 이상 (삼성전자 + LG화학 등) |
| Docker | `docker compose up` 유지 |

### Phase 2-B: LangGraph 마이그레이션

Phase 2-A의 **동일 기능**을 LangGraph StateGraph로 재구현.

| 항목 | 기준 |
|------|------|
| 기능 동등성 | Phase 2-A의 모든 기능이 LangGraph 버전에서 동일 동작 |
| StateGraph | loop.py의 while 루프 → StateGraph + nodes + edges로 교체 |
| Checkpoint | 대화 상태를 LangGraph Checkpoint로 자동 관리 |
| Before/After | README에 직접 구현 vs LangGraph 비교 섹션 포함 |

---

## 3. 아키텍처

### Phase 2-A: 대화 히스토리 + 리포트

```
POST /chat  { message, session_id? }
       ↓
  agent/main.py
  ├─ session_id → SessionStore에서 이전 messages 조회
  └─ run_agent(user_message, history=[...])
       ↓
  agent/loop.py (변경)
  ├─ contents = history + [새 user message]  ← 핵심 변경
  ├─ while function_calls: (기존 동일)
  │     MCP Client → MCP Server
  └─ 응답 반환 + SessionStore에 messages 저장
       ↓
  ChatResponse { response, session_id }
```

**SessionStore 설계:**

```python
# agent/session.py (신규)
class SessionStore:
    """인메모리 세션 저장소. Phase 2-A에서는 dict 기반."""

    def get(session_id: str) -> list[Content]
    def save(session_id: str, messages: list[Content]) -> None
    def create() -> str  # uuid4 기반 session_id 반환
```

- Phase 2-A: 인메모리 dict (서버 재시작 시 소멸 — 허용)
- 세션 만료: TTL 기반 (예: 30분 미사용 시 삭제)
- 최대 히스토리: 최근 N턴 유지 (토큰 제한 방지)

### Phase 2-B: LangGraph StateGraph

```
POST /chat  { message, session_id? }
       ↓
  agent/main.py (변경 — graph.run() 호출)
       ↓
  agent/graph.py (신규)
  ├─ StateGraph 정의
  │     State: { messages, session_id }
  │     Nodes: agent_node, tool_node
  │     Edges: should_continue (tool 호출 여부)
  ├─ agent_node: Gemini API 호출
  ├─ tool_node: MCP Tool 실행
  └─ Checkpoint: MemorySaver (대화 상태 자동 유지)
       ↓
  ChatResponse { response, session_id }
```

**Phase 2-B에서 제거되는 것:**
- `agent/loop.py` → `agent/graph.py`로 대체 (loop.py 보존, import만 변경)
- `agent/session.py` → LangGraph Checkpoint가 대체

---

## 4. 파일 구조

### Phase 2-A 변경

```
agent/
├── main.py          # 변경 — session_id 파라미터 추가, SessionStore 연동
├── loop.py          # 변경 — run_agent(message, history) 시그니처 변경
├── session.py       # 신규 — 인메모리 세션 저장소
├── mcp_client.py    # 변경 없음
├── Dockerfile       # 변경 없음
└── requirements.txt # 변경 없음
```

### Phase 2-B 추가 변경

```
agent/
├── main.py          # 변경 — graph.run() 호출로 교체
├── graph.py         # 신규 — LangGraph StateGraph 정의
├── loop.py          # 보존 — Phase 2-A 코드 유지 (비교용, import에서 제거)
├── session.py       # 보존 — loop.py가 사용하던 것 (graph.py는 미사용)
├── mcp_client.py    # 변경 없음
├── Dockerfile       # 변경 없음
└── requirements.txt # 변경 — langgraph 추가
```

### 테스트

```
tests/agent/
├── test_session.py       # 신규 (2-A) — SessionStore 단위 테스트
├── test_loop.py          # 변경 (2-A) — history 전달 테스트 추가
├── test_graph.py         # 신규 (2-B) — StateGraph 단위 테스트
├── test_main.py          # 변경 (2-A) — session_id 파라미터 테스트
└── test_mcp_client.py    # 변경 없음
```

---

## 5. 의존성

### Phase 2-A: 추가 없음

현재 `agent/requirements.txt`로 충분:
```
google-genai>=1.0.0
mcp>=1.6.0
fastapi>=0.115.0
uvicorn>=0.32.0
pydantic>=2.0.0
```

SessionStore는 순수 Python dict 기반. 외부 의존성 없음.

### Phase 2-B: langgraph 추가

```
# agent/requirements.txt 에 추가
langgraph>=0.4.0
```

**주의**: `langchain-core`가 langgraph의 전이 의존성으로 들어옴.
LangChain LCEL은 사용하지 않음 — LangGraph 단독 사용.

---

## 6. API 변경

### 현재 (Phase 1)

```python
# POST /chat
class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    response: str
```

### Phase 2-A 이후

```python
# POST /chat
class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None  # 없으면 새 세션 생성

class ChatResponse(BaseModel):
    response: str
    session_id: str  # 클라이언트가 후속 요청에 사용
```

**하위 호환성**: `session_id` 생략 시 단일 턴 동작 (Phase 1과 동일).

---

## 7. 핵심 구현 상세

### 7-1. loop.py 변경 (Phase 2-A)

현재 `run_agent(user_message: str)` → `run_agent(user_message: str, history: list | None = None)`

```python
# 변경 포인트 (loop.py:49~59)
async def run_agent(
    user_message: str,
    history: list[types.Content] | None = None,
) -> tuple[str, list[types.Content]]:
    """Agent Loop. history를 받아 대화를 이어간다."""
    mcp_tools = await list_mcp_tools()
    gemini_tool = _mcp_tools_to_gemini(mcp_tools)

    contents = list(history) if history else []
    contents.append(
        types.Content(
            role="user",
            parts=[types.Part.from_text(text=user_message)],
        )
    )
    # ... 이하 while 루프 동일 ...

    # 반환: (응답 텍스트, 전체 messages)
    return response.text or "", contents
```

**핵심**: `contents`를 외부에서 주입받고, 완료 후 전체 `contents`를 반환.
SessionStore가 이 `contents`를 저장/복원.

### 7-2. 토큰 제한 관리

Gemini 2.5 Flash 컨텍스트: 1,048,576 토큰.
RAG 검색 결과가 길 수 있으므로 히스토리 관리 필요:

```python
# agent/session.py
MAX_HISTORY_TURNS = 20  # 최근 20턴 유지
MAX_HISTORY_TOKENS_ESTIMATE = 100_000  # 대략적 토큰 추정

def trim_history(messages: list[Content]) -> list[Content]:
    """오래된 턴을 제거하여 토큰 한도 내로 유지."""
    if len(messages) <= MAX_HISTORY_TURNS * 2:  # user+assistant = 2
        return messages
    # system prompt(첫 턴) 보존 + 최근 N턴
    return messages[:1] + messages[-(MAX_HISTORY_TURNS * 2):]
```

### 7-3. 종합 리포트 (프롬프트 기반)

별도 코드 변경 없이 **시스템 프롬프트 강화**로 구현.
Gemini가 이미 멀티 Tool 호출 + 멀티스텝을 지원하므로,
"종합 분석" 키워드 시 재무 + 주가 + 공시를 조합하도록 안내:

```python
# loop.py SYSTEM_PROMPT에 추가
SYSTEM_PROMPT = (
    "당신은 한국 금융 데이터 분석 AI 어시스턴트입니다. "
    "DART 전자공시와 KRX 주가 데이터를 조회하는 도구를 사용하여 "
    "사용자의 질문에 정확하게 답변하세요. "
    "데이터를 조회한 후에는 핵심 수치를 포함하여 명확하게 요약해주세요.\n\n"
    "종합 분석을 요청받으면 다음 도구를 모두 활용하세요:\n"
    "1. get_financials — 재무제표 데이터\n"
    "2. get_stock_price — 최근 주가 동향\n"
    "3. search_documents — 공시 원문에서 사업 위험, 전망 등\n"
    "결과를 [재무 현황], [주가 동향], [주요 공시 내용] 섹션으로 구분하여 리포트를 작성하세요."
)
```

### 7-4. 멀티 기업 인덱싱

Phase 1의 `scripts/index_documents.py`가 이미 `--corps` 플래그 지원:

```bash
python scripts/index_documents.py --corps "삼성전자,LG화학" --years "2024"
```

FAISS 인덱스 재생성 후 search_documents의 `corp_name` 필터로 자연스럽게 동작.
**코드 변경 없음** — 인덱싱 재실행만 필요.

---

## 8. Phase 2-A → 2-B 전환

### 전환 기준

Phase 2-A 완료 조건 충족 후 전환:
- 대화 히스토리 동작 확인
- 종합 리포트 생성 확인
- 기존 테스트 전체 통과

### 전환 범위

| 항목 | Phase 2-A (while 루프) | Phase 2-B (LangGraph) |
|------|----------------------|----------------------|
| Agent 핵심 | loop.py (while) | graph.py (StateGraph) |
| 대화 상태 | session.py (dict) | LangGraph MemorySaver |
| MCP 연결 | mcp_client.py (동일) | mcp_client.py (동일) |
| API 스키마 | ChatRequest/Response (동일) | ChatRequest/Response (동일) |
| MCP Server | 변경 없음 | 변경 없음 |

### 비교 포인트 (README 포함)

Phase 2-B 완료 후 README에 추가할 비교 표:

| 비교 항목 | Phase 2-A (직접 구현) | Phase 2-B (LangGraph) |
|-----------|---------------------|----------------------|
| 코드 라인 수 | ~130줄 (loop.py + session.py) | ~??줄 (graph.py) |
| 대화 상태 관리 | 수동 (SessionStore) | 자동 (Checkpoint) |
| 상태 시각화 | 없음 | LangGraph Studio |
| 확장성 | 노드 추가 시 if/else 증가 | 노드/엣지 선언적 추가 |
| 의존성 | 0 추가 | langgraph + langchain-core |
| 학습 곡선 | 낮음 | 중간 |

→ 면접 질문 "왜 LangGraph를 선택했나"에 실측 데이터로 답변 가능.

---

## 9. CLAUDE.md 수정 필요 사항

Phase 2-B 진입 시 CLAUDE.md 변경:

```diff
- Phase 0에서 `langchain`, `langgraph`, `crewai` import (프레임워크 없이 구현 원칙)
+ Phase 0~2-A에서 `langchain`, `langgraph`, `crewai` import 금지.
+ Phase 2-B부터 `langgraph` 허용 (직접 구현 비교 완료 후 도입 근거 확보됨).
```

---

## 10. 도입 판단 근거

> Phase 1 완료 시점에서 Phase 2 방향을 결정하기 위해 수행한 분석 기록.

### 10-1. 현재 능력 갭 분석

Phase 1 완료 시점의 Agent Loop(loop.py)를 기능별로 평가:

| 미지원 기능 | 실질적 UX 영향 | 판단 |
|------------|---------------|------|
| 대화 히스토리 | **높음** — "작년 대비?" 같은 후속 질문 불가, 매 요청이 독립 | **해결 필요** |
| 병렬 Tool 호출 | 낮음 — Tool 4개, 순차 호출 응답 시간이 수용 가능 | YAGNI |
| 조건 분기/폴백 | 낮음 — Tool 실패율이 낮고, 실패 시 Gemini가 자연어로 안내 | YAGNI |
| 상태 저장/복원 | 낮음 — 분석 요청이 1회성, 중단→재개 시나리오 없음 | YAGNI |

**결론**: 대화 히스토리가 유일한 실질적 UX 문제. 나머지는 현 규모(1,494 청크, 단일 사용자, Tool 4개)에서 문제되지 않는다.

### 10-2. LangGraph 도입 필요성 평가

**현 시점에서 LangGraph는 기술적으로 불필요하다.**

- 대화 히스토리는 while 루프 + 인메모리 dict로 해결 가능 (Phase 2-A)
- StateGraph의 이점(시각화, 선언적 확장)은 노드 3개 이하에서 오버헤드
- langgraph 의존성 추가 → langchain-core 전이 의존성 포함

**그럼에도 도입하는 이유 — 포트폴리오 가치:**

1. **Before/After 실측 비교** — "왜 LangGraph를 선택했나" 면접 질문에 직접 구현 vs 프레임워크 정량 데이터로 답변 가능
2. **Constitution 준수** — "복잡성이 생길 때 도입" 원칙을 Phase 2-A 완료로 먼저 증명
3. **학습 트리거 충족** — CLAUDE.md §7 "에러, 품질 미달, 설명 불가 중 하나가 생길 때만 해당 개념을 파고든다" → 2-A 구현 후 graph 확장성 한계를 체감한 시점에 도입

### 10-3. 2-A/2-B 분리 결정

| 방안 | 장점 | 단점 | 판정 |
|------|------|------|------|
| LangGraph 직행 | 구현 1회 | Constitution 위반. 비교 데이터 없음 | **기각** |
| 2-A만 (LangGraph 보류) | 최소 변경 | 포트폴리오 가치 부족 | 보류 |
| **2-A → 2-B 순차** | Constitution 준수 + 비교 데이터 확보 | 구현 2회 | **채택** |

**채택 근거**: Phase 2-A의 구현 비용이 낮고(SessionStore ~50줄, loop.py 변경 ~10줄), 2-B에서 동일 기능을 LangGraph로 재구현하면 코드량·상태관리·확장성 정량 비교 표를 만들 수 있다.

### 10-4. YAGNI 적용 항목

| 항목 | 현재 판단 | 재검토 트리거 |
|------|----------|-------------|
| SessionStore → Redis | dict 유지 | 동시 사용자 >1 또는 서버 재시작 시 세션 보존 필요 |
| pgvector 마이그레이션 | FAISS 유지 | 인덱싱 대상 >5개 기업 또는 청크 >50,000 |
| 병렬 Tool 호출 | 순차 유지 | Tool 응답 시간 합계 >10초로 UX 저하 |
| 조건 분기/폴백 | 미구현 | Tool 실패율 >5% 또는 사용자 불만 |

---

## 11. 기술적 결정 근거

| 결정 | 선택 | 근거 |
|------|------|------|
| 2단계 분리 (2-A/2-B) | Phase 2-A 먼저 | CLAUDE.md "복잡성이 생길 때 도입" 원칙. 직접 구현 → LangGraph 비교로 포트폴리오 강화 |
| 세션 저장소 | 인메모리 dict | 단일 사용자 + Docker Compose 환경. Redis/DB 불필요 (YAGNI) |
| 히스토리 관리 | 턴 수 기반 트림 | Gemini 컨텍스트 100만+ 토큰이지만, RAG 결과 포함 시 보수적 관리 필요 |
| 리포트 생성 | 프롬프트 기반 | 별도 템플릿 엔진 불필요. Gemini 멀티스텝으로 충분 |
| Phase 1-2 (pgvector) | 여전히 보류 | 기업 2개, 청크 ~3,000 → FAISS 충분. 트리거 미충족 |
| LangGraph 버전 | ≥ 0.4.0 | StateGraph + MemorySaver 안정 버전 |

---

## 12. 구현 순서 (다음 세션용)

### Phase 2-A 체크리스트

1. `agent/session.py` 생성 — SessionStore (인메모리 dict, TTL, trim)
2. `agent/loop.py` 수정 — `run_agent(message, history)` 시그니처 변경
3. `agent/main.py` 수정 — `session_id` 파라미터 추가, SessionStore 연동
4. `SYSTEM_PROMPT` 강화 — 종합 리포트 안내 추가
5. 멀티 기업 인덱싱 — `index_documents.py --corps "삼성전자,LG화학"` 실행
6. 테스트 — test_session.py, test_loop.py 수정, test_main.py 수정
7. Docker 빌드 확인 — `docker compose up` 정상 동작
8. Steady State 확인 — 대화 지속 + 종합 리포트 생성

### Phase 2-B 체크리스트

1. `agent/requirements.txt` — `langgraph>=0.4.0` 추가
2. `agent/graph.py` 생성 — StateGraph (agent_node, tool_node, should_continue)
3. `agent/main.py` 수정 — `graph.run()` 호출로 교체
4. `CLAUDE.md` 수정 — langgraph import 허용
5. 테스트 — test_graph.py 생성, 기존 테스트 통과 확인
6. Docker 빌드 확인
7. README 비교 표 작성 (loop.py vs graph.py)
8. Steady State 확인 — Phase 2-A 동일 기능 동작

---

## 13. Steady State 최종 기준

| 항목 | Phase 2-A | Phase 2-B |
|------|-----------|-----------|
| 대화 지속 | "삼성전자 매출" → "작년 대비?" → 맥락 유지 답변 | 동일 |
| 종합 리포트 | "삼성전자 종합 분석" → 재무+주가+공시 통합 | 동일 |
| 멀티 기업 | 2개 이상 기업 인덱싱 + 검색 | 동일 |
| Docker | `docker compose up` 한 줄 기동 | 동일 |
| 비교 문서 | — | README에 loop.py vs graph.py 비교 표 |
