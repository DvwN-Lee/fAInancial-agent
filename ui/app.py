import logging
import os

import requests
import streamlit as st

logger = logging.getLogger(__name__)

AGENT_API_URL = os.getenv("AGENT_API_URL", "http://localhost:8000")

TOOL_LABELS = {
    "get_financials": "재무제표",
    "search_disclosures": "공시검색",
    "get_stock_price": "주가조회",
    "search_documents": "문서검색",
}

EXAMPLE_QUESTIONS = [
    "삼성전자 2024년 매출과 영업이익 알려줘",
    "SK하이닉스 최근 주가 동향은?",
    "네이버 최근 공시 내용 요약해줘",
    "LG에너지솔루션 종합 분석 리포트",
]

# ── Page Config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="fAInancial Agent",
    page_icon="💹",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Design System Injection ───────────────────────────────────────────────────
st.markdown("""
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=IBM+Plex+Mono:ital,wght@0,300;0,400;0,500;1,300&family=IBM+Plex+Sans:wght@300;400;500&display=swap" rel="stylesheet">

<style>
/* ── Variables ─────────────────────────────────────────────────────────────── */
:root {
    --bg-deep:     #040709;
    --bg-surface:  #070c14;
    --bg-raised:   #0c1422;
    --bg-hover:    #111d2e;
    --amber:       #E8A020;
    --amber-dim:   rgba(232,160,32,0.12);
    --amber-glow:  rgba(232,160,32,0.04);
    --teal:        #3DD6C0;
    --red:         #F06565;
    --text-bright: #EEF2F8;
    --text-mid:    #8A95AC;
    --text-dim:    #3E4E6A;
    --border:      rgba(255,255,255,0.055);
    --border-a:    rgba(232,160,32,0.25);
    --ff-display:  'Syne', sans-serif;
    --ff-mono:     'IBM Plex Mono', monospace;
    --ff-body:     'IBM Plex Sans', sans-serif;
}

/* ── Global Reset ──────────────────────────────────────────────────────────── */
html, body, [data-testid="stAppViewContainer"],
[data-testid="stApp"], .stApp {
    background: var(--bg-deep) !important;
    color: var(--text-bright) !important;
    font-family: var(--ff-body) !important;
}

/* Hide Streamlit chrome */
#MainMenu, footer, [data-testid="stToolbar"],
[data-testid="stDecoration"], [data-testid="stStatusWidget"] { display:none !important; }

header[data-testid="stHeader"] { background: transparent !important; }

/* ── Scrollbar ─────────────────────────────────────────────────────────────── */
::-webkit-scrollbar { width: 4px; }
::-webkit-scrollbar-track { background: var(--bg-deep); }
::-webkit-scrollbar-thumb { background: var(--border-a); border-radius: 2px; }

/* ── Main content area ─────────────────────────────────────────────────────── */
[data-testid="stMain"],
[data-testid="stMainBlockContainer"],
section.main,
section.main > div,
.main > div { background: var(--bg-deep) !important; }

.block-container {
    padding: 2rem 2.5rem 4rem !important;
    max-width: 860px !important;
}

/* ── Sidebar ───────────────────────────────────────────────────────────────── */
[data-testid="stSidebar"] {
    background: var(--bg-surface) !important;
    border-right: 1px solid var(--border) !important;
}
[data-testid="stSidebar"] > div:first-child { padding: 1.8rem 1.4rem !important; }

/* Sidebar title */
[data-testid="stSidebar"] h1 {
    font-family: var(--ff-display) !important;
    font-weight: 800 !important;
    font-size: 1.15rem !important;
    letter-spacing: 0.04em !important;
    color: var(--amber) !important;
    text-transform: uppercase !important;
    margin-bottom: 0.1rem !important;
}
[data-testid="stSidebar"] .stCaption p {
    font-family: var(--ff-mono) !important;
    font-size: 0.68rem !important;
    color: var(--text-dim) !important;
    letter-spacing: 0.08em !important;
    text-transform: uppercase !important;
}

/* Sidebar divider */
[data-testid="stSidebar"] hr {
    border-color: var(--border) !important;
    margin: 1rem 0 !important;
}

/* Sidebar subheader */
[data-testid="stSidebar"] h3 {
    font-family: var(--ff-mono) !important;
    font-size: 0.65rem !important;
    font-weight: 500 !important;
    letter-spacing: 0.12em !important;
    text-transform: uppercase !important;
    color: var(--text-dim) !important;
    margin-bottom: 0.6rem !important;
}

/* Sidebar markdown list */
[data-testid="stSidebar"] .stMarkdown p,
[data-testid="stSidebar"] .stMarkdown li {
    font-family: var(--ff-mono) !important;
    font-size: 0.8rem !important;
    color: var(--text-mid) !important;
    line-height: 1.9 !important;
}

/* New conversation button */
[data-testid="stSidebar"] .stButton > button {
    background: transparent !important;
    border: 1px solid var(--border-a) !important;
    color: var(--amber) !important;
    font-family: var(--ff-mono) !important;
    font-size: 0.75rem !important;
    font-weight: 400 !important;
    letter-spacing: 0.06em !important;
    padding: 0.55rem 1rem !important;
    border-radius: 2px !important;
    transition: background 0.18s, box-shadow 0.18s !important;
    width: 100% !important;
}
[data-testid="stSidebar"] .stButton > button:hover {
    background: var(--amber-dim) !important;
    box-shadow: 0 0 12px var(--amber-dim) !important;
}

/* ── Main Title ────────────────────────────────────────────────────────────── */
h1 {
    font-family: var(--ff-display) !important;
    font-weight: 800 !important;
    font-size: 2.2rem !important;
    letter-spacing: -0.01em !important;
    color: var(--text-bright) !important;
    line-height: 1.15 !important;
}

/* ── Section headers ───────────────────────────────────────────────────────── */
h2, h3 {
    font-family: var(--ff-display) !important;
    font-weight: 600 !important;
    color: var(--text-mid) !important;
}

/* ── Example question label ────────────────────────────────────────────────── */
.welcome-label {
    font-family: var(--ff-mono);
    font-size: 0.72rem;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: var(--text-dim);
    margin-bottom: 0.8rem;
    display: block;
}

/* ── Example Buttons ───────────────────────────────────────────────────────── */
[data-testid="stHorizontalBlock"] .stButton > button {
    background: var(--bg-raised) !important;
    border: 1px solid var(--border) !important;
    color: var(--text-mid) !important;
    font-family: var(--ff-mono) !important;
    font-size: 0.78rem !important;
    font-weight: 300 !important;
    letter-spacing: 0.01em !important;
    padding: 0.75rem 1rem !important;
    border-radius: 2px !important;
    text-align: left !important;
    line-height: 1.4 !important;
    transition: all 0.15s ease !important;
    min-height: 3.2rem !important;
}
[data-testid="stHorizontalBlock"] .stButton > button:hover {
    background: var(--bg-hover) !important;
    border-color: var(--border-a) !important;
    color: var(--amber) !important;
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 16px rgba(0,0,0,0.4) !important;
}
[data-testid="stHorizontalBlock"] .stButton > button:before {
    content: '→ ' !important;
    color: var(--amber) !important;
    opacity: 0.5 !important;
}

/* ── Chat messages ─────────────────────────────────────────────────────────── */
[data-testid="stChatMessage"] {
    background: transparent !important;
    border: none !important;
    padding: 0.6rem 0 !important;
}

/* User message */
[data-testid="stChatMessage"][data-testid*="user"],
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) {
    background: var(--bg-raised) !important;
    border-left: 2px solid var(--amber) !important;
    padding: 0.9rem 1.2rem !important;
    border-radius: 0 2px 2px 0 !important;
    margin: 0.4rem 0 !important;
}

/* Assistant message */
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]) {
    border-left: 2px solid var(--border) !important;
    padding: 0.9rem 1.2rem !important;
    margin: 0.4rem 0 !important;
}

/* Message text */
[data-testid="stChatMessage"] .stMarkdown p {
    font-family: var(--ff-body) !important;
    font-size: 0.9rem !important;
    line-height: 1.75 !important;
    color: var(--text-bright) !important;
}

/* Avatar icons */
[data-testid="chatAvatarIcon-user"],
[data-testid="chatAvatarIcon-assistant"] {
    background: var(--bg-raised) !important;
    border: 1px solid var(--border) !important;
    border-radius: 2px !important;
    font-size: 0.8rem !important;
}

/* ── Tool Badge (caption) ──────────────────────────────────────────────────── */
.stCaption p {
    font-family: var(--ff-mono) !important;
    font-size: 0.66rem !important;
    letter-spacing: 0.08em !important;
    text-transform: uppercase !important;
    color: var(--amber) !important;
    opacity: 0.75 !important;
    margin-bottom: 0.35rem !important;
}

/* ── Chat Input wrapper (bottom bar) ──────────────────────────────────────── */
[data-testid="stBottom"],
[data-testid="stBottom"] > div,
[data-testid="stBottom"] .stChatInputContainer,
[data-testid="stBottom"] .stChatFloatingInputContainer,
.stChatFloatingInputContainer,
.stChatFloatingInputContainer > div {
    background: var(--bg-deep) !important;
    border-top: 1px solid var(--border) !important;
}

/* ── Chat Input ────────────────────────────────────────────────────────────── */
[data-testid="stChatInput"],
[data-testid="stChatInputContainer"] {
    background: var(--bg-surface) !important;
    border: 1px solid var(--border) !important;
    border-radius: 2px !important;
    transition: border-color 0.2s !important;
}

/* BaseWeb inner containers */
[data-testid="stChatInput"] [data-baseweb="textarea"],
[data-testid="stChatInput"] [data-baseweb="base-input"],
[data-testid="stChatInputContainer"] [data-baseweb="textarea"],
[data-testid="stChatInputContainer"] [data-baseweb="base-input"] {
    background: var(--bg-surface) !important;
    border-color: var(--border) !important;
}
[data-testid="stChatInput"]:focus-within,
[data-testid="stChatInputContainer"]:focus-within {
    border-color: var(--border-a) !important;
    box-shadow: 0 0 0 1px var(--amber-dim) !important;
}
[data-testid="stChatInput"] textarea,
[data-testid="stChatInputContainer"] textarea {
    font-family: var(--ff-mono) !important;
    font-size: 0.85rem !important;
    font-weight: 300 !important;
    color: var(--text-bright) !important;
    background: transparent !important;
    caret-color: var(--amber) !important;
}
[data-testid="stChatInput"] textarea::placeholder,
[data-testid="stChatInputContainer"] textarea::placeholder {
    color: var(--text-dim) !important;
    font-style: italic !important;
}

/* Submit button */
[data-testid="stChatInput"] button,
[data-testid="stChatInputContainer"] button {
    background: var(--amber-dim) !important;
    border: 1px solid var(--border-a) !important;
    border-radius: 1px !important;
    color: var(--amber) !important;
    transition: background 0.15s !important;
}
[data-testid="stChatInput"] button:hover,
[data-testid="stChatInputContainer"] button:hover {
    background: var(--amber) !important;
    color: var(--bg-deep) !important;
}

/* ── Spinner ───────────────────────────────────────────────────────────────── */
.stSpinner > div {
    border-top-color: var(--amber) !important;
}
.stSpinner p {
    font-family: var(--ff-mono) !important;
    font-size: 0.75rem !important;
    color: var(--text-dim) !important;
    letter-spacing: 0.06em !important;
}

/* ── Horizontal Rule ───────────────────────────────────────────────────────── */
hr { border-color: var(--border) !important; margin: 1.5rem 0 !important; }

/* ── Code blocks ───────────────────────────────────────────────────────────── */
code, pre {
    font-family: var(--ff-mono) !important;
    background: var(--bg-raised) !important;
    border: 1px solid var(--border) !important;
    border-radius: 2px !important;
    font-size: 0.82rem !important;
    color: var(--teal) !important;
}

/* ── Tables (financial data) ───────────────────────────────────────────────── */
table { width: 100% !important; border-collapse: collapse !important; }
th {
    font-family: var(--ff-mono) !important;
    font-size: 0.68rem !important;
    letter-spacing: 0.1em !important;
    text-transform: uppercase !important;
    color: var(--text-dim) !important;
    border-bottom: 1px solid var(--border-a) !important;
    padding: 0.5rem 0.75rem !important;
}
td {
    font-family: var(--ff-mono) !important;
    font-size: 0.82rem !important;
    color: var(--text-mid) !important;
    border-bottom: 1px solid var(--border) !important;
    padding: 0.45rem 0.75rem !important;
}
tr:hover td { background: var(--bg-raised) !important; }

/* ── Fade-in animation ─────────────────────────────────────────────────────── */
@keyframes fadeUp {
    from { opacity: 0; transform: translateY(8px); }
    to   { opacity: 1; transform: translateY(0); }
}
[data-testid="stChatMessage"] {
    animation: fadeUp 0.22s ease forwards;
}
</style>
""", unsafe_allow_html=True)

