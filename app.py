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
    pattern = r"```(?:[a-zA-Z0-9]+)?\n(.*?)```"
    matches = re.findall(pattern, text, re.DOTALL)
    return "\n\n# --- Next Code Block ---\n\n".join(matches) if matches else None

def fetch_web_results(query, tavily_key=""):
    if tavily_key:
        try:
            tavily = TavilyClient(api_key=tavily_key)
            res = tavily.search(query=query, max_results=3, search_depth="basic")
            results = res.get("results", [])
            if results:
                return "\n".join([f"• {r.get('title')}: {r.get('content')} ({r.get('url')})" for r in results])
        except Exception:
            pass

    try:
        with DDGS() as ddgs:
            raw = [r['body'] for r in ddgs.text(query, max_results=3)]
            return "\n".join(raw) if raw else ""
    except Exception:
        return ""

# 7. Sidebar (Tabs for Recent Chats, Uploads, Settings)
with st.sidebar:
    st.title("Control Panel")
    tab_chats, tab_upload, tab_settings = st.tabs(["Recent Chats", "Attachments", "Settings"])

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
                btn_label = f"💬 **{chat_name}**" if is_active else f"💬 {chat_name}"
                if st.button(btn_label, key=f"sel_{chat_name}", use_container_width=True):
                    st.session_state.active_chat = chat_name
                    st.rerun()
            with col2:
                if len(st.session_state.chats) > 1:
                    if st.button("🗑️", key=f"del_{chat_name}"):
                        del st.session_state.chats[chat_name]
                        st.session_state.active_chat = list(st.session_state.chats.keys())[0]
                        st.rerun()

    # TAB 2: File & Image Attachment
    with tab_upload:
        st.subheader("Attach File or Image")
        uploaded_file = st.file_uploader(
            "Upload image or document (.py, .txt, .json, .csv, .png, .jpg)",
            type=["png", "jpg", "jpeg", "py", "txt", "csv", "json", "md"]
        )

    # TAB 3: Settings & API Keys
    with tab_settings:
        st.subheader("Authentication")
        openai_api_key = st.text_input("OpenAI API Key", type="password", placeholder="sk-...")
        tavily_api_key = st.text_input("Tavily Key (Optional)", type="password", placeholder="tvly-...")
        replicate_api_token = st.text_input("Replicate Token (Optional)", type="password", placeholder="r8_...")

        st.subheader("Mode & Behavior")
        persona_choice = st.selectbox("Mode / Persona", list(PERSONAS.keys()))
        language_choice = st.selectbox("Response Language", list(LANGUAGES.keys()))
        model_choice = st.selectbox("Model Version", ("gpt-4o-mini", "gpt-4o"))

# Get current chat history
current_messages = st.session_state.chats[st.session_state.active_chat]

# 8. Main Chat Interface Header
st.title(f"Kevin's Chatbot")
st.caption(f"Active Session: **{st.session_state.active_chat}** | Mode: **{persona_choice}**")

# Display Message History for Active Chat
for idx, msg in enumerate(current_messages):
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if "image_bytes" in msg:
            st.image(msg["image_bytes"])
        if "video_url" in msg:
            st.video(msg["video_url"])
        
        # Display Code Download Button if message contains code
        if msg["role"] == "assistant":
            extracted_code = extract_code_from_text(msg["content"])
            if extracted_code:
                st.download_button(
                    label="📄 Download Generated Code",
                    data=extracted_code,
                    file_name="script.py",
                    mime="text/x-python",
                    key=f"dl_hist_{idx}"
                )

# 9. Process User Input & File Uploads
if prompt := st.chat_input("Type a message or ask to write/debug code..."):
    if not openai_api_key:
        st.info("Please enter your OpenAI API key in the sidebar under Settings to begin.")
        st.stop()

    # Parse attached file content
    file_context_str = ""
    image_b64 = None

    if uploaded_file is not None:
        file_bytes = uploaded_file.getvalue()
        file_type = uploaded_file.type
        
        if "image" in file_type or uploaded_file.name.endswith(('.png', '.jpg', '.jpeg')):
            image_b64 = base64.b64encode(file_bytes).decode('utf-8')
            prompt_display = f"📷 *[Attached Image: {uploaded_file.name}]*\n\n{prompt}"
        else:
            try:
                text_content = file_bytes.decode('utf-8')
                file_context_str = f"\n\n--- ATTACHED FILE ({uploaded_file.name}) ---\n```{text_content}