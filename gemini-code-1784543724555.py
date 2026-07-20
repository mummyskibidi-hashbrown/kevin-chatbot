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
        tavily_api_key = st.text_input("Tavily Key (Optional)", type="password", placeholder="tvly-...")
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
        2. Select a persona mode (e.g., **Coding Mode** for technical assistance).
        3. Type a message in the main chat prompt below.

        **Key Features:**
        * **Coding Mode:** Generates formatted code blocks with an automatic **Download Code** button.
        * **File Analysis:** Upload source files (`.py`, `.json`, `.csv`) or images in the **Attachments** tab before submitting your prompt.
        * **Recent Chats:** Manage multiple chat threads in the **Recent Chats** tab.

        **Increasing Upload File Size Limit:**
        To allow uploads larger than Streamlit's default 200MB limit, create or edit `.streamlit/config.toml` in your project folder:
        ```toml
        [server]
        maxUploadSize = 500
        ```
        """)

# Get current chat history
current_messages = st.session_state.chats[st.session_state.active_chat]

# 8. Main Chat Interface Header
st.title("Kevin's Chatbot")
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
                    label="Download Generated Code",
                    data=extracted_code,
                    file_name="script.py",
                    mime="text/x-python",
                    key=f"dl_hist_{idx}"
                )

# 9. Process User Input & File Uploads
if prompt := st.chat_input("Type a message or ask to write/debug code..."):
    if not openai_api_key:
        st.info("Please enter your OpenAI API key in the sidebar under Setup to begin.")
        st.stop()

    # Parse attached file content
    file_context_str = ""
    image_b64 = None

    if uploaded_file is not None:
        file_bytes = uploaded_file.getvalue()
        file_type = uploaded_file.type
        
        if "image" in file_type or uploaded_file.name.endswith(('.png', '.jpg', '.jpeg')):
            image_b64 = base64.b64encode(file_bytes).decode('utf-8')
            prompt_display = f"[Attached Image: {uploaded_file.name}]\n\n{prompt}"
        else:
            try:
                text_content = file_bytes.decode('utf-8', errors='ignore')
                bt = "`" * 3
                file_context_str = (
                    f"\n\n--- ATTACHED FILE ({uploaded_file.name}) ---\n"
                    f"{bt}\n" + text_content + f"\n{bt}\n--- END FILE ---"
                )
                prompt_display = f"[Attached File: {uploaded_file.name}]\n\n{prompt}"
            except Exception:
                prompt_display = prompt
    else:
        prompt_display = prompt

    # Save User Message to Current Active Chat
    current_messages.append({"role": "user", "content": prompt_display})
    with st.chat_message("user"):
        st.markdown(prompt_display)

    prompt_low = prompt.lower()
    is_video = any(kw in prompt_low for kw in ["generate video", "make a video", "animate"])
    is_image = any(kw in prompt_low for kw in ["generate image", "draw", "make a picture", "create photo"])

    # Option A: Video Generation
    if is_video and replicate_api_token:
        with st.chat_message("assistant"):
            with st.spinner("Rendering video (30-60s)..."):
                try:
                    import os
                    os.environ["REPLICATE_API_TOKEN"] = replicate_api_token
                    output = replicate.run(
                        "kwaivgi/kling-v1.6-standard",
                        input={"prompt": prompt, "duration": 5}
                    )
                    url = output[0] if isinstance(output, list) else output
                    text = f"Generated video for: *{prompt}*"
                    st.markdown(text)
                    st.video(url)
                    current_messages.append({"role": "assistant", "content": text, "video_url": url})
                except Exception as e:
                    st.error(f"Failed to generate video: {e}")

    # Option B: Image Generation
    elif is_image:
        with st.chat_message("assistant"):
            with st.spinner("Generating image..."):
                try:
                    client = OpenAI(api_key=openai_api_key)
                    res = client.images.generate(model="gpt-image-2", prompt=prompt, n=1)
                    img_bytes = base64.b64decode(res.data[0].b64_json)
                    text = f"Generated image for: *{prompt}*"
                    st.markdown(text)
                    st.image(img_bytes)
                    current_messages.append({"role": "assistant", "content": text, "image_bytes": img_bytes})
                except Exception as e:
                    st.error(f"Failed to generate image: {e}")

    # Option C: Chat & Code Response (GPT-4o / GPT-4o-Mini with Vision & Web Search)
    else:
        with st.chat_message("assistant"):
            try:
                # Web Search Context
                keywords = ["latest", "news", "who won", "score", "current", "2026", "today"]
                needs_search = any(kw in prompt_low for kw in keywords)
                search_context = ""
                
                if needs_search:
                    with st.spinner("Checking live sources..."):
                        search_context = fetch_web_results(prompt, tavily_key=tavily_api_key)

                client = OpenAI(api_key=openai_api_key)
                
                sys_prompt = f"{PERSONAS[persona_choice]} {LANGUAGES[language_choice]}\nSystem Year: 2026."
                if search_context:
                    sys_prompt += f"\n\nLive Search Reference Data:\n{search_context}"

                # Format messages payload
                messages_payload = [{"role": "system", "content": sys_prompt}]
                
                for m in current_messages[:-1]:
                    if m["role"] in ["user", "assistant"]:
                        messages_payload.append({"role": m["role"], "content": m["content"]})

                # Build final multi-modal prompt with attached file / image
                final_user_text = prompt + file_context_str
                
                if image_b64:
                    user_content_payload = [
                        {"type": "text", "text": final_user_text},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}}
                    ]
                else:
                    user_content_payload = final_user_text

                messages_payload.append({"role": "user", "content": user_content_payload})

                # Stream response
                stream = client.chat.completions.create(
                    model=model_choice,
                    messages=messages_payload,
                    stream=True,
                )
                
                def stream_gen():
                    for chunk in stream:
                        delta = chunk.choices[0].delta.content
                        if delta:
                            yield delta

                output_text = st.write_stream(stream_gen)
                current_messages.append({"role": "assistant", "content": output_text})

                # Display download button immediately if response contained code
                extracted_code = extract_code_from_text(output_text)
                if extracted_code:
                    st.download_button(
                        label="Download Generated Code",
                        data=extracted_code,
                        file_name="script.py",
                        mime="text/x-python",
                        key=f"dl_live_{len(current_messages)}"
                    )

            except Exception as e:
                st.error(f"Error: {e}")