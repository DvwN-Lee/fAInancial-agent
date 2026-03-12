# SAGA 운용 지침 (Claude Code Operational Protocol)

> 이 파일은 매 세션 항상 로드되는 핵심 운용 프로토콜이다.
> Phase·Agent·실패 대응 세부 지침은 아래 Skills를 호출한다.
> 프로젝트의 CLAUDE.md(Constitution)와 함께 적용되며, 충돌 시 CLAUDE.md가 우선한다.

**관련 Skills (필요 시 호출):**
- `saga-phase-gate` — Phase 진입·Gate 조건·TDAID·Spec Drift
- `saga-agents` — Subagent 구성·모델 티어링·Worktree·Agent Teams·VETO
- `saga-recovery` — 실패 대응·Circuit Breaker·에스컬레이션

---

## 1. 세션 시작 체크 (매 세션)

세션 시작 시 아래 순서대로 컨텍스트를 로드한다.

1. `memory/MEMORY.md` — 이전 세션 패턴 및 아키텍처 결정 확인
2. `docs/handoffs/HANDOFF.md` — 현재 Phase Gate 상태 확인 (없으면 Phase 0부터)
3. `docs/improvements/INDEX.md` — 미해결 개선 항목 확인
4. `status: pending-update` 파일 — 7일 내 해소 필요 항목 식별

**판단:**
- HANDOFF.md에 진행 중인 Phase가 있으면 → 해당 Phase 작업 재개
- 신규 작업 요청이면 → 트랙 판단 후 적절한 Phase 진입

---

## 2. 트랙 선택

작업 규모에 따라 3-Track 중 하나를 선택한다. **기준 중 하나라도 상위 트랙에 해당하면 상위 트랙 선택 (안전 우선).**

| 트랙 | 판단 기준 (Feature/Epic: OR, Hotfix: AND) | Phase 경로 |
|------|------------------------------------------|-----------|
| **Hotfix** | 변경 ≤5파일 **AND** 단일 버그 수정 **AND** Subagent 불필요 | Phase 3 → 4-Auto |
| **Feature** | 변경 6~20파일 **또는** 신규 모듈 ≤1개 **또는** Subagent 1~2개 | Phase 2 → 3 → 4 |
| **Epic** | 변경 >20파일 **또는** 신규 시스템 계층 **또는** Subagent ≥3개 | Phase 1 → 2 → 3 → 4 → 5 |

**4-Auto (Hotfix Phase 4):** 자동 테스트 suite + lint + type check만 실행. Human 교차 검증·성능 Gate 생략. 전체 통과 시 바로 PR Merge.

**트랙 전환:** 작업 중 실제 규모가 초기 판단을 초과하면 즉시 상위 트랙으로 전환.
전환 전 `git commit`으로 현재 상태를 보존하고, 상위 트랙의 첫 Phase부터 재개한다.

---

## 3. 문서 관리 원칙

### SSOT (Single Source of Truth)
- 개념의 정의는 단일 파일에서만 한다
- 다른 파일에서는 `[텍스트](../파일.md#섹션)` 형식의 공식 링크로 참조
- "~에서 설명한 것처럼" 같은 비공식 참조는 sync-check.sh가 탐지하지 못하므로 사용 금지

### status 필드
`methodology/`, `research/` 하위 모든 파일 헤더에 필수.

| 값 | 의미 |
|----|------|
| `current` | 최신 상태 |
| `pending-update` | 업데이트 필요 (7일 내 해소 권장) |
| `archive` | 이력 보존용, 수정 불필요 |

신규 문서 생성 시 반드시 `> **status**: current`를 헤더에 포함한다.

---

## 4. 세션 마무리

### MEMORY.md 업데이트

저장해야 할 것:
- 여러 세션에서 반복 확인된 안정적 패턴
- 핵심 아키텍처 결정 (변경 가능성 낮음)
- 반복 발생 문제의 해결법

저장하면 안 되는 것:
- 현재 세션의 임시 상태
- 단일 세션에서만 확인된 패턴
- CLAUDE.md와 중복되는 내용

### Handoff 원칙

- `docs/handoffs/HANDOFF.md` 대시보드는 **절대 수정하지 않는다** (Human 전용)
- `docs/handoffs/phase-N-*.md` 파일은 Gate 전환 시 Agent가 생성한다
- 다음 세션을 위한 컨텍스트는 `memory/MEMORY.md`에 저장

---

## 5. 보안 운용

### 레이어 인식

```
Layer 1: 시스템 프롬프트  → 확률적 behavioral
Layer 2: settings.json   → 확률적 behavioral (알려진 버그로 간헐적 무시 가능)
Layer 3: PreToolUse Hook → 결정론적 (exit 2 = 강제 차단, 모델 우회 불가)
```

settings.json deny는 완벽하지 않다. Hook이 없는 상태에서 deny가 무시되는 버그가 존재한다.
진정한 기술적 차단이 필요한 항목은 Hook의 exit 2로 강제한다.

### 민감 파일 보호

작업 중 다음 파일은 직접 읽거나 수정하지 않는다:
`.env`, `.env.*`, `*.pem`, `*.key`, `credentials*`, `secrets*`, `terraform.tfvars`
