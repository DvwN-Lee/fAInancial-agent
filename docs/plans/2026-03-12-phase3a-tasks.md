# Phase 3-A 태스크 정의

> **status**: current
> **작성일**: 2026-03-12
> **설계 문서**: [phase3a-productionization.md](./2026-03-12-phase3a-productionization.md)

---

## 의존성 그래프

```
T1 (CI)
 └── T2 (Streamlit UI)
      └── T4 (Demo 산출물)
           ↑
T3 (LangFuse) ──┘
```

- T1은 의존성 없음 — 첫 번째 실행
- T2는 T1 완료 후 (CI가 UI 코드도 커버)
- T3는 T2와 병렬 가능하나 T2 완료 후 순차 실행 (Docker Compose 통합 충돌 방지)
- T4는 T2 + T3 완료 후 (UI + LangFuse 화면이 필요)

---

## T1 — GitHub Actions CI

**목표**: push/PR 시 pytest + lint 자동 실행

**파일**:
- `.github/workflows/ci.yml` (신규)

**완료 기준**:
- `feat/phase3a-productionization` 브랜치 push 시 CI 트리거 확인
- `uv run pytest tests/ -v` 91개 전체 통과
- `uv run ruff check .` lint 통과
- GitHub Actions 탭에서 초록 체크 확인

**TDAID 전략**:
- [Red]: 빈 ci.yml push → CI 실패 or 미트리거
- [Green]: 올바른 ci.yml 작성 → CI 통과
- [Validate]: main PR 시 CI 자동 트리거 확인

---

## T2 — Streamlit UI

**목표**: `/chat` API를 사용하는 웹 채팅 인터페이스

**파일**:
- `ui/app.py` (신규)
- `ui/Dockerfile` (신규)
- `docker-compose.yml` 수정 (ui 서비스 추가)

**완료 기준**:
- `docker compose up` 후 `http://localhost:8501` 접속 가능
- 메시지 입력 → FastAPI `/chat` 호출 → 응답 표시
- 동일 세션에서 대화 지속 (session_id 유지)
- 페이지 새로고침 시 새 세션 시작

**TDAID 전략**:
- [Red]: `ui/app.py` import → ModuleNotFoundError (streamlit 미설치)
- [Green]: `ui/requirements.txt` + `Dockerfile` + `app.py` 작성
- [Validate]: Docker Compose로 실제 UI 동작 확인 (Steady State)

---

## T3 — LangFuse Observability

**목표**: LangGraph 실행 트레이싱 (self-hosted LangFuse)

**파일**:
- `docker-compose.langfuse.yml` (신규)
- `agent/graph.py` 수정 (`_get_langfuse_handler` + `run_graph` config 주입)
- `agent/requirements.txt` 수정 (`langfuse` 추가)

**완료 기준**:
- `docker compose -f docker-compose.yml -f docker-compose.langfuse.yml up` 기동
- `http://localhost:3000` LangFuse 대시보드 접속
- 채팅 1회 후 LangFuse에 trace 1건 생성 확인
- `LANGFUSE_*` 환경변수 미설정 시 기존 동작 유지 (graceful degradation)
- 기존 테스트 91개 전체 통과 (LangFuse mock 처리)

**TDAID 전략**:
- [Red]: `graph.py`에 `_get_langfuse_handler` 추가 → 테스트 실패
- [Green]: 구현 + `test_graph.py`에 LangFuse 관련 테스트 추가
- [Validate]: Docker + 실제 LangFuse trace 확인

---

## T4 — Demo 산출물

**목표**: README에 UI 스크린샷 + CI 뱃지 추가

**파일**:
- `docs/demo/` (신규, 스크린샷 + GIF)
- `README.md` 수정

**완료 기준**:
- README에 GitHub Actions CI 뱃지 포함
- README에 Streamlit UI 스크린샷 1장 이상 포함
- Quick Start에 `:8501` UI URL 안내 추가
- LangFuse 선택적 실행 방법 포함

**TDAID 전략**:
- 코드 변경 없음 — 운영 작업 (스크린샷 캡처 + README 편집)

---

## 태스크 요약

| ID | 내용 | 의존성 | 파일 수 |
|----|------|--------|--------|
| T1 | GitHub Actions CI | 없음 | 1 |
| T2 | Streamlit UI + Docker | T1 | 3 |
| T3 | LangFuse Observability | T2 | 3 |
| T4 | Demo 산출물 + README | T2, T3 | 2 |

합계: 9개 파일
