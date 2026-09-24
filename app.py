import streamlit as st
import re
from difflib import SequenceMatcher
from groq import Groq

try:
    import textstat
except ImportError:
    textstat = None

# -----------------------------
# PAGE CONFIG
# -----------------------------

st.set_page_config(
    page_title="Academic Humanizer Pro",
    page_icon="📚",
    layout="wide"
)

# -----------------------------
# GROQ CLIENT & MODEL FETCHING
# -----------------------------

if "GROQ_API_KEY" not in st.secrets:
    st.error("Missing GROQ_API_KEY in Streamlit secrets. Please add it to .streamlit/secrets.toml")
    st.stop()

client = Groq(api_key=st.secrets["GROQ_API_KEY"])

@st.cache_data(ttl=3600)
def fetch_available_models():
    """Dynamically fetches active chat models from your Groq API key."""
    fallback_models = [
        "llama-3.3-70b-versatile",
        "llama-3.1-8b-instant",
        "deepseek-r1-distill-llama-70b",
        "mixtral-8x7b-32768",
        "llama-3.2-11b-vision-instruct"
    ]
    try:
        models_data = client.models.list()
        chat_models = [
            m.id for m in models_data.data 
            if not any(excluded in m.id for excluded in ["whisper", "guard", "embed", "tts", "moderation"])
        ]
        # Sort so 70B / versatile models appear near the top if present
        chat_models.sort(key=lambda x: ("70b" not in x.lower(), "versatile" not in x.lower(), x))
        return chat_models if chat_models else fallback_models
    except Exception:
        return fallback_models

# -----------------------------
# CITATION & NUMBER LOCKING
# -----------------------------

def lock_citations(text):
    """Safely locks bracketed citations like [1] or [12-15] into tokens."""
    mapping = {}
    counter = 0

    def replace_match(match):
        nonlocal counter
        token = f"__CIT_{counter}__"
        mapping[token] = match.group(0)
        counter += 1
        return token

    locked_text = re.sub(r"\[\d+(?:[-–]\d+)?\]", replace_match, text)
    return locked_text, mapping

def restore_citations(text, mapping):
    for token, citation in mapping.items():
        text = text.replace(token, citation)
    return text

def lock_numbers(text):
    """Safely locks numbers and percentages into tokens without corrupting citation tokens."""
    mapping = {}
    counter = 0

    def replace_match(match):
        nonlocal counter
        token = f"__NUM_{counter}__"
        mapping[token] = match.group(0)
        counter += 1
        return token

    # Matches numbers/percentages while ignoring digits inside existing tokens
    pattern = r"(?<![a-zA-Z_])\d+(?:\.\d+)?%?(?![a-zA-Z_])"
    locked_text = re.sub(pattern, replace_match, text)
    return locked_text, mapping

def restore_numbers(text, mapping):
    for token, value in mapping.items():
        text = text.replace(token, value)
    return text

# -----------------------------
# LLM REWRITE
# -----------------------------

def rewrite_text(text, mode, model_name):
    base_instructions = """
STRICT RULE FOR PLACEHOLDERS:
- Do NOT alter, delete, translate, or move any placeholder tokens like `__CIT_0__` or `__NUM_1__`.
- Leave all `__CIT_X__` and `__NUM_X__` tokens in their exact original form.
"""

    prompts = {
        "Light": f"""
{base_instructions}
Task: Rewrite lightly for flow and readability.
Requirements:
- Preserve technical meaning and key details.
- Preserve all placeholder tokens exactly as written.
- Make light adjustments to grammar and sentence flow.
""",
        "Medium": f"""
{base_instructions}
Task: Rewrite in clear, natural academic English.
Requirements:
- Preserve all placeholder tokens exactly as written.
- Reduce textual similarity while maintaining academic rigor.
- Vary sentence structures and improve sentence flow.
- Eliminate overly robotic AI phrasing.
""",
        "Aggressive": f"""
{base_instructions}
Task: Restructure and rewrite extensively.
Requirements:
- Preserve all placeholder tokens exactly as written.
- Reorganize ideas, combine/split sentences, and increase sentence length variation (burstiness).
- Significantly minimize textual overlap while retaining full scholarly accuracy.
"""
    }

    try:
        completion = client.chat.completions.create(
            model=model_name,
            temperature=0.7,
            max_tokens=4096,
            messages=[
                {"role": "system", "content": prompts[mode]},
                {"role": "user", "content": text}
            ]
        )
        return completion.choices[0].message.content
    except Exception as e:
        return f"Error: API call failed. Details: {str(e)}"