# ── Session State ─────────────────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages: list[dict] = []
if "session_id" not in st.session_state:
    st.session_state.session_id: str | None = None

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("fAInancial")
    st.caption("AI 기반 금융 데이터 분석")
    st.divider()
    st.subheader("AVAILABLE TOOLS")
    st.markdown(
        "- [ 재무제표 ] 조회\n"
        "- [ 주가 ] 조회\n"
        "- [ 공시 ] 검색\n"
        "- [ 문서 ] 검색"
    )
    st.divider()
    if st.button("NEW SESSION", use_container_width=True):
        st.session_state.messages = []
        st.session_state.session_id = None
        st.rerun()


# ── Helpers ───────────────────────────────────────────────────────────────────
def call_agent(prompt: str) -> tuple[str, list[str]]:
    try:
        payload = {"message": prompt, "session_id": st.session_state.session_id}
        resp = requests.post(f"{AGENT_API_URL}/chat", json=payload, timeout=120)
        resp.raise_for_status()
        try:
            data = resp.json()
        except requests.exceptions.JSONDecodeError:
            logger.exception("응답 JSON 파싱 실패: %s", resp.text[:200])
            data = {}
        st.session_state.session_id = data.get("session_id")
        return data.get("response", "(응답 없음)"), data.get("tools_used", [])
    except requests.exceptions.ConnectionError:
        return f"Agent API에 연결할 수 없습니다. ({AGENT_API_URL})", []
    except requests.exceptions.Timeout:
        return "응답 시간이 초과되었습니다. 잠시 후 다시 시도해 주세요.", []
    except requests.exceptions.HTTPError as e:
        return f"API 오류: {e.response.status_code} - {e.response.text}", []
    except Exception as e:
        logger.exception("예상치 못한 오류 발생")
        return f"오류가 발생했습니다: {e}", []


