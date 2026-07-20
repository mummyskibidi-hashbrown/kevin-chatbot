else:
        # Standard Groq Text Generation with Web Search & System Prompts
        with st.chat_message("assistant"):
            try:
                # Check if prompt requires web lookup
                search_keywords = ["winner", "who won", "score", "news", "latest", "current", "2026", "result", "match", "in "]
                should_search = any(kw in prompt_lower for kw in search_keywords)
                
                search_context = ""
                if should_search:
                    with st.spinner("Searching the web..."):
                        # Find the previous user message to give context to short follow-ups
                        previous_user_prompt = ""
                        for m in reversed(st.session_state.messages[:-1]):
                            if m["role"] == "user":
                                previous_user_prompt = m["content"]
                                break
                        
                        # Combine previous query with current prompt for a smart search query
                        search_query = f"{previous_user_prompt} {prompt}" if previous_user_prompt and len(prompt) < 15 else prompt
                        search_context = search_web(search_query)
                
                client = Groq(api_key=groq_api_key)
                
                # Enforce strict system instructions to force the AI to use web search results
                system_content = f"{PERSONAS[persona_option]} {LANGUAGES[language_option]}"
                if search_context:
                    system_content += f"""

CRITICAL INSTRUCTIONS FOR LIVE SEARCH:
- You have been provided with LIVE WEB SEARCH RESULTS below.
- You MUST rely on these live search results to answer questions about recent events, matches, and winners.
- Do NOT claim that 2026 events haven't happened yet if the search results contain information about them. Treat the search results as absolute fact.

Live web search results:
{search_context}"""

                api_messages = [{"role": "system", "content": system_content}]
                
                for m in st.session_state.messages:
                    if m["role"] in ["user", "assistant"]:
                        api_messages.append({"role": m["role"], "content": m["content"]})

                stream = client.chat.completions.create(
                    model=model_option,
                    messages=api_messages,
                    stream=True,
                )
                
                def stream_response():
                    for chunk in stream:
                        content = chunk.choices[0].delta.content
                        if content:
                            yield content

                response = st.write_stream(stream_response)
                st.session_state.messages.append({"role": "assistant", "content": response})

            except Exception as e:
                st.error(f"An error occurred: {e}")