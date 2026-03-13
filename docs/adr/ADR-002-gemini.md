# ADR-002: Gemini를 LLM으로 선택

## Status
Accepted (2026-03-10)

## Context
- 한국 금융 데이터 분석 Agent의 LLM으로, 한국어 이해력 + tool_use(function calling) 지원이 필수
- 포트폴리오 프로젝트 특성상 무료 tier 운용이 강력한 제약 조건
- langchain 생태계와의 통합이 필요 (langchain-google-genai)

## Decision
Gemini (gemini-2.5-flash)를 langchain-google-genai를 통해 사용.

고려한 대안:
- **GPT-4o**: tool_use 성능 우수하나, 무료 tier 없음. API 비용이 포트폴리오 프로젝트 제약에 부적합
- **Claude**: 한국어 성능 우수하나, 무료 tier 제한적. tool_use API 형식이 다름
- **로컬 LLM (Ollama)**: 비용 무료이나, tool_use 품질과 한국어 성능이 상용 모델 대비 부족

선택 근거: Gemini의 무료 tier(gemini-2.5-flash: RPM 제한 있으나 개발/데모에 충분), 네이티브 tool_use 지원, 한국어 재무 데이터 요약 품질이 프로젝트 제약 조건에 최적. GEMINI_API_KEY 환경변수로 분리하여 모델 교체 용이.

## Consequences
- 긍정: 무료 운용, langchain-google-genai로 LangGraph 통합 원활, tool_use 네이티브 지원
- 부정: 무료 tier Rate Limit (RPM 5~15, RPD 20~500 모델별 상이), Google AI Studio에서 실측 필요
- MODEL 환경변수로 모델명 분리하여 향후 교체 가능 (gemini-2.5-flash → 다른 모델)
