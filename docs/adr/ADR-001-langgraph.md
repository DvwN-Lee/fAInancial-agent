# ADR-001: LangGraph를 Agent 프레임워크로 선택

## Status
Accepted (2026-03-12)

## Context
- Phase 0에서 while 루프 + tool_use 파싱으로 Agent를 직접 구현했으나, 상태 관리와 반복 제어의 복잡도가 증가
- Phase 2-B부터 프레임워크 도입이 필요했으며, 프로젝트 원칙에 따라 단계적 도입 방침
- 요구사항: 노드/엣지 기반 제어 흐름, 대화 상태 자동 관리(checkpointer), langchain 생태계 호환

## Decision
LangGraph의 StateGraph + InMemorySaver를 선택.

고려한 대안:
- **CrewAI**: 멀티 에이전트 오케스트레이션에 특화되나, 단일 Agent에는 과도한 추상화. 프로젝트 코드 규칙에서 import 금지
- **AutoGen**: 대화형 멀티 에이전트 프레임워크이나, 단일 Agent + Tool 호출 패턴에는 불필요한 복잡성
- **while 루프 직접 구현 (Phase 0)**: loop.py로 검증 완료. 상태 저장/복원을 수동 관리해야 하며 확장성 한계

선택 근거: StateGraph의 노드(agent_node, tool_node) + 엣지(should_continue) 구조가 Phase 0의 while 루프 패턴과 1:1 대응되어 마이그레이션이 자연스럽고, InMemorySaver가 SessionStore(dict 기반)를 대체하여 세션 자동 관리를 제공한다. langchain-google-genai와의 통합이 원활하다.

## Consequences
- 긍정: 노드 단위 테스트 가능, checkpointer로 세션 관리 자동화, GraphRecursionError로 무한 루프 방지 내장
- 부정: LangGraph 버전 의존성 추가, 프레임워크 학습 비용
- Phase 0 원본(loop.py, session.py)은 레포에 보존하여 행동 동등성 비교 기준으로 활용