# -----------------------------
# METRICS
# -----------------------------

def similarity_score(original, rewritten):
    return round(SequenceMatcher(None, original, rewritten).ratio() * 100, 2)

def originality_score(original, rewritten):
    return round(100 - similarity_score(original, rewritten), 2)

def readability_score(text):
    if textstat is None:
        return "N/A"
    try:
        return round(textstat.flesch_reading_ease(text), 2)
    except Exception:
        return "N/A"

# -----------------------------
# UI LAYOUT
# -----------------------------

st.title("📚 Academic Humanizer Pro")

st.markdown("""
### Features
✅ **Citation & Statistics Locking** (Preserves `[1]`, percentages, and figures automatically)  
✅ **Dynamic Groq Models** (Choose from available Llama, DeepSeek, or Mixtral models)  
✅ **Originality & Readability Analysis**  
""")

col_mode, col_model = st.columns(2)

with col_mode:
    rewrite_mode = st.selectbox("Rewrite Strength", ["Light", "Medium", "Aggressive"], index=1)

with col_model:
    available_models = fetch_available_models()
    selected_model = st.selectbox("Select Groq Model", available_models, index=0)

input_text = st.text_area("Paste Academic Text Here", height=280, placeholder="Enter academic text containing citations and numerical findings...")

if st.button("✨ Humanize Text", type="primary"):
    if not input_text.strip():
        st.warning("Please paste some text before rewriting.")
    else:
        with st.spinner(f"Rewriting using `{selected_model}`..."):
            # Step 1: Lock citations & numbers into placeholders
            text_locked, citation_map = lock_citations(input_text)
            text_locked, number_map = lock_numbers(text_locked)
            
            # Step 2: Query Groq LLM
            rewritten_raw = rewrite_text(text_locked, rewrite_mode, selected_model)
            
            if rewritten_raw.startswith("Error:"):
                st.error(rewritten_raw)
            else:
                # Step 3: Restore citations & numbers from placeholders
                rewritten_final = restore_numbers(rewritten_raw, number_map)
                rewritten_final = restore_citations(rewritten_final, citation_map)
                
                st.session_state["original"] = input_text
                st.session_state["rewritten"] = rewritten_final

# -----------------------------
# RESULTS DISPLAY
# -----------------------------

if "original" in st.session_state and "rewritten" in st.session_state:
    original = st.session_state["original"]
    rewritten = st.session_state["rewritten"]

    similarity = similarity_score(original, rewritten)
    originality = originality_score(original, rewritten)
    readability = readability_score(rewritten)

    st.divider()

    m1, m2, m3 = st.columns(3)
    with m1:
        st.metric("Similarity", f"{similarity}%")
    with m2:
        st.metric("Originality Score", f"{originality}%")
    with m3:
        st.metric("Readability Ease (Flesch)", readability)

    st.divider()

    left, right = st.columns(2)
    with left:
        st.subheader("Original Input")
        st.text_area("Original Output", original, height=400, key="orig_display", disabled=True)

    with right:
        st.subheader("Humanized Output")
        st.text_area("Rewritten Output", rewritten, height=400, key="rewrite_display")

    st.download_button(
        label="📥 Download Rewritten Text (.txt)",
        data=rewritten,
        file_name="academic_humanized.txt",
        mime="text/plain"
    )
