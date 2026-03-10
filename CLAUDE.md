# CLAUDE.md — fAInancial-agent

> **프로젝트 유형**: Python AI Agent — MCP + Financial Data
> **Phase 0 상태**: 진행 중

---

## Constitution

fAInancial-agent 프로젝트 관리 시 반드시 준수해야 하는 불변 원칙이다.

### 핵심 원칙

1. **구현 우선** — 이론을 다 이해한 다음 구현하지 않는다. 동작하는 것을 먼저 만들고, 막히면 그 시점에 학습한다
2. **MCP Tool = 수단** — DART/KRX MCP 서버는 Agent가 데이터를 가져오기 위한 Tool이다. MCP 서버 자체가 목표가 아니다
3. **프레임워크 금지 (Phase 0)** — Agent Loop는 while 루프 + tool_use 파싱으로 직접 구현한다. LangChain/LangGraph는 Phase 2에서 복잡성이 생길 때 도입한다
4. **레포가 포트폴리오** — 첫 커밋부터 공개. 완성본이 아니라 진행 과정이 증거물이다
5. **환경변수 분리** — API 키는 `.env`에만. 코드에 하드코딩하지 않는다
6. **Docker Compose 단위 배포** — 로컬 실행은 항상 `docker compose up` 한 줄로 가능해야 한다
7. **학습 트리거는 문제다** — 에러, 품질 미달, 설명 불가 중 하나가 생길 때만 해당 개념을 파고든다

### 금지 행동

- `.env` 파일 직접 수정 또는 생성 (Human 전용)
- API 키, 토큰을 코드에 하드코딩
- Phase 0에서 `langchain`, `langgraph`, `crewai` import (프레임워크 없이 구현 원칙)
- `docs/handoffs/` 내 파일 수정 또는 생성 (Human 전용)
- MCP 서버 없이 DART/KRX API를 Agent에서 직접 호출 (Tool 추상화 원칙)

### 작업 흐름

```
자연어 입력 (POST /chat)
        ↓
  Agent Loop (agent/loop.py)
  └─ while stop_reason != "end_turn":
        ↓ tool_use 응답
  MCP Client → MCP Server (mcp_server/main.py)
  ├─ dart_financials()   ← DART OpenAPI
  └─ krx_price()         ← KRX / FinanceDataReader
        ↓ tool_result
  LLM 최종 응답
        ↓
  FastAPI (agent/main.py) → Docker Compose 배포
```

### Steady State 기준

| 항목 | 기준 |
|------|------|
| Agent Loop 동작 | "삼성전자 2025년 매출 알려줘" → DART Tool 호출 → LLM 요약이 터미널에서 확인됨 |
| Docker Compose 실행 | `docker compose up` 한 줄로 MCP 서버 + Agent API 전체 기동 |
| README 완성도 | 아키텍처 다이어그램(Mermaid) + Quick Start 포함 |

---

## PR Writing Rules

- Do not include "Generated with [Claude Code](...)" or "🤖 Generated with" lines in PR descriptions.
- Do not include "Co-Authored-By: Claude ..." lines in PR descriptions or commit messages.
- Use `.claude/hooks/pr-wrapper.sh` to strip these lines before posting a PR description.
- Use `.claude/hooks/strip-claude-meta.sh` as a commit-msg hook to strip them from commits.
