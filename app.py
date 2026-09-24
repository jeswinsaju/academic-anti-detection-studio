import streamlit as st
import re
from difflib import SequenceMatcher
from groq import Groq

try:
    import textstat
except ImportError:
    textstat = None

# ----------------------------------
# CONFIG
# ----------------------------------

st.set_page_config(
    page_title="Academic Editor",
    page_icon="📚",
    layout="wide"
)

# ----------------------------------
# GROQ
# ----------------------------------

if "GROQ_API_KEY" not in st.secrets:
    st.error("Missing GROQ_API_KEY in Streamlit Secrets")
    st.stop()

client = Groq(
    api_key=st.secrets["GROQ_API_KEY"]
)

# ----------------------------------
# MODEL LIST
# ----------------------------------

@st.cache_data(ttl=3600)
def get_models():

    fallback = [
        "llama-3.1-8b-instant"
    ]

    try:

        models = client.models.list()

        available = []

        for model in models.data:

            name = model.id.lower()

            if any(
                x in name
                for x in [
                    "whisper",
                    "embed",
                    "tts",
                    "guard"
                ]
            ):
                continue

            available.append(model.id)

        return available if available else fallback

    except Exception:
        return fallback

# ----------------------------------
# CITATION LOCKER
# ----------------------------------

def lock_citations(text):

    mapping = {}

    counter = 0

    def repl(match):

        nonlocal counter

        token = f"REFTOKEN{counter}X"

        mapping[token] = match.group(0)

        counter += 1

        return token

    text = re.sub(
        r"\[\d+(?:[-–]\d+)?\]",
        repl,
        text
    )

    return text, mapping


def restore_citations(text, mapping):

    for token, citation in mapping.items():

        text = text.replace(
            token,
            citation
        )

    return text

# ----------------------------------
# NUMBER LOCKER
# ----------------------------------

def lock_numbers(text):

    mapping = {}

    counter = 0

    def repl(match):

        nonlocal counter

        token = f"NUMTOKEN{counter}X"

        mapping[token] = match.group(0)

        counter += 1

        return token

    pattern = r"(?<![a-zA-Z_])\d+(?:\.\d+)?%?(?![a-zA-Z_])"

    text = re.sub(
        pattern,
        repl,
        text
    )

    return text, mapping


def restore_numbers(text, mapping):

    for token, value in mapping.items():

        text = text.replace(
            token,
            value
        )

    return text

# ----------------------------------
# PASS 1
# ----------------------------------

def rewrite_pass1(text, model):

    prompt = f"""
Preserve every placeholder token exactly.

Requirements:
- Preserve meaning.
- Preserve findings.
- Preserve technical content.
- Preserve all placeholder tokens.

Rewrite in clear academic English.

Text:

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

# ----------------------------------
# PASS 2
# ----------------------------------

def rewrite_pass2(text, model):

    prompt = f"""
Preserve every placeholder token exactly.

Revise the academic text below.

Requirements:
- Preserve meaning.
- Preserve findings.
- Preserve placeholder tokens.
- Improve readability.
- Improve flow.
- Improve paragraph organization.
- Reduce repetition.
- Vary sentence structure.

Return only the revised text.

Text:

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

# ----------------------------------
# METRICS
# ----------------------------------

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
        100 - similarity_score(
            original,
            rewritten
        ),
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

# ----------------------------------
# UI
# ----------------------------------

st.title("📚 Academic Editor")

st.markdown("""
### Features

✅ Citation preservation

✅ Number/statistics preservation

✅ Groq-powered academic editing

✅ Two-pass revision workflow

✅ Similarity analysis

✅ Readability analysis

✅ TXT export
""")

col1, col2 = st.columns(2)

with col1:

    enhance_mode = st.selectbox(
        "Revision Mode",
        [
            "Standard",
            "Enhanced"
        ]
    )

with col2:

    available_models = get_models()

    selected_model = st.selectbox(
        "Groq Model",
        available_models
    )

input_text = st.text_area(
    "Paste Academic Text",
    height=300
)

# ----------------------------------
# PROCESS
# ----------------------------------

if st.button("✨ Edit Text"):

    if not input_text.strip():

        st.warning(
            "Please enter text."
        )

    else:

        try:

            with st.spinner("Editing..."):

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

                if enhance_mode == "Enhanced":

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

            st.error(f"Groq Error: {str(e)}")

# ----------------------------------
# RESULTS
# ----------------------------------

if (
    "original" in st.session_state
    and
    "edited" in st.
