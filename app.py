import streamlit as st
from openai import OpenAI
import replicate
import base64
import re
from duckduckgo_search import DDGS
from tavily import TavilyClient

# 1. Page Configuration
st.set_page_config(
    page_title="Kevin's Chatbot",
    layout="centered",
    initial_sidebar_state="expanded"
)

# 2. Custom CSS - Square / Angular Design
st.markdown("""
<style>
    /* Sharp, square design system */
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
    st.markdown("""
    Welcome. This application is an experimental preview currently in active development.

    **Please review before continuing:**
    * **Accuracy:** AI outputs can be wrong, outdated, or fabricated. Always double-check code and facts.
    * **Web Search and Vision:** Search results and file parsing rely on automated external services.
    
    Verify critical information against primary documentation.
    """)
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

# 6. Helper Functions
def extract_code_from_text(text):
    """Extracts code blocks from markdown text for downloading."""
    backticks = "`" * 3
    pattern = backticks + r"(?:[a-zA-Z0-9_]+)?\n(.*?)" + backticks
    matches = re.findall(pattern, text, re.DOTALL)
    return "\n\n# --- Next Code Block ---\n\n".join(matches) if matches else None

def fetch_web_results(query, tavily_key=""):
    if tavily_key:
        try:
            tavily = TavilyClient(api_key=tavily_key)
            res = tavily.search(query=query, max_results=3, search_depth="basic")
            results = res.get("results", [])
            if results:
                return "\n".join([f"* {r.get('title')}: {r.get('content')} ({r.get('url')})" for r in results])
        except Exception:
            pass

    try:
        with DDGS() as ddgs:
            raw = [r['body'] for r in ddgs.text(query, max_results=3)]
            return "\n".join(raw) if raw else ""
    except Exception:
        return ""

# 7. Sidebar
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
                btn_label = f"**{chat_name}**" if is_active else chat_name
                if st.button(btn_label, key=f"sel_{chat_name}", use_container_width=True):
                    st.session_state.active_chat = chat_name
                    st.rerun()
            with col2:
                if len(st.session_state.chats) > 1:
                    if st.button("X", key=f"del_{chat_name}"):
                        del st.session_state.chats[chat_name]
                        st.session_state.active_chat = list(st.session_state.chats.keys())[0]
                        st.rerun()

    # TAB 2: File & Image Attachment
    with tab_upload:
        st.subheader("Attach File or Image")
        uploaded_file = st.file_uploader(
            "Upload image, code, or document",
            type=["png", "jpg", "jpeg", "py", "txt", "csv", "json", "md", "js", "html", "css", "cpp", "c", "java", "pdf"]
        )

    # TAB 3: Setup (API Keys & Model Parameters)
    with tab_setup:
        st.subheader("Authentication")
        openai_api_key = st.text_input("OpenAI API Key", type="password", placeholder="sk-...")
        tavily_api_key = st.text_input("Tavily API Key (Optional for Real-Time Search)", type="password", placeholder="tvly-...")
        replicate_api_token = st.text_input("Replicate Token (Optional)", type="password", placeholder="r8_...")

        st.subheader("Mode and Behavior")
        persona_choice = st.selectbox("Mode / Persona", list(PERSONAS.keys()))
        language_choice = st.selectbox("Response Language", list(LANGUAGES.keys()))
        model_choice = st.selectbox("Model Version", ("gpt-4o-mini", "gpt-4o"))

    # TAB 4: Instructions
    with tab_instructions:
        st.subheader("System Instructions")
        st.markdown("""
        **Getting Started:**
        1. Go to the **Setup** tab and enter your **OpenAI API Key**.
        2. Enter your **Tavily API Key** if you wish to enable real-time web searching capabilities.
        3. Select a persona mode (e.g., **Coding Mode** for technical assistance).
        4. Type a message in the main chat prompt below.

        **Key Features:**
        * **Real-Time Web Search:** Uses Tavily API to fetch current online information automatically.
        * **Coding Mode:** Generates formatted code blocks with an automatic **Download Code** button.
        * **File Analysis:** Upload source files (`.py`, `.json`, `.csv`) or images in the **Attachments** tab before submitting your prompt.
        * **Recent Chats:** Manage multiple chat threads in the **Recent Chats** tab.

        **Increasing Upload File Size Limit:**
        To allow uploads larger than Streamlit's default 200MB limit, create or edit `.streamlit/config.toml` in your project folder:
        ```toml
        [server]
        maxUploadSize = 500