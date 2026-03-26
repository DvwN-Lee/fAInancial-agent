# Demo Assets

> 이 폴더에는 [README 데모 섹션](../../README.md#데모)에 사용되는 스크린샷과 캡처 가이드가 포함되어 있습니다.

---

## 파일 구조

```
docs/demo/
├── README.md                # 이 파일
├── ui-welcome.png           # Step 1 — Streamlit 시작 화면
├── ui-chat.png              # Step 2 — 채팅 응답 + Tool 뱃지
├── langfuse-dashboard.png   # Step 3 — LangFuse Home 대시보드
├── langfuse-traces.png      # Step 4 — Tracing 탭 목록
└── langfuse-trace-detail.png # Step 5 — 개별 trace 노드 흐름
```

---

## 캡처 가이드

### 사전 조건

- Docker Compose 전체 스택 기동 상태 (`docker compose -f docker-compose.yml -f docker-compose.langfuse.yml up`)
- 브라우저: Chrome/Chromium 권장
- 창 너비: 1440px 이상 (LangFuse trace 이름·latency 가독성 확보)

### 캡처 절차

1. `docker compose up`으로 전체 스택 실행
2. http://localhost:8501 접속 — **ui-welcome.png** 캡처
3. 예시 질문 입력: "삼성전자(005930) 종합 분석 리포트" — 응답 완료 후 **ui-chat.png** 캡처
4. http://localhost:3000 접속 (LangFuse)
   - Home 대시보드 — **langfuse-dashboard.png** 캡처
   - Tracing 탭 목록 — **langfuse-traces.png** 캡처
   - 개별 trace 상세 — **langfuse-trace-detail.png** 캡처

### 이미지 규격

| 항목 | 기준 |
|------|------|
| 포맷 | PNG |
| 최대 크기 | 파일당 5MB 이하 |
| 해상도 | 1440px 너비 이상 (trace 이름·latency 수치 가독) |
| DPI | 1x 권장 (2x Retina는 파일 크기 과대) |

---

## 갱신 체크리스트

UI 또는 LangFuse 버전에 주요 변경이 있을 때 아래 체크리스트를 따릅니다:

- [ ] 최신 코드로 `docker compose up` 실행
- [ ] 브라우저 캐시 비우기
- [ ] 위 캡처 절차 1~4 재실행
- [ ] 이미지 최적화 (5MB 이하 확인)
- [ ] [README.md 데모 섹션](../../README.md#데모) 이미지 경로 확인
- [ ] PR에 변경된 이미지 포함

---

[메인 README로 돌아가기](../../README.md#데모)
