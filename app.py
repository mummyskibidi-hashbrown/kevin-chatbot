import streamlit as st
from groq import Groq
from PIL import Image
import io
import replicate
import base64
import re
import pypdf
from duckduckgo_search import DDGS
from tavily import TavilyClient

# 1. Page Configuration
st.set_page_config(
    page_title="Kevin's Chatbot",
    layout="centered",
    initial_sidebar_state="expanded"
)

# 2. Custom CSS - Square / Angular Design System
st.markdown("""
<style>
    .block-container {
        padding-top: 2rem;
        padding-bottom: 3rem;
    }
    .stButton > button {
        border-radius: 2px !important;
        font-weight: 500;
    }
    .stChatMessage {
        border-radius: 2px !important;
        border: 1px solid #e0e0e0;
        padding: 0.8rem;
    }
    div[data-baseweb="input"] {
        border-radius: 2px !important;
    }
    div[data-baseweb="select"] {
        border-radius: 2px !important;
    }
</style>
""", unsafe_allow_html=True)

# 3. Development Disclaimer Modal
if "disclaimer_accepted" not in st.session_state:
    st.session_state.disclaimer_accepted = False

@st.dialog("Beta Notice and Limitations")
def show_disclaimer_modal():
    st.markdown(
        "Welcome. This application is an experimental preview currently in active development.\n\n"
        "**Please review before continuing:**\n"
        "* **Accuracy:** AI outputs can be wrong, outdated, or fabricated. Always double-check code and facts.\n"
        "* **Web Search:** Search results and file parsing rely on automated external services.\n\n"
        "Verify critical information against primary documentation."
    )
    st.markdown("---")
    if st.button("I Understand and Agree", type="primary", use_container_width=True):
        st.session_state.disclaimer_accepted = True
        st.rerun()

if not st.session_state.disclaimer_accepted:
    show_disclaimer_modal()

# 4. Multi-Chat Session State Initialization
if "chats" not in st.session_state:
    st.session_state.chats = {"Main Chat": []}
if "active_chat" not in st.session_state:
    st.session_state.active_chat = "Main Chat"

# 5. Personas & Settings
PERSONAS = {
    "Helpful Assistant": "You are a clear, direct, and knowledgeable AI assistant.",
    "Coding Mode": "You are an expert software engineer and coding assistant. Write clean, efficient, production-ready, bug-free code with clear comments. Format code blocks strictly using standard markdown code fences with language identifiers.",
    "Technical Expert": "You provide precise, highly technical explanations with code snippets where applicable.",
    "Casual & Direct": "You speak concisely, use everyday casual phrasing, and get straight to the point.",
    "Unhinged & Unfiltered": "You are a chaotic, vulgar, and completely unfiltered AI persona. Use aggressive profanity and erratic capitalization in every sentence."
}

LANGUAGES = {
    "Auto-Detect": "Respond in whichever language the user inputs.",
    "English": "Respond strictly in English.",
    "Spanish": "Respond strictly in Spanish.",
    "French": "Respond strictly in French.",
    "German": "Respond strictly in German.",
    "Japanese": "Respond strictly in Japanese."
}

# 6. Helper Functions & Search Optimizer
def extract_code_from_text(text):
    """Extracts code blocks from markdown text for downloading."""
    fence = "```"
    pattern = fence + r"(?:[a-zA-Z0-9_]+)?\n(.*?)" + fence
    matches = re.findall(pattern, text, re.DOTALL)
    return "\n\n# --- Next Code Block ---\n\n".join(matches) if matches else None

ACRONYMS = {
    r"\bwc\b": "world cup",
    r"\bucl\b": "uefa champions league",
    r"\bepl\b": "premier league",
    r"\bnba\b": "nba finals",
    r"\bnfl\b": "super bowl",
    r"\bmlb\b": "world series"
}

def optimize_search_query(query, chat_history=[]):
    """Expands short acronyms and enriches short/vague prompts with chat context."""
    clean_q = query.lower()

    # Expand common sports/event acronyms
    for pattern, replacement in ACRONYMS.items():
        clean_q = re.sub(pattern, replacement, clean_q)

    # Attach history context for short follow-up queries (< 5 words)
    if len(clean_q.split()) <= 5 and chat_history:
        past_user_msgs = [m["content"] for m in chat_history if m["role"] == "user"]
        if past_user_msgs:
            last_msg = past_user_msgs[-1]
            if "]\n\n" in last_msg:
                last_msg = last_msg.split("]\n\n")[-1]
            for pattern, replacement in ACRONYMS.items():
                last_msg = re.sub(pattern, replacement, last_msg, flags=re.IGNORECASE)
            clean_q = f"{last_msg} {clean_q}"

    # Auto-add recent year anchor if asking for winners/results without a specified year
    if any(w in clean_q for w in ["winner", "won", "champion", "world cup", "finals", "champions league"]) and not re.search(r"\b202\d\b", clean_q):
        clean_q += " 2026"

    return clean_q.strip()

def fetch_web_results(query, chat_history=[], tavily_key=""):
    """Fetches real-time web results using optimized search strings."""
    optimized_q = optimize_search_query(query, chat_history)

    if tavily_key:
        try:
            tavily = TavilyClient(api_key=tavily_key)
            res = tavily.search(query=optimized_q, max_results=4, search_depth="basic")
            results = res.get("results", [])
            if results:
                return "\n".join([f"* {r.get('title')}: {r.get('content')} ({r.get('url')})" for r in results])
        except Exception:
            pass

    try:
        with DDGS() as ddgs:
            raw = [r['body'] for r in ddgs.text(optimized_q, max_results=4)]
            return "\n".join(raw) if raw else ""
    except Exception:
        return ""

# 7. Sidebar Control Panel
with st.sidebar:
    st.title("Control Panel")
    tab_chats, tab_upload, tab_setup, tab_instructions = st.tabs(["Recent Chats", "Attachments", "Setup", "Instructions"])

    # TAB 1: Recent Chats Management
    with tab_chats:
        st.subheader("Sessions")
        if st.button("+ New Chat", use_container_width=True, type="primary"):
            new_id = f"Chat {len(st.session_state.chats) + 1}"
            st.session_state.chats[new_id] = []
            st.session_state.active_chat = new_id
            st.rerun()

        st.markdown("---")
        for chat_name in list(st.session_state.chats.keys()):
            col1, col2 = st.columns([0.8, 0.2])
            with col1:
                is_active = (chat_name == st.session_state.active_chat)
