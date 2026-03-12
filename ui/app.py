import logging
import os

import requests
import streamlit as st

logger = logging.getLogger(__name__)

AGENT_API_URL = os.getenv("AGENT_API_URL", "http://localhost:8000")

TOOL_LABELS = {
    "get_financials": "📊 재무제표 조회",
    "search_disclosures": "📋 공시 검색",
    "get_stock_price": "📈 주가 조회",
    "search_documents": "🔍 문서 검색",
}

EXAMPLE_QUESTIONS = [
    "삼성전자 2024년 매출과 영업이익 알려줘",
    "SK하이닉스 최근 주가 동향은?",
    "네이버 최근 공시 내용 요약해줘",
    "LG에너지솔루션 종합 분석 리포트 작성해줘",
]

# --- Page Config ---
st.set_page_config(page_title="fAInancial Agent", page_icon="💹", layout="centered")

# --- Session State ---
if "messages" not in st.session_state:
    st.session_state.messages: list[dict] = []
if "session_id" not in st.session_state:
    st.session_state.session_id: str | None = None

# --- Sidebar ---
with st.sidebar:
    st.title("fAInancial Agent")
    st.caption("AI 기반 금융 데이터 분석")
    st.divider()
    st.subheader("사용 가능한 기능")
    st.markdown(
        "- 📊 재무제표 조회\n"
        "- 📈 주가 조회\n"
        "- 📋 공시 검색\n"
        "- 🔍 문서 검색"
    )
    st.divider()
    if st.button("🔄 새 대화 시작", use_container_width=True):
        st.session_state.messages = []
        st.session_state.session_id = None
        st.rerun()


# --- Helper: API 호출 ---
def call_agent(prompt: str) -> tuple[str, list[str]]:
    """Agent API를 호출하고 (응답 텍스트, tools_used)를 반환한다."""
    try:
        payload = {
            "message": prompt,
            "session_id": st.session_state.session_id,
        }
        resp = requests.post(
            f"{AGENT_API_URL}/chat",
            json=payload,
            timeout=120,
        )
        resp.raise_for_status()
        try:
            data = resp.json()
        except requests.exceptions.JSONDecodeError:
            logger.exception("응답 JSON 파싱 실패: %s", resp.text[:200])
            data = {}
        answer = data.get("response", "(응답 없음)")
        st.session_state.session_id = data.get("session_id")
        tools_used = data.get("tools_used", [])
        return answer, tools_used
    except requests.exceptions.ConnectionError:
        return f"Agent API에 연결할 수 없습니다. ({AGENT_API_URL})", []
    except requests.exceptions.Timeout:
        return "응답 시간이 초과되었습니다. 잠시 후 다시 시도해 주세요.", []
    except requests.exceptions.HTTPError as e:
        return f"API 오류: {e.response.status_code} - {e.response.text}", []
    except Exception as e:
        logger.exception("예상치 못한 오류 발생")
        return f"오류가 발생했습니다: {e}", []


# --- Helper: Tool 뱃지 렌더링 ---
def render_tool_badges(tools: list[str]):
    """사용된 tool 이름을 TOOL_LABELS로 매핑하여 caption으로 표시."""
    if not tools:
        return
    labels = [TOOL_LABELS.get(t, t) for t in tools]
    st.caption(" · ".join(labels))


# --- Helper: 메시지 전송 처리 ---
def send_message(prompt: str):
    """사용자 메시지를 전송하고 응답을 표시한다."""
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("분석 중..."):
            answer, tools_used = call_agent(prompt)
        render_tool_badges(tools_used)
        st.markdown(answer)

    st.session_state.messages.append({
        "role": "assistant",
        "content": answer,
        "tools_used": tools_used,
    })


# --- 환영 화면 (대화 없을 때만) ---
if not st.session_state.messages:
    st.title("💹 fAInancial Agent")
    st.markdown("**이런 질문을 해보세요:**")
    cols = st.columns(2)
    for i, q in enumerate(EXAMPLE_QUESTIONS):
        if cols[i % 2].button(q, key=f"example_{i}", use_container_width=True):
            send_message(q)
            st.rerun()
else:
    # --- 대화 히스토리 렌더링 ---
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            if message["role"] == "assistant":
                render_tool_badges(message.get("tools_used", []))
            st.markdown(message["content"])

# --- Chat Input ---
if prompt := st.chat_input("질문을 입력하세요 (예: 삼성전자 2024년 매출 알려줘)"):
    send_message(prompt)
    st.rerun()
