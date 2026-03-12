---
name: saga-recovery
description: Use when handling failures, errors, or unexpected stops during any phase. Triggers on phrases like "실패", "오류", "Circuit Breaker", "테스트 실패", "에스컬레이션", "롤백", "재시도", "막힘", "진행 불가".
---

# SAGA 실패 대응 지침

**모든 자동 중단 시 `git commit`으로 현재 상태를 먼저 보존한다.**

| 상황 | 조치 |
|------|------|
| 동일 패턴 오류 2회 연속 | 다른 프롬프트/접근 방식으로 재시도 |
| Circuit Breaker OPEN | `git commit` → 상위 모델로 새 Subagent spawn → 미해소 시 Human 에스컬레이션 |
| Phase Gate 체크리스트 미충족 | 1회 자동 재시도 → 실패 시 이전 Phase 롤백 + Human 통보 |
| `status="failed"` 응답 | Spot-check(출력 파일 존재 + `git log`) 후 성공 여부 재판단 |

## Circuit Breaker

**발동 조건:** 동일 Subagent에서 연속 3회 테스트 실패 코드 생성 또는 TDD cycle 3회 비수렴.

**모델 교체 매트릭스** (상위 모델로 새 Subagent spawn — Claude 자신의 모델 교체 불가):

| 현재 Subagent 모델 | 교체 대상 | 미해소 시 |
|-------------------|-----------|---------|
| Haiku | → Sonnet | → Opus |
| Sonnet | → Opus | → Human 에스컬레이션 |
| Opus | → Human 에스컬레이션 | — |

## Human 에스컬레이션 포맷

```
## 실패 요약
### 시도한 접근
### 실패 원인
### 선택지
```
