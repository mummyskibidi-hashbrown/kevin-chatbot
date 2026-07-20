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
    page_icon="💬",
    layout="centered",
    initial_sidebar_state="expanded"
)

# 2. Custom Styling
st.markdown("""
<style>
    .block-container {
        padding-top: 2rem;
        padding-bottom: 3rem;
    }
    .stButton > button {
        border-radius: 8px;
    }
    .stChatMessage {
        border-radius: 10px;
        padding: 0.8rem;
    }
</style>
""", unsafe_allow_html=True)

# 3. Development Disclaimer Modal
if "disclaimer_accepted" not in st.session_state:
    st.session_state.disclaimer_accepted = False

@st.dialog("Beta Notice & Limitations")
def show_disclaimer_modal():
    st.markdown("""
    Welcome! This app is an **experimental preview** currently in active development.

    **Please review before continuing:**
    * **Accuracy:** AI outputs can be wrong, outdated, or fabricated. Double-check all code and facts.
    * **Web Search & Vision:** Search results and file parsing rely on automated external services.
    
    Always double-check important outputs against primary sources.
    """)
    st.markdown("---")
    if st.button("I Understand & Agree", type="primary", use_container_width=True):
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
    pattern = r"```(?:[a-zA-Z0-9]+)?\n(.*?)