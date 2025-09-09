
import os
import io
import streamlit as st

# ---- Optional imports for file parsing ----
from typing import List

try:
    from pypdf import PdfReader
except Exception:
    PdfReader = None

try:
    import docx
except Exception:
    docx = None

# ===============================
# OpenAI (>=1.0) Client Helper
# ===============================
def get_openai_client():
    """
    Returns an OpenAI client from openai>=1.0.
    Reads API key from Streamlit secrets or environment.
    Shows a friendly warning if not configured.
    """
    api_key = None
    try:
        api_key = st.secrets.get("OPENAI_API_KEY", None)
    except Exception:
        api_key = None
    if not api_key:
        api_key = os.getenv("OPENAI_API_KEY")

    try:
        from openai import OpenAI
    except Exception as e:
        st.error("OpenAI SDK not installed or is the legacy 0.x version. "
                 "Make sure requirements include 'openai>=1.0' and that it is installed.")
        return None

    if not api_key:
        st.warning("OpenAI API key not found. Add OPENAI_API_KEY to .streamlit/secrets.toml or environment variables.")
        return None

    # Construct the client (>=1.0 syntax)
    return OpenAI(api_key=api_key)


def call_llm_chat(system_prompt: str, user_prompt: str, model: str = "gpt-4o-mini", temperature: float = 0.2) -> str:
    """
    Calls the Chat Completions API using openai>=1.0 interface.
    """
    client = get_openai_client()
    if client is None:
        return "Missing or invalid OpenAI setup. Please configure OPENAI_API_KEY and install 'openai>=1.0'."

    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
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
        file.seek(0)

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
    return read_txt(file)

# ===============================
# Main UI
# ===============================
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
                st.success("OPENAI_API_KEY found in environment.", icon="✅")
            else:
                st.warning("Add OPENAI_API_KEY to `.streamlit/secrets.toml` or environment variables.", icon="⚠️")

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
        st.session_state.jd_text = jd_text_area

    parsed_cv = ""
    if cv_file:
        parsed_cv = read_any(cv_file, cv_file.name)

    # Prompts
    system_prompt = (
        "You are a helpful assistant that writes tailored cover letters and bullet points that map a resume "
        "to a given job description. Be concise and specific."
    )

    st.header("3) Generate")
    col1, col2 = st.columns(2)
    with col1:
        gen_cover = st.button("Generate Cover Letter")
    with col2:
        gen_bullets = st.button("Generate Resume Bullets")

    output = ""
    if gen_cover or gen_bullets:
        if not st.session_state.jd_text.strip():
            st.error("Please provide a Job Description (upload or paste).")
        elif not (parsed_cv.strip() or profile_extra.strip()):
            st.error("Please provide your Resume (upload) or profile text.")
        else:
            user_prompt = f"""JOB DESCRIPTION:
{st.session_state.jd_text}

RESUME / PROFILE:
{parsed_cv}

EXTRA NOTES:
{profile_extra}

TASK: {"Write a tailored cover letter (<= 300 words)." if gen_cover else "Write 6–8 quantified resume bullet points mapped to the JD, grouped by theme."}
"""
            with st.spinner("Thinking..."):
                output = call_llm_chat(system_prompt, user_prompt, model="gpt-4o-mini", temperature=0.2)

    if output:
        st.divider()
        st.subheader("Result")
        st.write(output)


if __name__ == "__main__":
    main()
