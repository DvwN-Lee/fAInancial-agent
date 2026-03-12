# Phase 3-A 설계 문서 — fAInancial-agent 프로덕션화

> **status**: current
> **작성일**: 2026-03-12
> **트랙**: Feature
> **브랜치**: `feat/phase3a-productionization`

---

## 1. 목표

Phase 2 (LangGraph 마이그레이션) 완료 후, fAInancial-agent를 "보여줄 수 있는 프로젝트"로 전환한다.

| 항목 | 내용 |
|------|------|
| CI | GitHub Actions — 자동 품질 관리 (pytest + lint) |
| UI | Streamlit 웹 인터페이스 — 채용 담당자가 즉시 사용 가능 |
| Observability | LangFuse self-hosted — 프로덕션 사고방식 증명 |
| Demo | README 스크린샷 + GIF — API 키 노출 없이 시연 가능 |

---

## 2. 아키텍처 변경

### 2-1. 현재 (Phase 2 완료 후)

```
Docker Compose
├── agent    (FastAPI :8000)
└── mcp      (MCP Server :8001)
```

### 2-2. Phase 3-A 완료 후

```
Docker Compose
├── agent      (FastAPI :8000)
├── mcp        (MCP Server :8001)
├── ui         (Streamlit :8501)
└── langfuse   (LangFuse :3000 + PostgreSQL)
```

### 2-3. 트레이싱 흐름

```
사용자 → Streamlit UI
         → POST /chat (FastAPI)
           → run_graph() + LangFuse CallbackHandler
             → LangFuse Server (trace 저장)
             → Gemini LLM + MCP Tool 호출
           ← 응답 텍스트
         ← 채팅 메시지 출력
```

---

## 3. T1 — GitHub Actions CI

### 파일

- `.github/workflows/ci.yml`

### 인터페이스

```yaml
# 트리거
on:
  push:
    branches: [main, "feat/**"]
  pull_request:
    branches: [main]

# 스텝
steps:
  - uses: actions/checkout@v4
  - uses: astral-sh/setup-uv@v5
  - run: uv sync --frozen
  - run: uv run pytest tests/ -v --tb=short
  - run: uv run ruff check .
```

### 설계 결정

| 항목 | 결정 | 근거 |
|------|------|------|
| 패키지 관리 | `uv` | 기존 pyproject.toml/uv.lock 일치 |
| Lint | `ruff` | 기존 ruff 설정 존재 확인 필요 |
| 시크릿 불필요 | 모든 테스트가 mock 기반 | 실제 API 키 없이 91개 테스트 전부 통과 |
| Python 버전 | 3.12 | pyproject.toml 기준 |

---

## 4. T2 — Streamlit UI

### 파일

- `ui/app.py`
- `ui/Dockerfile`

### 인터페이스

```python
# 환경변수
AGENT_API_URL: str  # default: "http://agent:8000" (Docker), "http://localhost:8000" (local)

# 상태 (st.session_state)
session_state.messages: list[dict]  # {"role": "user"|"assistant", "content": str}
session_state.session_id: str | None  # FastAPI session_id 라운드트립

# API 호출
POST {AGENT_API_URL}/chat
Body: {"message": str, "session_id": str | None}
Response: {"response": str, "session_id": str}
```

### UI 구성

```
┌─────────────────────────────────────────┐
│  fAInancial Agent                       │
│  재무 데이터 AI 어시스턴트              │
├─────────────────────────────────────────┤
│  [assistant] 안녕하세요! ...            │
│  [user]      삼성전자 2024 매출은?      │
│  [assistant] 삼성전자 2024년 매출은...  │
│                                         │
├─────────────────────────────────────────┤
│  메시지를 입력하세요...        [전송]   │
└─────────────────────────────────────────┘
```

### 설계 결정

| 항목 | 결정 | 근거 |
|------|------|------|
| 라이브러리 | Streamlit | 빠른 구현, 포트폴리오 표준 |
| API 통신 | `httpx` (async) or `requests` | FastAPI `/chat` 엔드포인트 재사용 |
| 세션 관리 | `st.session_state.session_id` | 페이지 새로고침 시 새 세션 시작 |
| 라이브 호스팅 | 미적용 | API 키 노출 위험 — 스크린샷/GIF로 대체 |
| 포트 | 8501 | Streamlit 기본값 |

### Docker Compose 추가

```yaml
ui:
  build: ./ui
  ports:
    - "8501:8501"
  environment:
    - AGENT_API_URL=http://agent:8000
  depends_on:
    - agent
```

---

## 5. T3 — LangFuse Observability

### 파일

