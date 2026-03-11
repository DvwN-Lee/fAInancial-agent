# Phase 1 RAG Design — DART 공시 문서 벡터 검색

> **status**: current
> **date**: 2026-03-10
> **track**: Feature (Phase 1-1 FAISS → Phase 1-2 pgvector)
> **SAGA phase**: Phase 1 SPECIFICATION

---

## 1. 목표

DART 공시 원문(사업보고서 등)을 벡터화하여, 자연어 질문에 대해
관련 공시 내용을 검색·인용할 수 있는 RAG 파이프라인을 구축한다.

### Steady State 기준

| 항목 | 기준 |
|------|------|
| RAG 동작 | "삼성전자 2024년 사업 위험 요인" → 공시 원문 기반 답변 생성 |
| 품질 | RAGAS faithfulness ≥ 0.7, answer_relevancy ≥ 0.7, context_precision ≥ 0.6 |
| Docker | `docker compose up` 한 줄로 전체 기동 유지 |

---

## 2. 아키텍처

### 오프라인 (배치 인덱싱)

```
scripts/index_documents.py (CLI)
  │
  ├─ DART API /list.json → rcept_no 획득
  ├─ /document.xml?rcept_no=... → ZIP 다운로드 (정식 API)
  ├─ ZIP 해제 → *.html 파일 전체 순회 → BeautifulSoup 텍스트 추출
  │   ※ document.xml은 목차/매니페스트. 본문 텍스트는 ZIP 내 *.html 파일에 존재
  ├─ 청크 분할 (chunk_size ~500자, overlap ~100자)
  ├─ Voyage AI voyage-finance-2 배치 임베딩
  │   ※ 무료 50M 토큰 (신용카드 불필요). 금융 도메인 특화. 배치 인덱싱 ~87만 토큰 = 여유
  ├─ FAISS 인덱스 + 메타데이터 저장 (원자적 쓰기: .tmp → os.rename)
  │     ├─ data/faiss/index.faiss
  │     └─ data/faiss/metadata.json
  └─ 환경변수: VOYAGE_API_KEY
```

### 온라인 (런타임 검색)

```
Agent Loop (agent/loop.py) — 변경 없음
  │ function_call: search_documents(query, corp_name, year)
  ▼
MCP Server (mcp_server/main.py)
  ├─ get_financials()       ← 기존
  ├─ search_disclosures()   ← 기존
  ├─ get_stock_price()      ← 기존
  └─ search_documents()     ← 신규 RAG Tool
       │
       ▼
  mcp_server/rag_search.py
  ├─ _get_index() — lazy load 1회, 메모리 유지 (파일 미존재 시 명시적 에러)
  ├─ FAISS 전체 검색(k×3) → metadata post-filter(corp_name/year) → 상위 k 반환
  │   ※ Phase 1-1 규모(수천 청크)에서 post-filter 충분. IDSelectorArray 불필요
  ├─ query → Voyage AI embedding
  └─ 상위 k개 청크 텍스트 + 출처 반환
```

### MCP Tool 시그니처

```python
@mcp.tool()
def search_documents(
    query: str,
    corp_name: str | None = None,
    year: str | None = None,
) -> str:
    """공시 문서에서 관련 내용을 검색합니다.

    Args:
        query: 검색 질문 (예: 사업 위험 요인, 주요 투자 계획)
        corp_name: 기업명 필터 (예: 삼성전자). 없으면 전체 검색
        year: 사업연도 필터 (예: 2024). 없으면 전체 연도 검색
    """
```

---

## 3. 파일 구조

### 신규/변경 파일

```
fAInancial-agent/
├── scripts/
│   ├── index_documents.py     # 신규 — 오프라인 배치 인덱서
│   ├── evaluate_rag.py        # 신규 — RAGAS 평가 스크립트
│   └── requirements.txt       # 신규 — 스크립트 전용 의존성
├── mcp_server/
│   ├── main.py                # 변경 — search_documents Tool 등록
│   ├── rag_search.py          # 신규 — FAISS 로드 + 검색 로직
│   └── requirements.txt       # 변경 — faiss-cpu, voyageai 추가
├── data/
│   ├── documents/             # 신규 — 다운로드된 공시 ZIP
│   ├── faiss/                 # 신규 — index.faiss + metadata.json
│   ├── eval/                  # 신규 — 평가 데이터셋 + 결과
│   └── .gitkeep
├── tests/
│   ├── test_html_parser.py     # 신규 — HTML→텍스트 추출 단위 테스트
│   ├── test_chunker.py        # 신규 — 청킹 로직 단위 테스트
│   ├── test_rag_search.py     # 신규 — search_documents 통합 테스트
│   └── test_rag.py            # 신규 — E2E 흐름 테스트
└── docker-compose.yml         # 변경 — data/ 볼륨 마운트 추가
```

