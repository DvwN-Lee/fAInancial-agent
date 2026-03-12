import logging
import os

import requests
import streamlit as st

logger = logging.getLogger(__name__)

AGENT_API_URL = os.getenv("AGENT_API_URL", "http://localhost:8000")

st.set_page_config(page_title="fAInancial Agent", page_icon="💹", layout="centered")

st.title("fAInancial Agent")
st.caption("재무 데이터 AI 어시스턴트")

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages: list[dict] = []
if "session_id" not in st.session_state:
    st.session_state.session_id: str | None = None

# Display chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Chat input
if prompt := st.chat_input("질문을 입력하세요 (예: 삼성전자 2024년 매출 알려줘)"):
    # Display user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Call Agent API
    with st.chat_message("assistant"):
        with st.spinner("분석 중..."):
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
            except requests.exceptions.ConnectionError:
                answer = f"Agent API에 연결할 수 없습니다. ({AGENT_API_URL})"
            except requests.exceptions.Timeout:
                answer = "응답 시간이 초과되었습니다. 잠시 후 다시 시도해 주세요."
            except requests.exceptions.HTTPError as e:
                answer = f"API 오류: {e.response.status_code} - {e.response.text}"
            except Exception as e:
                logger.exception("예상치 못한 오류 발생")
                answer = f"오류가 발생했습니다: {e}"

        st.markdown(answer)

    st.session_state.messages.append({"role": "assistant", "content": answer})
