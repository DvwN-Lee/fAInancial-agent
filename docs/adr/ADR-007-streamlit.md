# ADR-007: Streamlit을 UI 프레임워크로 선택

## Status
Accepted (2026-03-12)

## Context
- Agent API(FastAPI)에 대한 웹 기반 대화형 UI가 필요
- Python 개발자가 별도 프론트엔드 기술 없이 빠르게 구현 가능해야 함
- Bloomberg Terminal 스타일 다크모드 디자인 요구 (팀 디자인 리뷰를 통해 결정)

## Decision
Streamlit을 단일 파일 UI로 선택.

고려한 대안:
- **Gradio**: ML 데모에 최적화되어 있으나, 대화형 UI 커스터마이징이 제한적
- **React + Vite**: 완전한 커스텀 가능하나, 별도 프론트엔드 빌드 파이프라인 필요. Python-only 원칙에 부적합
- **Chainlit**: LLM 대화 UI 전용이나, 생태계가 작고 커스텀 디자인 자유도 제한

선택 근거: Streamlit은 Python 단일 파일(ui/app.py)로 대화형 UI를 구현할 수 있으며, st.session_state로 대화 히스토리와 세션 관리를 간단히 처리한다. st.markdown(unsafe_allow_html=True)로 커스텀 CSS를 주입하여 Bloomberg Terminal 스타일 다크모드를 구현할 수 있다.

## Consequences
- 긍정: Python-only 개발, 빠른 프로토타이핑, 커스텀 CSS로 디자인 자유도 확보
- 부정: 고성능 실시간 UI에는 부적합, Streamlit 런타임 의존성, 대규모 사용자 동시 접속 제한
- Docker 컨테이너(:8501)로 독립 배포, AGENT_API_URL 환경변수로 FastAPI 연결
- 다크모드 구현: config.toml 테마 설정 + 커스텀 CSS 이중 방어 구조로 Streamlit 업데이트에 대응
