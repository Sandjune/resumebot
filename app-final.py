import os
import io
import streamlit as st

# ---- Imports for file parsing ----
from typing import List



# --- OpenAI SDK compatibility (v1.x and legacy 0.x) ---
# Tries modern client first; falls back to legacy "openai" import if needed.
def _load_openai_client_and_call():
    import os, streamlit as st
    api_key = None
    try:
        api_key = st.secrets.get("OPENAI_API_KEY", None)
    except Exception:
        api_key = None
    if not api_key:
        api_key = os.getenv("OPENAI_API_KEY")

    # Try modern SDK first
    try:
        from openai import OpenAI  # v1+
        if not api_key:
            st.warning("OpenAI API key not found. Add OPENAI_API_KEY to .streamlit/secrets.toml or environment variables.")
            return None, "modern"
        client = OpenAI(api_key=api_key)
        return client, "modern"
    except Exception:
        # Fallback: legacy SDK
        try:
            import openai as openai_legacy  # 0.x
            if not api_key:
                st.warning("OpenAI API key not found. Add OPENAI_API_KEY to .streamlit/secrets.toml or environment variables.")
                return None, "legacy"
            openai_legacy.api_key = api_key
            return openai_legacy, "legacy"
        except Exception:
            st.error("OpenAI SDK not installed. Run: pip install --upgrade openai")
            return None, "none"


def _llm_chat(system_prompt: str, user_prompt: str) -> str:
    client, mode = _load_openai_client_and_call()
    if client is None:
        return "Missing or invalid OpenAI setup. Please configure OPENAI_API_KEY and install the 'openai' package."

    try:
        if mode == "modern":
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.2,
            )
            return resp.choices[0].message.content
        else:
            # Legacy API shape
            resp = client.ChatCompletion.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.2,
            )
            return resp["choices"][0]["message"]["content"]
    except Exception as e:
        import streamlit as st
        st.error(f"OpenAI call failed: {e}")
        return "There was an error calling the LLM. Check your API key, billing, SDK version, and model name."


try:
    from pypdf import PdfReader
except Exception:
    PdfReader = None

try:
    import docx
except Exception:
    docx = None


# ===============================
# Session State Initialization
# ===============================
def init_state():
    defaults = {
        "jd_text": "",
        "cv_text": "",                 # (optional) if you want a single-CV text
        "profile_corpus": "",          # concatenated text from profile uploads + freeform
        "collection": None,            # placeholder for your vector DB collection
        "chat": [],                    # chat history
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()


# ===============================
# File Parsing Helpers
# ===============================
def read_txt(file) -> str:
    try:
        # file may be BytesIO; decode as utf-8, fallback latin-1
        content = file.read()
        try:
            return content.decode("utf-8")
        except UnicodeDecodeError:
            return content.decode("latin-1", errors="ignore")
    finally:
        file.seek(0)

def read_docx(file) -> str:
    if docx is None:
        st.warning("python-docx not installed; cannot read DOCX.")
        return ""
    try:
        # python-docx can read file-like objects directly
        d = docx.Document(file)
        return "\n".join(p.text for p in d.paragraphs if p.text.strip())
    except Exception as e:
        st.error(f"Failed to read DOCX: {e}")
        return ""
    finally:
        file.seek(0)

def read_pdf(file) -> str:
    if PdfReader is None:
        st.warning("pypdf not installed; cannot read PDF.")
        return ""
    try:
        reader = PdfReader(file)
        parts = []
        for page in reader.pages:
            try:
                parts.append(page.extract_text() or "")
            except Exception:
                pass
        return "\n".join(parts)
    except Exception as e:
        st.error(f"Failed to read PDF: {e}")
        return ""
    finally:
        file.seek(0)

def read_any(file, name: str) -> str:
    name_lower = (name or "").lower()
    if name_lower.endswith(".pdf"):
        return read_pdf(file)
    elif name_lower.endswith(".docx"):
        return read_docx(file)
    elif name_lower.endswith(".txt"):
        return read_txt(file)
    # fallback: try text
    return read_txt(file)


# ===============================
# Placeholder Retrieval & LLM
# (replace with your actual logic)
# ===============================
def retrieve(collection, prompt, k=3):
    # TODO: replace with your retrieval logic
    return []


def llm_answer_openai(system_prompt: str, user_prompt: str) -> str:
    """Call OpenAI Chat Completions with gpt-4o-mini (or your chosen model)."""
    client = None  # removed; using _llm_chat
    if client is None:
        return "Missing OPENAI_API_KEY. Please add it to .streamlit/secrets.toml or your environment."
    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
        )
        return resp.choices[0].message.content
    except Exception as e:
        import streamlit as st
        st.error(f"OpenAI call failed: {e}")
        return "There was an error calling the LLM. Check your API key, billing, and model name."
