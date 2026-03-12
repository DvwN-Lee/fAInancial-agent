---
name: saga-agents
description: Use when configuring agents/subagents, spawning Agent Teams, running VETO protocol, or deciding between direct work vs delegation. Triggers on phrases like "Subagent", "Agent Teams", "팀 구성", "VETO", "병렬 실행", "Worktree", "모델 선택", "리뷰어 구성", "다관점 검토".
---

# SAGA 에이전트 구성 및 VETO 운용 지침

## 에이전트 선택 기준

| 상황 | 구성 |
|------|------|
| 단일 파일, 명확한 범위 | 직접 수행 |
| 독립적 병렬 작업 (Phase 2·3·5) | Subagent (`Agent` tool) |
| 다관점 토론·합의 필요 (Phase 1·4) | Agent Teams (VETO 프로토콜) |

**동시 Subagent 한도: ≤3개.** 초과 시 큐에 등록, 완료 후 순차 실행.

## 모델 티어링

| 역할 | 모델 | 적용 |
|------|------|------|
| Lead (의사결정·아키텍처) | **Opus** | 복잡한 판단, 설계 |
| Worker/Subagent (실행) | **Sonnet** | 코드 생성, 문서 작성 |
| Hook Classifier (경량 판단) | **Haiku** | 명령 분류, 패턴 매칭 |

## Phase 3 Worktree 격리

Phase 3 BUILD에서 병렬 Subagent를 사용할 때 `isolation: "worktree"` 파라미터를 사용한다.

```python
Agent(
    subagent_type="general-purpose",
    isolation="worktree",    # 격리된 git worktree 생성
    prompt="..."
)
```

- 각 Subagent는 독립된 worktree에서 작업하여 충돌을 방지한다
- Lead는 모든 Subagent 완료 후 결과를 통합하고 worktree를 정리한다
- 비정상 종료 후 잔존 worktree: `git worktree list` 확인 → cherry-pick 후 `git worktree remove`

## Agent Teams 사용 조건

사용 전 확인:
- `settings.json`에 `"CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1"` 설정 여부
- 팀원은 Lead 대화 히스토리를 상속받지 않으므로 프롬프트에 핵심 컨텍스트 포함 필수
- 팀원 수: 3~4명, 모델: Sonnet 권장

**알려진 제약:** 세션 재개 불가, Nested Teams 불가, 세션당 1 Team.
다음 중 하나 해당 시 Subagent 기반으로 복귀:
- Agent Teams 기능 불안정 (스폰 오류 반복)
- 단일 Phase 내 Agent Teams Round가 5를 초과하는 상황이 반복됨

## Generator–Validator 분리 원칙

Phase 3(BUILD) 산출물을 Phase 4(VERIFY)에서 검증할 때,
Phase 3 Generator와 동일한 Subagent 인스턴스를 Phase 4 Validator로 재사용하지 않는다.

---

## VETO 운용

### Phase A: Agent Teams 내부 토론
- Lead는 안건 broadcast 후 논의에서 제외 (앵커링 바이어스 방지)
- 각 Agent는 Lead에게 직접 투표 제출 (`VOTE: Approve` / `VETO + evidence + proposal`)
- **합의 기준**: Veto 0건 (전원 Approve)
- **Round 한도**: 5 Round → 미해소 시 SAGA 문서 원칙 기반 결정, `tasks.md`에 해당 안건 앞 `[문서 기반 결정]` 태그 기록

### Phase B: Lead 검토
- Lead가 합의안을 Constitution·requirements.md 기준으로 독립 분석
- Approve → 확정 / Veto → 사유 + 개선 방향과 함께 Phase A 재시작
- **Round 한도**: 3 Round → 미해소 시 Human 에스컬레이션

### Kill-switch 예외 (투표 없이 즉시 발동)

| 조건 | 조치 |
|------|------|
| 보안 취약점 (CVE High/Critical) | 즉시 VETO + **작업 중단** |
| 법적 컴플라이언스 위반 | 즉시 VETO + **Human 에스컬레이션** |
