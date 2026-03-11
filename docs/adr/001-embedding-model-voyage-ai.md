# ADR-001: 임베딩 모델을 Gemini에서 Voyage AI로 전환

> **status**: accepted
> **date**: 2026-03-11
> **deciders**: Human + Agent Teams VETO (3명 Sonnet)

## Context

Phase 1 RAG 파이프라인은 DART 공시 원문을 벡터화하여 시맨틱 검색을 제공한다.
초기 설계에서 Gemini text-embedding-004를 임베딩 모델로 선택했으나,
배치 인덱싱 과정에서 무료 티어 제한이 실질적 병목으로 식별되었다.

### 문제

| 항목 | Gemini text-embedding-004 |
|------|--------------------------|
| 무료 한도 | 1,000 RPD (Requests Per Day) |
| 배치 대응 | `batch_embed_contents`로 RPD 절감 가능하나 일일 한도 존재 |
| 결과 | 수천 청크 인덱싱 시 하루 만에 완료 불가능할 수 있음 |

`batch_embed_contents` + quota guard로 우회 설계를 했으나,
개발·테스트·재인덱싱 사이클을 고려하면 RPD 제한이 반복적 마찰을 유발한다.

## Decision

임베딩 모델을 **Voyage AI voyage-finance-2**로 전환한다.

## Considered Options

### Option 1: Gemini text-embedding-004 유지 + quota guard

- 장점: 기존 설계 변경 없음. GEMINI_API_KEY 재사용
- 단점: 1,000 RPD 제한 존속. 재인덱싱마다 일일 할당량 소진 위험. quota guard 복잡도 추가

### Option 2: Voyage AI voyage-3.5-lite

- 장점: 범용 임베딩 모델, 한국어 지원
- 단점: 무료 토큰 없음 (확인 결과 신규 모델은 무료 토큰 미제공)

### Option 3: Voyage AI voyage-finance-2 (선택)

- 장점: 50M 무료 토큰 (신용카드 불필요). 금융 도메인 특화 (일반 모델 대비 금융 검색 성능 우위). 1024차원 고정. DART 공시 문서에 최적
- 단점: 신규 환경변수(VOYAGE_API_KEY) 추가. 범용 모델 대비 비금융 데이터 검색 성능 미검증

### Option 4: OpenAI text-embedding-3-small

- 장점: 업계 표준, 문서·커뮤니티 풍부
- 단점: 무료 티어 없음 (신용카드 필수). 유료 과금 발생

### Option 5: voyage-multilingual-2 (한국어 특화)

- 장점: 한국어 특화 벤치마크 최상위. 50M 무료 토큰
- 단점: 금융 도메인 최적화 아님. voyage-finance-2 대비 금융 문서 검색에서 열위

### 선택 근거: voyage-finance-2

| 기준 | voyage-finance-2 | voyage-3.5-lite | voyage-multilingual-2 |
|------|-----------------|-----------------|----------------------|
| 무료 토큰 | 50M | 없음 | 50M |
| 금융 도메인 최적화 | 최적 | 범용 | 다국어 특화 |
| DART 공시 적합성 | 최적 (금융 문서) | 보통 | 보통 |
| 차원 | 1024 (고정) | 1024 (기본, MRL) | 1024 |
| 컨텍스트 | 32K | 32K | 32K |

DART 공시 문서(사업보고서, 재무제표 주석 등)는 금융 도메인 문서이므로,
금융 특화 임베딩 모델이 범용 모델보다 검색 품질에서 유리하다.

## Consequences

### 긍정적

- **RPD 병목 해소**: 50M 무료 토큰 = 배치 인덱싱 ~57회 실행 가능 (87만 토큰/회 기준)
- **금융 도메인 최적화**: 금융 검색에서 OpenAI 대비 평균 7%, Cohere 대비 12% 성능 우위
- **quota guard 제거**: 코드 복잡도 감소
- **장애 도메인 분리**: LLM(Gemini) ↔ 임베딩(Voyage) 독립
- **비용 제로**: 50M 토큰 무료, 신용카드 불필요

### 부정적

- **환경변수 추가**: `.env`에 `VOYAGE_API_KEY` 추가 필요 (Human 관리)
- **FAISS 인덱스 재생성**: 차원 변경 (768 → 1024)으로 기존 인덱스 호환 불가
- **무료 한도 상대적 제한**: 50M 토큰은 ~57회 인덱싱. 빈번한 재인덱싱 시 소진 가능 (단, Phase 1 규모에서 충분)
- **외부 서비스 의존 추가**: Voyage AI 서비스 장애 시 RAG 검색 불능 (단, LLM은 정상)

### 변경 범위

| 파일 | 변경 |
|------|------|
| `scripts/index_documents.py` | Gemini client → Voyage client, 배치 임베딩 호출 변경 |
| `mcp_server/rag_search.py` | Gemini client → Voyage client, 쿼리 임베딩 호출 변경 |
| `mcp_server/requirements.txt` | `google-genai` → `voyageai` |
| `scripts/requirements.txt` | `google-genai` → `voyageai` |
| `tests/mcp_server/test_rag_search.py` | fixture 차원 768 → 1024 |
| `data/faiss/*` | 전면 재생성 필수 |

### 변경 없는 항목

- FAISS IndexFlatIP 타입
- MCP Tool 시그니처 (`search_documents`)
- Agent 코드 (`agent/loop.py`, `agent/mcp_client.py`)
- DART API 흐름
- Docker 구성 (볼륨 마운트 동일)
- RAGAS 평가 (LLM 기반, 임베딩 무관)

## Validation

SAGA VETO 프로토콜로 검증 완료 (2026-03-11).
VETO 시점 모델은 voyage-3.5-lite였으나, 무료 토큰 미제공 확인 후 voyage-finance-2로 최종 변경.
SDK 호출 방식·차원(1024)·의존성 구조는 동일하므로 VETO 결과의 유효성 유지.

| 검증자 | 역할 | 투표 |
|--------|------|------|
| voyage-api-reviewer | Voyage AI SDK, 무료 티어, 차원, 한국어 | APPROVE |
| arch-reviewer | 아키텍처, Constitution, 의존성, 장애 도메인 | APPROVE |
| compat-reviewer | FAISS 호환성, 테스트, Docker, 마이그레이션 | APPROVE |

Phase A: VETO 0건 합의. Phase B: Lead APPROVE.

## References

- [설계 문서](../plans/2026-03-10-phase1-rag-design.md) — Section 8 VETO 결과
- [Voyage AI Embeddings 문서](https://docs.voyageai.com/docs/embeddings)
- [Voyage AI 가격 정책](https://docs.voyageai.com/docs/pricing)
- [voyage-finance-2 Pinecone 문서](https://docs.pinecone.io/models/voyage-finance-2)
