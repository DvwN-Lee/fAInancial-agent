# fAInancial-agent 개선사항 인덱스

> **상태**: 초기 구성
> **작성일**: 2026-03-10

---

## 개요

fAInancial-agent 프로젝트의 개선사항을 우선순위별로 추적하는 로드맵 문서.

## 우선순위별 통합 로드맵

### P0: 즉시 — Phase 0 완료 기준

| # | 영역 | 조치 | 상태 |
|---|------|------|:----:|
| 0-1 | MCP Server | DART Tool (재무제표·공시 검색) + KRX Tool (주가) 구현 | - |
| 0-2 | Agent Loop | while + tool_use 파싱 직접 구현 → "삼성전자 매출" 시나리오 동작 | - |

### P1: 단기 — Phase 1 (RAG)

| # | 영역 | 조치 | 관련 문서 |
|---|------|------|----------|
| 1-1 | RAG Tool | DART 공시 PDF → FAISS 벡터 검색 → MCP Tool 응답에 통합 | Phase 1 태그 |
| 1-2 | 품질 측정 | RAGAS 지표 도입 — 검색 품질 수치화 | README 테이블 |

### P2: 중기 — Phase 2 (Multi-Agent)

| # | 영역 | 조치 | 관련 문서 |
|---|------|------|----------|
| 2-1 | 오케스트레이션 | LangGraph StateGraph로 Agent Loop 재구성 | Phase 2 태그 |
| 2-2 | 프레임워크 비교 | CrewAI로 동일 워크플로우 재구현 → LangGraph 대비 실측 비교 | 벤치마크 문서 |

---

## 권한 정책 매트릭스

### 파일 작업 권한

| 작업 | 프로젝트 내부 (일반) | 프로젝트 내부 (보안 경계) | 프로젝트 내부 (민감 데이터) |
|------|:---:|:---:|:---:|
| **CREATE** | Allow | Human | Human |
| **EDIT** | Allow | Human | Human |
| **DELETE** | Human | Human | Human |
| **READ** | Allow | Allow | Deny |

**보안 경계 파일**: `.claude/settings.json`, `.claude/hooks/*`, `CLAUDE.md`
**민감 데이터 파일**: `.env*`, `*credentials*`, `*secrets*`, `*.pem`, `*.key`

### 민감 데이터 파일 접근 정책

`.env` 파일은 **Deny**하되, `.env.example`만 Read/Edit **Allow**:

```
.env            → Deny (Read/Edit/Create 모두 차단)
.env.*          → Deny (실제 값 파일)
.env.example    → Allow (Read + Edit 허용)
```
