# 문서 네비게이션

> fAInancial-agent 프로젝트의 전체 문서 구조와 권장 읽기 경로입니다.

---

## 문서 카테고리

| 카테고리 | 위치 | 설명 |
|----------|------|------|
| 프로젝트 소개 | [`README.md`](../README.md) | 아키텍처, Quick Start, 데모, 기술 스택 |
| 아키텍처 결정 | [`docs/adr/`](adr/README.md) | 10건의 ADR (기술 선택 근거) |
| 설계 문서 | [`docs/superpowers/specs/`](superpowers/specs/) | VETO 합의 기반 설계 분석 |
| 구현 계획 | [`docs/superpowers/plans/`](superpowers/plans/) | Task 단위 구현 플랜 |
| 검증 보고서 | [`docs/verify-report-*.md`](./) | Phase 4 VERIFY Gate 결과 |
| 데모 자산 | [`docs/demo/`](demo/README.md) | 스크린샷 캡처 가이드 |
| 프로젝트 규칙 | [`.claude/CLAUDE.md`](../.claude/CLAUDE.md) | Constitution, 금지 행동, Steady State |

---

## 권장 읽기 경로

### 처음 방문한 개발자

```
README.md (프로젝트 개요 + Quick Start)
    ↓
docs/adr/README.md (기술 스택 한눈에 파악)
    ↓
ADR-001 → ADR-002 → ADR-003 (핵심 아키텍처 3건)
```

### 기술 스택을 깊이 이해하고 싶을 때

```
ADR-001 LangGraph (Agent 프레임워크)
    ├→ ADR-002 Gemini (LLM)
    ├→ ADR-003 MCP (Tool 통신) → ADR-010 DART/KRX (데이터 소스)
    └→ ADR-006 FastAPI (API) → ADR-007 Streamlit (UI)

ADR-004 Voyage AI (임베딩) → ADR-005 FAISS (벡터 DB)

ADR-008 Docker Compose (배포 — 모든 서비스 통합)
ADR-009 LangFuse (Observability — 선택)
```

### 프로젝트 진행 과정을 추적하고 싶을 때

```
1. docs/superpowers/specs/2026-03-13-adr-tech-stack-design.md
   (ADR 작성 기준 설계)

2. docs/superpowers/specs/2026-03-14-langfuse-v3-upgrade-design.md
   → docs/superpowers/plans/2026-03-14-langfuse-v3-upgrade.md
   (LangFuse v3 설계 → 구현 플랜)

3. docs/superpowers/specs/2026-03-15-langfuse-demo-scenario-analysis.md
   → docs/superpowers/specs/2026-03-16-e2e-demo-scenario-design.md
   (데모 시나리오 분석 → 재설계)

4. docs/superpowers/specs/2026-03-16-langfuse-demo-execution-review.md
   (실행 리뷰: 예상 vs 실제)

5. docs/superpowers/plans/2026-03-16-readme-demo-story.md
   → docs/superpowers/specs/2026-03-16-readme-demo-story-review.md
   (README 데모 스토리 플랜 → VETO 리뷰)

6. docs/superpowers/specs/2026-03-16-project-retrospective.md
   (프로젝트 전체 회고)
```

### 검증 결과만 확인하고 싶을 때

```
docs/verify-report-20260313.md     — Phase 3-A 검증 (PR #4)
docs/verify-report-20260313-pr5.md — Phase 3-B UI/UX 검증 (PR #5)
```

---

## 계층 다이어그램

```
┌─────────────────────────────────────────┐
│  README.md (진입점)                      │
├─────────────────────────────────────────┤
│  docs/adr/          10건 ADR            │
│  ├── LLM Layer      001, 002            │
│  ├── Tool Layer     003, 010            │
│  ├── Search Layer   004, 005            │
│  ├── App Layer      006, 007            │
│  └── Infra Layer    008, 009            │
├─────────────────────────────────────────┤
│  docs/superpowers/  설계 + 플랜          │
│  ├── specs/         VETO 기반 설계 분석   │
│  └── plans/         Task 단위 구현 플랜   │
├─────────────────────────────────────────┤
│  docs/verify-*      Phase 4 검증 보고서   │
├─────────────────────────────────────────┤
│  docs/demo/         데모 자산 + 캡처 가이드│
├─────────────────────────────────────────┤
│  .claude/CLAUDE.md  프로젝트 규칙        │
└─────────────────────────────────────────┘
```
