import re
from difflib import SequenceMatcher

import streamlit as st
from groq import Groq

try:
    import textstat
except ImportError:
    textstat = None


# --------------------------------------------------
# PAGE CONFIG
# --------------------------------------------------

st.set_page_config(
    page_title="Academic Editor",
    page_icon="📚",
    layout="wide"
)


# --------------------------------------------------
# GROQ CLIENT
# --------------------------------------------------

if "GROQ_API_KEY" not in st.secrets:
    st.error("Missing GROQ_API_KEY in Streamlit secrets.")
    st.stop()

client = Groq(
    api_key=st.secrets["GROQ_API_KEY"]
)


# --------------------------------------------------
# MODEL DISCOVERY
# --------------------------------------------------

@st.cache_data(ttl=3600)
def get_models():
    fallback = ["llama-3.1-8b-instant"]

    try:
        models = client.models.list()

        available = []

        for model in models.data:
            model_id = model.id.lower()

            if any(
                x in model_id
                for x in ["whisper", "tts", "embed", "guard"]
            ):
                continue

            available.append(model.id)

        return available if available else fallback

    except Exception:
        return fallback


# --------------------------------------------------
# CITATION LOCKER
# --------------------------------------------------

def lock_citations(text):
    mapping = {}
    counter = 0

    def repl(match):
        nonlocal counter

        token = f"REFTOKEN{counter}X"
        mapping[token] = match.group(0)

        counter += 1
        return token

    locked = re.sub(
        r"\[\d+(?:[-–]\d+)?\]",
        repl,
        text
    )

    return locked, mapping


def restore_citations(text, mapping):
    for token, citation in mapping.items():
        text = text.replace(token, citation)

    return text


# --------------------------------------------------
# NUMBER LOCKER
# --------------------------------------------------

def lock_numbers(text):
    mapping = {}
    counter = 0

    def repl(match):
        nonlocal counter

        token = f"NUMTOKEN{counter}X"
        mapping[token] = match.group(0)

        counter += 1
        return token

    pattern = r"(?<![A-Za-z_])\d+(?:\.\d+)?%?(?![A-Za-z_])"

    locked = re.sub(
        pattern,
        repl,
        text
    )

    return locked, mapping


def restore_numbers(text, mapping):
    for token, value in mapping.items():
        text = text.replace(token, value)

    return text


# --------------------------------------------------
# PASS 1
# --------------------------------------------------

def rewrite_pass1(text, model):
    prompt = f"""
Preserve all placeholder tokens exactly.

Requirements:
- Preserve meaning.
- Preserve findings.
- Preserve technical content.
- Preserve all placeholder tokens exactly.

Rewrite using clear academic English.

TEXT:

{text}
"""

    response = client.chat.completions.create(
        model=model,
        temperature=0.6,
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ]
    )

    return response.choices[0].message.content


# --------------------------------------------------
# PASS 2
# --------------------------------------------------

def rewrite_pass2(text, model):
    prompt = f"""
Preserve all placeholder tokens exactly.

Revise the following academic text.

Requirements:
- Preserve meaning.
- Preserve findings.
- Preserve technical accuracy.
- Preserve all placeholders exactly.
- Improve readability.
- Improve organization.
- Reduce repetition.
- Improve flow and clarity.

Return only the revised text.

TEXT:

{text}
"""

    response = client.chat.completions.create(
        model=model,
        temperature=0.8,
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ]
    )

    return response.choices[0].message.content


# --------------------------------------------------
# METRICS
# --------------------------------------------------

def similarity_score(original, rewritten):
    return round(
        SequenceMatcher(
            None,
            original,
            rewritten
        ).ratio() * 100,
        2
    )


def originality_score(original, rewritten):
    return round(
        100 - similarity_score(original, rewritten),
        2
    )


def readability_score(text):
    if textstat is None:
        return "N/A"

    try:
        return round(
            textstat.flesch_reading_ease(text),
            2
        )
    except Exception:
        return "N/A"


# --------------------------------------------------
# UI
# --------------------------------------------------

st.title("📚 Academic Editor")

st.markdown(
    """
### Features

✅ Citation preservation

✅ Statistics preservation

✅ Number preservation

✅ Groq-powered academic editing

✅ Two-pass revision workflow

✅ Similarity analysis

✅ Readability analysis

✅ TXT export
"""
)

col1, col2 = st.columns(2)

with col1:
    revision_mode = st.selectbox(
        "Revision Mode",
        ["Standard", "Enhanced"]
    )

with col2:
    models = get_models()

    selected_model = st.selectbox(
        "Groq Model",
        models
    )

input_text = st.text_area(
    "Paste Academic Text",
    height=320
)


# --------------------------------------------------
# PROCESS BUTTON
# --------------------------------------------------

if st.button("✨ Edit Text"):

    if not input_text.strip():
        st.warning("Please enter some text.")

    else:
        try:
            with st.spinner("Editing text..."):

                locked_text, citation_map = lock_citations(
                    input_text
                )

                locked_text, number_map = lock_numbers(
                    locked_text
                )

                first_pass = rewrite_pass1(
                    locked_text,
                    selected_model
                )

                second_pass = rewrite_pass2(
                    first_pass,
                    selected_model
                )

                if revision_mode == "Enhanced":
                    second_pass = rewrite_pass2(
                        second_pass,
                        selected_model
                    )

                final_text = restore_numbers(
                    second_pass,
                    number_map
                )

                final_text = restore_citations(
                    final_text,
                    citation_map
                )

                st.session_state["original"] = input_text
                st.session_state["edited"] = final_text

        except Exception as e:
            st.error(f"Error: {e}")


# --------------------------------------------------
# RESULTS
# --------------------------------------------------

if "original" in st.session_state and "edited" in st.session_state:

    original_text = st.session_state["original"]
    edited_text = st.session_state["edited"]

    similarity = similarity_score(
        original_text,
        edited_text
    )

    originality = originality_score(
        original_text,
        edited_text
    )

    readability = readability_score(
        edited_text
    )

    st.divider()

    m1, m2, m3 = st.columns(3)

    with m1:
        st.metric(
            "Similarity",
            f"{similarity}%"
        )

    with m2:
        st.metric(
            "Originality",
            f"{originality}%"
        )

    with m3:
        st.metric(
            "Readability",
            readability
        )

    st.divider()

    left, right = st.columns(2)

    with left:
        st.subheader("Original")

        st.text_area(
            "Original Text",
            value=original_text,
            height=450,
            disabled=True
        )

    with right:
        st.subheader("Edited")

        st.text_area(
            "Edited Text",
            value=edited_text,
            height=450
        )

    st.download_button(
        label="📥 Download TXT",
        data=edited_text,
        file_name="academic_editor_output.txt",
        mime="text/plain"
    )
