# ADR-010: DART/KRX를 금융 데이터 소스로 선택

## Status
Accepted (2026-03-10)

## Context
- 한국 금융 데이터 분석 Agent가 조회할 데이터 소스 결정 필요
- 재무제표(DART 전자공시) + 주가(KRX) 두 축의 데이터가 핵심
- 무료 공개 API 기반 운용, 외부 유료 벤더 의존 없음

## Decision
DART OpenAPI(전자공시) + FinanceDataReader(KRX 주가)를 데이터 소스로 선택.

고려한 대안:
- **KRX 공식 OpenAPI (data.krx.co.kr)**: KRX가 직접 제공하는 API이나, 인증 절차가 복잡하고 데이터 형식이 비표준적
- **유료 벤더 (Bloomberg, Refinitiv)**: 기관급 데이터 품질이나, 비용이 포트폴리오 프로젝트에 부적합
- **웹 스크래핑**: 비용 무료이나, 사이트 구조 변경 시 즉시 파손. 법적 리스크

선택 근거: DART OpenAPI는 금융감독원이 운영하는 공식 전자공시 시스템으로, API 키 발급이 간단하고 일일 10,000 호출 한도 내에서 무료 운용이 가능하다. document.xml API는 ZIP 형식으로 반환하며, 내부 HTML 파일을 파싱하여 RAG 인덱싱에 활용한다. FinanceDataReader는 KRX, Yahoo Finance, FRED 등 다중 소스를 Python 라이브러리 하나로 추상화하여 주가 데이터 수집이 간편하다.

## Consequences
- 긍정: 무료 공개 API, 공식 데이터 소스 신뢰성, FinanceDataReader의 다중 소스 추상화
- 부정: DART 일일 10,000 호출 제한, document.xml ZIP 파싱 복잡성, FinanceDataReader 라이브러리 유지보수 의존
- 데이터 소스 접근은 MCP 서버(mcp_server/)에 캡슐화하여 Agent가 직접 호출하지 않음 (ADR-003 참조)