---

## 4. 의존성 배치

### mcp_server/requirements.txt (런타임)

| 라이브러리 | 용도 |
|-----------|------|
| `faiss-cpu` | rag_search.py 런타임 검색 |
| `voyageai` | 쿼리 임베딩 (Voyage AI voyage-finance-2) |

### scripts/requirements.txt (오프라인 전용, 신규)

| 라이브러리 | 용도 |
|-----------|------|
| `beautifulsoup4` | ZIP 내 XML/HTML 텍스트 추출 |
| `lxml` | BeautifulSoup XML 파서 |
| `faiss-cpu` | 인덱스 생성 |
| `voyageai` | 문서 임베딩 (Voyage AI voyage-finance-2) |
| `ragas` | RAG 품질 평가 |

프로덕션 컨테이너(mcp-server, agent)에 오프라인 전용 의존성 미포함.

---

## 5. RAGAS 품질 측정

### 평가 흐름

```
scripts/evaluate_rag.py

입력: data/eval/qa_set.json (수동 작성 5~10개)
  ├─ 질문 → search_documents() → contexts
  ├─ 질문 + contexts → Gemini → answer
  ├─ RAGAS 메트릭 계산
  └─ 출력: data/eval/results_YYYYMMDD.json
```

### 평가 데이터셋 포맷

```json
[
  {
    "question": "삼성전자 2024년 사업보고서에서 주요 사업 위험은?",
    "ground_truth": "반도체 수급 변동, 환율 리스크, ...",
    "corp_name": "삼성전자",
    "year": "2024"
  }
]
```

`ground_truth` 필드 필수 — context_precision 산출 전제조건.
복수 기업(삼성전자/LG화학 등) × 복수 질문 유형(위험요인/투자계획 등)으로 구성.

### 목표 수치

| 메트릭 | 목표 | 미달 시 조치 |
|--------|------|------------|
| faithfulness | ≥ 0.7 | 청킹 크기/오버랩 조정 |
| answer_relevancy | ≥ 0.7 | 프롬프트 튜닝 |
| context_precision | ≥ 0.6 | 청킹 전략 개선 |

Phase 1에서는 리랭킹, 하이브리드 검색 등 고급 기법 미도입.

> **측정 한계**: 5~10개 샘플은 통계적 유의성보다 **방향성 확인 초기 벤치마크** 목적.
> Phase 2에서 30+ 샘플로 확대하여 통계적 신뢰도를 확보한다.

---

## 6. Phase 1-1 → 1-2 전환 계획

| 항목 | Phase 1-1 (FAISS) | Phase 1-2 (pgvector) |
|------|-------------------|---------------------|
| Vector DB | FAISS 로컬 파일 | PostgreSQL + pgvector |
| 메타데이터 필터 | metadata.json 순회 | SQL WHERE 절 |
| Docker 서비스 | 2개 (기존) | 3개 (+postgres) |
| 교체 범위 | — | rag_search.py 내부만 |
| Tool 시그니처 | 동일 | 동일 |
| Agent 코드 변경 | — | 없음 |

### 전환 기준

Phase 1-1 완료 조건 충족 + RAGAS 목표 달성 후 전환.
인덱서 공통 로직(DART API → XML 파싱 → 청킹 → 임베딩)은 재사용,
출력 대상만 파일 → PostgreSQL INSERT로 변경.

---

## 7. 기술적 결정 근거

