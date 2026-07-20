def extract_code_from_text(text):
    """Extracts code blocks from markdown text for downloading."""
    # Uses explicit backtick sequence to prevent parser errors on copy-paste
    backticks = "`" * 3
    pattern = backticks + r"(?:[a-zA-Z0-9_]+)?\n(.*?)" + backticks
    matches = re.findall(pattern, text, re.DOTALL)
    return "\n\n# --- Next Code Block ---\n\n".join(matches) if matches else None