def render_tool_badges(tools: list[str]):
    if not tools:
        return
    labels = [TOOL_LABELS.get(t, t) for t in tools]
    st.caption("  ·  ".join(f"[ {lbl} ]" for lbl in labels))


def send_message(prompt: str):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    with st.chat_message("assistant"):
        with st.spinner("데이터 조회 중..."):
            answer, tools_used = call_agent(prompt)
        render_tool_badges(tools_used)
        st.markdown(answer)
    st.session_state.messages.append({
        "role": "assistant", "content": answer, "tools_used": tools_used,
    })


# ── Welcome screen ────────────────────────────────────────────────────────────
if not st.session_state.messages:
    st.markdown("""
<div style="padding: 2.5rem 0 1.5rem; border-bottom: 1px solid rgba(255,255,255,0.055); margin-bottom: 2rem;">
  <div style="font-family:'IBM Plex Mono',monospace; font-size:0.65rem; letter-spacing:0.16em;
              text-transform:uppercase; color:#3E4E6A; margin-bottom:0.6rem;">
    KOREAN FINANCIAL DATA TERMINAL
  </div>
  <h1 style="font-family:'Syne',sans-serif; font-weight:800; font-size:2.6rem;
             letter-spacing:-0.02em; color:#EEF2F8; margin:0 0 0.4rem 0; line-height:1.1;">
    fAInancial Agent
  </h1>
  <p style="font-family:'IBM Plex Sans',sans-serif; font-size:0.9rem; font-weight:300;
            color:#8A95AC; margin:0; line-height:1.6;">
    DART 공시 · KRX 주가 · 재무제표를 자연어로 조회합니다
  </p>
</div>
    """, unsafe_allow_html=True)

    st.markdown('<span class="welcome-label">이런 질문을 해보세요:</span>', unsafe_allow_html=True)
    cols = st.columns(2)
    for i, q in enumerate(EXAMPLE_QUESTIONS):
        if cols[i % 2].button(q, key=f"ex_{i}", use_container_width=True):
            send_message(q)
            st.rerun()

    st.markdown("""
<div style="margin-top:3rem; padding-top:1.5rem; border-top:1px solid rgba(255,255,255,0.04);">
  <span style="font-family:'IBM Plex Mono',monospace; font-size:0.62rem; letter-spacing:0.1em;
               text-transform:uppercase; color:#3E4E6A;">
    Powered by Gemini · LangGraph · DART OpenAPI · KRX
  </span>
</div>
    """, unsafe_allow_html=True)

else:
    # ── Chat history ──────────────────────────────────────────────────────────
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            if msg["role"] == "assistant":
                render_tool_badges(msg.get("tools_used", []))
            st.markdown(msg["content"])

# ── Chat Input ────────────────────────────────────────────────────────────────
if prompt := st.chat_input("종목명 또는 질문을 입력하세요..."):
    send_message(prompt)
    st.rerun()
