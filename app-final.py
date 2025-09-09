import os
import streamlit as st

# ---- Imports for file parsing ----
from typing import List

try:
    from pypdf import PdfReader
except Exception:
    PdfReader = None

try:
    import docx
except Exception:
    docx = None

# --- OpenAI client (v1.x only) ---
from openai import OpenAI

def _get_openai_client():
    # Prefer Streamlit secrets, then env
    api_key = ""
    try:
        api_key = st.secrets.get("OPENAI_API_KEY", "")
    except Exception:
        api_key = ""
    api_key = api_key or os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        st.error("Missing OPENAI_API_KEY. Add it to .streamlit/secrets.toml or your environment.")
        return None
    return OpenAI(api_key=api_key)

def _llm_chat(system_prompt: str, user_prompt: str) -> str:
    client = _get_openai_client()
    if client is None:
        return "Missing or invalid OpenAI setup. Configure OPENAI_API_KEY."

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
        st.error(f"OpenAI call failed: {e}")
        return "There was an error calling the LLM. Check your API key, billing, SDK version, and model name."

# ===============================
# Session State Initialization
# ===============================
def init_state():
    defaults = {
        "jd_text": "",
        "cv_text": "",
        "profile_corpus": "",
        "collection": None,
        "chat": [],
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
        content = file.read()
        try:
            return content.decode("utf-8")
        except UnicodeDecodeError:
            return content.decode("latin-1", errors="ignore")
    finally:
        try:
            file.seek(0)
        except Exception:
            pass

def read_docx(file) -> str:
    if docx is None:
        st.warning("python-docx not installed; cannot read DOCX.")
        return ""
    try:
        d = docx.Document(file)
        return "\n".join(p.text for p in d.paragraphs if p.text.strip())
    except Exception as e:
        st.error(f"Failed to read DOCX: {e}")
        return ""
    finally:
        try:
            file.seek(0)
        except Exception:
            pass

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
        try:
            file.seek(0)
        except Exception:
            pass

def read_any(file, name: str) -> str:
    name_lower = (name or "").lower()
    if name_lower.endswith(".pdf"):
        return read_pdf(file)
    elif name_lower.endswith(".docx"):
        return read_docx(file)
    elif name_lower.endswith(".txt"):
        return read_txt(file)
    # fallback
    return read_txt(file)

# ===============================
# Retrieval stub (optional)
# ===============================
def retrieve(collection, prompt, k=3):
    return []

# Single, canonical entry point for the UI to call
def llm_answer_openai(system_prompt: str, user_prompt: str) -> str:
    return _llm_chat(system_prompt, user_prompt)

# === Streamlit UI ===
def main():
    st.set_page_config(page_title="ResumeBot", page_icon="🧭", layout="centered")
    st.title("ResumeBot")
    st.caption("Upload a Job Description and your Resume to tailor an application.")

    with st.sidebar:
        st.subheader("OpenAI Setup")
        key_in_secrets = False
        try:
            key_in_secrets = bool(st.secrets.get("OPENAI_API_KEY", ""))
        except Exception:
            key_in_secrets = False
        if key_in_secrets:
            st.success("OPENAI_API_KEY found in secrets.", icon="✅")
        else:
            if os.getenv("OPENAI_API_KEY"):
                st.success("OPENAI_API_KEY found in env.", icon="✅")
            else:
                st.warning("Add OPENAI_API_KEY to `.streamlit/secrets.toml` or env.", icon="⚠️")

    st.header("1) Job Description")
    jd_file = st.file_uploader("Upload JD (.pdf, .docx, .txt)", type=["pdf", "docx", "txt"], key="jd_upl")
    jd_text_area = st.text_area("...or paste JD text", value=st.session_state.get("jd_text", ""), height=180)

    st.header("2) Your Resume / Profile")
    cv_file = st.file_uploader("Upload Resume (.pdf, .docx, .txt)", type=["pdf", "docx", "txt"], key="cv_upl")
    profile_extra = st.text_area("Optional: add notes/links/extra profile info", height=120)

    # Parse uploads
    if jd_file:
        st.session_state.jd_text = read_any(jd_file, jd_file.name)
    else:
        st.session_state.jd_t
