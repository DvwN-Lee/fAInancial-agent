---
name: saga-phase-gate
description: Use when entering a Phase, checking Phase Gate conditions, running BUILD/VERIFY steps, writing Spec/design/dod.md, or switching tracks. Triggers on phrases like "Phase 진입", "Gate 확인", "Phase 1", "Phase 2", "Phase 3", "Phase 4", "Phase 5", "빌드", "구현 시작", "검증", "Spec 작성", "dod.md", "TDAID", "트랙 전환".
---

# SAGA Phase Gate 운용 지침

## Permission Mode

| Phase | 명칭 | Permission Mode |
|-------|------|----------------|
| 0 | FOUNDATION | `default` |
| 1 | SPECIFICATION | `plan` |
| 2 | DESIGN | `acceptEdits` |
| 3 | BUILD | `acceptEdits` + Hooks 활성화 |
| 4 | VERIFY | `plan` |
| 5 | REFINE | `acceptEdits` |

## Phase별 필수 산출물

| 산출물 | Phase | Hotfix | Feature | Epic | 생성 주체 |
|--------|:-----:|:------:|:-------:|:----:|---------|
| `CLAUDE.md` | 0 | Y | Y | Y | Agent |
| `.claude/settings.json` | 0 | Y | Y | Y | Agent |
| `project-brief.md` | 0 입력 | — | Y | Y | Human 작성 |
| `requirements.md` (EARS) | 1 | — | — | Y | Agent |
| `design.md` | 2 | — | Y | Y | Agent |
| `tasks.md` | 2 | — | Y | Y | Agent |
| `docs/dod.md` | 2 | — | Y | Y | Agent |
| 코드 + 테스트 | 3 | Y | Y | Y | Agent |
| `docs/verify-report-YYYYMMDD.md` | 4 | — | Y | Y | Agent |
| `docs/handoffs/phase-N-YYYYMMDD-HHmm.md` | Gate 전환 시 | 권장 | Y | Y | **Agent** |

## Phase Gate 조건

**Phase 0 → 1 (또는 트랙 진입):**
- CLAUDE.md Constitution 완비
- settings.json allow/deny/ask 구성 완료
- Hook 스크립트 배포 및 테스트 완료

**Phase 1 → 2 (Epic Track):**
- 모든 요구사항에 **EARS 표기법** 적용 완료
- `[NEEDS CLARIFICATION]` 태그 0건
- VETO 미해소 건수 0건
- **Wave 분할 계획 수립** (Phase 2 병렬 Subagent 설계 선행 조건)
- Handoff 파일 시크릿 스캐닝 통과 (보안 Gate): `detect-secrets scan docs/handoffs/` 실행 후 0건 확인. 스캐너 미설치 시 Human에게 확인 요청 후 대기.
- requirements.md Human 승인

**Phase 2 → 3:**
- design.md 모든 인터페이스 정의 완료
- tasks.md 의존성 그래프 순환 없음
- **`docs/dod.md` 작성 및 완비**

**Phase 3 BUILD — TDAID 5-Phase TDD 루프:**

Phase 3 각 태스크는 다음 5단계 루프로 실행한다:
```
[Plan]     테스트 전략 수립, 경계 조건 사전 식별
[Red]      실패 테스트 작성
[Green]    최소 구현
[Refactor] 리팩터링 (커버리지 감소 없음, 기능 추가 없음 조건 충족 시에만)
[Validate] 통합 테스트 + 커버리지 검증 + dod.md 체크리스트 확인 (Feature/Epic Track에만 적용)
```
Validate 통과 = Phase 3→4 Gate 사전 점검 완료.

**Phase 3 → 4:**
- **모든 tasks.md 항목 완료** (미완료 항목 0건, Feature/Epic Track에만 적용)
- 전체 테스트 suite 통과 + Lint/Type check 통과
- PR 생성 완료
- Phase 4 Validator는 Phase 3 Generator와 다른 Subagent 인스턴스 사용

**Phase 4 → 완료 (Feature Track):**
- 교차 검증 리포트 완성
- 이슈별 심각도 분류 완료
- CRITICAL 이슈 0건 (발견 시 Phase 3 회귀)
- PR 리뷰 Human Approve

**Phase 4 → 5 (Epic Track):**
- 교차 검증 리포트 완성
- 이슈별 심각도 분류 완료
- CRITICAL 이슈 0건 (발견 시 Phase 3 회귀)
- Spec↔Code 동기화 검증 완료

**Phase 5 → 완료 (Epic Track):**
- 모든 CRITICAL/MAJOR 수정 완료
- Spec↔Code 동기화 최종 확인
- 최종 PR Human 승인

## Spec↔Code Drift 원칙

**코드를 Spec에 맞게 수정한다. Spec을 코드에 맞추는 방향(Spec 후퇴)은 금지.**

drift 감지 (Spec 파일 최근 변경 이력 확인):
```bash
git diff HEAD -- docs/design.md docs/requirements.md
```

코드↔Spec 드리프트 실질 판단은 **테스트 결과 + 수동 리뷰**로 확인한다. 위 명령은 Spec 파일 자체의 변경 여부만 보여주며, 코드가 Spec을 따르는지는 별도 검토가 필요하다.

- drift가 CRITICAL(인터페이스 파괴 등)이면 → Phase 2 재시작 (Human 개입)
- drift가 의도적 설계 변경이면 → Phase 5 REFINE에서 요구사항 변경 절차를 거쳐 Spec 갱신

## Handoff 파일 원칙

| 파일 | 생성 주체 | 수정 가능 여부 |
|------|----------|-------------|
| `docs/handoffs/phase-N-YYYYMMDD-HHmm.md` | **Agent** (Gate 전환 시) | Agent 생성 후 수정 가능 |
| `docs/handoffs/HANDOFF.md` (대시보드) | **Human 전용** | Agent 수정·생성 금지 |

> CLAUDE.md Constitution의 `docs/handoffs/` 금지 규칙이 있는 경우,
> phase-N 파일 생성 허용으로 Constitution을 수정하거나, Human이 직접 생성한다.

## Phase 진입 시 입력 산출물 미존재 처리

Phase 진입 전 위 산출물 표의 해당 입력 산출물을 확인한다.
**미존재 시 → Human에게 해당 산출물 제공 요청 후 대기. Phase 진입 보류.**
