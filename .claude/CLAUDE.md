# CLAUDE.md — fAInancial-agent

> **프로젝트 유형**: Python AI Agent — MCP + Financial Data
> **현재 상태**: Phase 3-A 완료, UI/UX 개선 완료 (PR #5 merged)

---

## Constitution

fAInancial-agent 프로젝트 관리 시 반드시 준수해야 하는 불변 원칙이다.

### 핵심 원칙

1. **구현 우선** — 이론을 다 이해한 다음 구현하지 않는다. 동작하는 것을 먼저 만들고, 막히면 그 시점에 학습한다
   - 실행 기준: 동작하는 최소 단위(예: "DART에서 데이터 1건 조회")를 먼저 커밋. 엣지 케이스는 그 이후에 처리
2. **MCP Tool = 수단** — DART/KRX MCP 서버는 Agent가 데이터를 가져오기 위한 Tool이다. MCP 서버 자체가 목표가 아니다
   - 실행 기준: Agent 코드에서 DART/KRX API를 직접 호출하는 import가 있으면 위반
3. **프레임워크 단계적 도입** — Phase 0~1은 while 루프 + tool_use 파싱으로 직접 구현. Phase 2-B부터 LangGraph/langchain-google-genai 도입 (loop.py 보존)
   - 실행 기준: `agent/loop.py`, `agent/session.py`는 Phase 0 참조용으로 삭제하지 않음
4. **레포가 포트폴리오** — 첫 커밋부터 공개. 완성본이 아니라 진행 과정이 증거물이다
   - 실행 기준: 모든 기술 선택에 ADR 작성. 의사결정 시점에 즉시 기록
5. **환경변수 분리** — API 키는 `.env`에만. 코드에 하드코딩하지 않는다
   - 실행 기준: `grep -r "API_KEY\|SECRET" --include="*.py"` 결과가 `os.environ`/`os.getenv` 참조만 포함
6. **Docker Compose 단위 배포** — 로컬 실행은 항상 `docker compose up` 한 줄로 가능해야 한다
   - 실행 기준: 클린 환경에서 `.env` 설정 후 `docker compose up`으로 http://localhost:8501 정상 접속
7. **학습 트리거는 문제다** — 에러, 품질 미달, 설명 불가 중 하나가 생길 때만 해당 개념을 파고든다
   - 실행 기준: 테스트 실패, lint 경고, PR 리뷰에서 "왜?" 질문에 답하지 못할 때 학습 시작

### 금지 행동

- `.env` 파일 직접 수정 또는 생성 (Human 전용)
- API 키, 토큰을 코드에 하드코딩
- `crewai` import (불필요한 프레임워크 금지)
- Phase 0~1에서 `langchain`, `langgraph` import (Phase 2-B부터 허용)
- `docs/handoffs/` 내 파일 수정 또는 생성 (Human 전용)
- MCP 서버 없이 DART/KRX API를 Agent에서 직접 호출 (Tool 추상화 원칙)

### 작업 흐름

```
자연어 입력 (POST /chat)
        ↓
  LangGraph StateGraph (agent/graph.py)
  ├─ agent_node → Gemini LLM (langchain-google-genai)
  ├─ tool_node  → MCP Client → MCP Server (mcp_server/main.py)
  │  ├─ dart_financials()   ← DART OpenAPI
  │  └─ krx_price()         ← KRX / FinanceDataReader
  └─ InMemorySaver → 세션 자동 관리
        ↓
  FastAPI (agent/main.py) → Docker Compose 배포

  (참고: Phase 0~1 원본은 agent/loop.py + agent/session.py에 보존)
```

### Steady State 기준

| 항목 | 기준 |
|------|------|
| Agent Loop 동작 | "삼성전자 2025년 매출 알려줘" → DART Tool 호출 → LLM 요약이 터미널에서 확인됨 |
| Docker Compose 실행 | `docker compose up` 한 줄로 MCP 서버 + Agent API 전체 기동 |
| README 완성도 | 아키텍처 다이어그램(Mermaid) + Quick Start 포함 |

### 환경변수 구조

필수 (`.env`에 설정):
- `GEMINI_API_KEY` — Gemini LLM 호출
- `DART_API_KEY` — DART OpenAPI 재무제표/공시

선택 (LangFuse 사용 시):
- `LANGFUSE_PUBLIC_KEY` — LangFuse 대시보드 Settings > API Keys에서 발급
- `LANGFUSE_SECRET_KEY` — 위와 동일
- `ENCRYPTION_KEY` — `openssl rand -hex 32`로 생성 (LangFuse v3 필수)

---

## SAGA 운용 지침

SAGA 방법론의 운용 지침은 별도의 skill(`saga-methodology:saga-phases` 등)로 관리됩니다.

---

## PR Writing Rules

- Do not include "Generated with [Claude Code](...)" or "🤖 Generated with" lines in PR descriptions.
- Do not include "Co-Authored-By: Claude ..." lines in PR descriptions or commit messages.
- Use `.claude/hooks/pr-wrapper.sh` to strip these lines before posting a PR description.
- Use `.claude/hooks/strip-claude-meta.sh` as a commit-msg hook to strip them from commits.