- `docker-compose.langfuse.yml` (별도 Compose 파일로 선택적 활성화)
- `agent/graph.py` 수정 (CallbackHandler 주입)

### 인터페이스

```python
# agent/graph.py — run_graph() 변경
from langfuse.callback import CallbackHandler

async def run_graph(user_message: str, session_id: str) -> str:
    langfuse_handler = _get_langfuse_handler(session_id)  # 키 없으면 None
    config = {"configurable": {"thread_id": session_id}}
    if langfuse_handler:
        config["callbacks"] = [langfuse_handler]
    # ... 기존 로직 동일

def _get_langfuse_handler(session_id: str) -> CallbackHandler | None:
    """LANGFUSE_* 환경변수 미설정 시 None 반환 (graceful degradation)."""
    public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
    secret_key = os.getenv("LANGFUSE_SECRET_KEY")
    host = os.getenv("LANGFUSE_HOST", "http://langfuse:3000")
    if not public_key or not secret_key:
        return None
    return CallbackHandler(
        public_key=public_key,
        secret_key=secret_key,
        host=host,
        session_id=session_id,
    )
```

### LangFuse Docker Compose

```yaml
# docker-compose.langfuse.yml
services:
  langfuse-db:
    image: postgres:15
    environment:
      POSTGRES_USER: langfuse
      POSTGRES_PASSWORD: langfuse
      POSTGRES_DB: langfuse

  langfuse:
    image: langfuse/langfuse:latest
    ports:
      - "3000:3000"
    environment:
      DATABASE_URL: postgresql://langfuse:langfuse@langfuse-db:5432/langfuse
      NEXTAUTH_SECRET: ${LANGFUSE_NEXTAUTH_SECRET}
      NEXTAUTH_URL: http://localhost:3000
      SALT: ${LANGFUSE_SALT}
    depends_on:
      - langfuse-db
```

### 실행 방법 (선택적)

```bash
# 기본 (LangFuse 없이)
docker compose up

# LangFuse 포함
docker compose -f docker-compose.yml -f docker-compose.langfuse.yml up
```

### 설계 결정

| 항목 | 결정 | 근거 |
|------|------|------|
| Self-hosted | `langfuse/langfuse` Docker 이미지 | 직접 운영 = 포트폴리오 증명 |
| 별도 Compose 파일 | `docker-compose.langfuse.yml` | 기본 실행에 영향 없음 (YAGNI) |
| Graceful degradation | 키 없으면 CallbackHandler 미주입 | `docker compose up` 한 줄 유지 |
| 트레이싱 단위 | `run_graph()` 호출 = 1 trace | LangGraph run 단위와 일치 |

---

## 6. T4 — Demo 산출물

### 파일

- `docs/demo/` 디렉토리 (스크린샷 + GIF)
- `README.md` 업데이트

### 내용

| 항목 | 방법 |
|------|------|
| UI 스크린샷 | Streamlit 실행 후 캡처 (Docker + 실제 API 키) |
| 대화 GIF | 삼성전자 매출 → 종합 리포트 시나리오 |
| README 업데이트 | Quick Start에 UI URL (:8501) 추가, CI 뱃지, 스크린샷 삽입 |

---

## 7. 변경 파일 목록

| 파일 | 변경 유형 | 태스크 |
|------|----------|--------|
| `.github/workflows/ci.yml` | 신규 | T1 |
| `ui/app.py` | 신규 | T2 |
| `ui/Dockerfile` | 신규 | T2 |
| `docker-compose.yml` | 수정 (ui 서비스 추가) | T2 |
| `docker-compose.langfuse.yml` | 신규 | T3 |
| `agent/graph.py` | 수정 (LangFuse CallbackHandler) | T3 |
| `agent/requirements.txt` | 수정 (`langfuse` 추가) | T3 |
| `docs/demo/` | 신규 | T4 |
| `README.md` | 수정 (CI 뱃지, 스크린샷, UI 안내) | T4 |

총 변경: 9개 파일 (Feature Track 6~20파일 범위 내)

---

## 8. YAGNI 적용 항목

| 항목 | 판단 | 근거 |
|------|------|------|
| 라이브 데모 호스팅 | 미적용 | API 키 노출 위험 |
| RAGAS CI | 미적용 | Nice-to-have, 현재 MVP에 불필요 |
| K8s 배포 | 미적용 | Phase 3-B(별도 레포) 대상 |
| Redis 세션 | 미적용 | 인메모리 dict 충분 |
| UI 인증 | 미적용 | 포트폴리오 데모용, 보안 레이어 불필요 |
| LangFuse 항상 활성 | 미적용 | 선택적 Compose 파일로 분리 |
