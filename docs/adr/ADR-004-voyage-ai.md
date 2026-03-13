# ADR-004: Voyage AI를 임베딩 모델로 선택

## Status
Accepted (2026-03-11)

## Context
- DART 공시 원문(HTML)을 청크 분할 후 벡터 인덱싱하여 RAG 검색에 활용
- 한국어 재무제표 텍스트에 대한 임베딩 품질이 핵심
- 포트폴리오 프로젝트 특성상 무료 tier 운용 필요
- Phase 1-1 RAG 구현 시 팀 리뷰를 통해 확정된 결정

## Decision
Voyage AI의 voyage-finance-2 (기본 1024차원)를 선택.

고려한 대안:
- **OpenAI text-embedding-3**: 범용 고품질이나, 금융 도메인 특화 아님. 유료 과금
- **BGE-M3**: 다국어 지원, 오픈소스이나 금융 특화 학습 없음
- **KoSimCSE**: 한국어 의미 유사도 특화이나, 금융 도메인 학습 데이터 부족
- **KF-DeBERTa / klue/roberta**: 한국어 NLP 모델이나, 임베딩 전용이 아니며 금융 특화 fine-tuning 필요

선택 근거: voyage-finance-2는 금융 문서에 특화된 학습 데이터로 훈련되어 재무제표, 사업보고서 등의 임베딩 품질이 우수하다. 무료 한도 50M 토큰(신용카드 불필요)으로 개발/데모에 충분하다. RAGAS 평가 결과 faithfulness 1.000, context_precision 0.963을 달성하여 실증적으로 검증됨.

현재 인덱스 현황: 삼성전자 3,046 + LG화학 2,731 = 5,777 chunks.

## Consequences
- 긍정: 금융 도메인 특화 임베딩 품질, 무료 50M 토큰, SDK(voyageai) 사용 용이
- 부정: Voyage AI 서비스 의존성 (외부 API 호출), 한국어만을 위한 모델은 아님
- VOYAGE_API_KEY 환경변수로 분리, 향후 다른 임베딩 모델로 교체 시 인덱스 재구축 필요