| 결정 | 선택 | 근거 |
|------|------|------|
| 문서 소스 | DART 공시 원문 | 경영진 분석, 사업 위험 등 비정형 정보 포함 |
| 텍스트 추출 | ZIP→HTML (BeautifulSoup) | DART document.xml API가 ZIP 반환. ZIP 내 *.html이 본문. PDF 스크래핑 불필요 |
| 임베딩 | Voyage AI voyage-finance-2 | 무료 50M 토큰 (신용카드 불필요). 금융 도메인 특화. Gemini 1,000 RPD 제한 회피 |
| Vector DB 1단계 | FAISS 로컬 | 구현 최단순. Docker 서비스 추가 없음 |
| Vector DB 2단계 | pgvector | SQL 기반 메타데이터 필터링. 프로덕션 전환 |
| RAG 연결 | MCP Tool 추가 | CLAUDE.md 'MCP Tool = 수단' 원칙. Agent 코드 변경 제로 |
| 인덱싱 시점 | 오프라인 배치 | 응답 지연 방지. CLI 스크립트로 분리 |
| 품질 측정 | RAGAS | faithfulness/relevancy 수치화. 포트폴리오 차별화 |

---

## 8. VETO 검증 결과

### Round 1 (Agent Teams, 2026-03-10) — Gemini Embedding 기반 설계

Agent Teams 3명(Sonnet) VETO 프로토콜 실행 완료.

| 검증자 | 역할 | 투표 |
|--------|------|------|
| dart-api-reviewer | DART API + Gemini rate limit | VETO → 수용·반영 |
| arch-reviewer | 아키텍처 리스크 + Constitution | APPROVE (권고 2건) |
| ragas-reviewer | RAGAS 호환성 + 평가 전략 | APPROVE (권고 2건) |

반영된 수정 사항:

| VETO/권고 | 내용 | 반영 |
|-----------|------|------|
| VETO | ZIP 내 `*.html`이 실제 본문 (`document.xml`은 목차) | 인덱서 흐름 수정 |
| VETO | Gemini 무료 1,000 RPD → `batch_embed_contents` 필요 | 배치 임베딩 + quota guard 추가 |
| 권고 | FAISS post-filter로 충분 (IDSelectorArray 불필요) | 검색 흐름 명시 |
| 권고 | 원자적 쓰기 (`.tmp` → `os.rename`) | 인덱서 흐름에 반영 |
| 권고 | `ground_truth` 필드 필수 | 평가 데이터셋 포맷 명시 |
| 권고 | 5~10개 샘플 = 방향성 확인 초기 벤치마크 | 측정 한계 문서화 |

### Round 2 (2026-03-11) — 임베딩 모델 전환: Gemini → Voyage AI

**변경 사유**: Gemini text-embedding-004 무료 티어 1,000 RPD 제한 → 배치 인덱싱 시 실질적 병목.
Voyage AI voyage-finance-2는 50M 무료 토큰(신용카드 불필요), 금융 도메인 특화.

**변경 범위**:

| 항목 | Before (Gemini) | After (Voyage AI) |
|------|----------------|-------------------|
| 임베딩 모델 | text-embedding-004 | voyage-finance-2 |
| 무료 한도 | 1,000 RPD | 50M 토큰 |
| SDK | `google-genai` | `voyageai` |
| 환경변수 | `GEMINI_API_KEY` (공유) | `VOYAGE_API_KEY` (신규) |
| 배치 전략 | `batch_embed_contents` + quota guard | `vo.embed(texts)` 네이티브 배치 |

**변경 없는 항목**: FAISS IndexFlatIP 타입, MCP Tool 시그니처, Agent 코드, DART API 흐름, RAGAS 평가, Docker 구성

**변경 필요 항목** (VETO 리뷰에서 식별):
- FAISS 인덱스 차원: 768 → 1024 (voyage-finance-2 기본값). 기존 인덱스 재생성 필수
- `index_documents.py` + `rag_search.py` 양파일 EMBEDDING_MODEL 동시 수정
- 테스트 fixture 차원 상수: 768 → 1024
- 재시도/백오프 로직: Voyage AI RPM 제한 대응용 보존
- `.env.example`에 `VOYAGE_API_KEY` 추가

### VETO 결과

| 검증자 | 역할 | 투표 |
|--------|------|------|
| voyage-api-reviewer | Voyage AI SDK + 무료 티어 + 차원 | APPROVE (권고 1건) |
| arch-reviewer | 아키텍처 + Constitution + 의존성 | APPROVE (부대조건 3건) |
| compat-reviewer | FAISS 호환성 + 테스트 + Docker | APPROVE (체크리스트 6건) |

**Phase A**: VETO 0건 합의 달성. **Phase B**: Lead APPROVE.
