import streamlit as st
import re
from difflib import SequenceMatcher
from openai import OpenAI

try:
    import textstat
except ImportError:
    textstat = None


# --------------------------------
# CONFIG
# --------------------------------

st.set_page_config(
    page_title="Academic Humanizer",
    page_icon="📚",
    layout="wide"
)

client = OpenAI(
    api_key=st.secrets["OPENAI_API_KEY"]
)

# --------------------------------
# CITATION LOCKING
# --------------------------------

def lock_citations(text):

    citations = re.findall(
        r"\[\d+(?:[-–]\d+)?\]",
        text
    )

    mapping = {}

    for i, citation in enumerate(citations):

        token = f"__CIT_{i}__"

        mapping[token] = citation

        text = text.replace(
            citation,
            token,
            1
        )

    return text, mapping


def restore_citations(text, mapping):

    for k, v in mapping.items():
        text = text.replace(k, v)

    return text


# --------------------------------
# NUMBER LOCKING
# --------------------------------

def lock_numbers(text):

    pattern = r"\d+(?:\.\d+)?%?"

    numbers = re.findall(
        pattern,
        text
    )

    mapping = {}

    for i, number in enumerate(numbers):

        token = f"__NUM_{i}__"

        mapping[token] = number

        text = text.replace(
            number,
            token,
            1
        )

    return text, mapping


def restore_numbers(text, mapping):

    for k, v in mapping.items():
        text = text.replace(k, v)

    return text


# --------------------------------
# LLM REWRITE
# --------------------------------

def llm_rewrite(text, mode):

    prompts = {

        "Light": """
Rewrite lightly.

Requirements:
- Preserve citations exactly
- Preserve numbers exactly
- Preserve statistics exactly
- Preserve findings exactly
- Improve readability
""",

        "Medium": """
Rewrite academically.

Requirements:
- Preserve citations exactly
- Preserve numerical values exactly
- Preserve findings
- Vary sentence structure
- Reduce textual similarity
- Improve flow
- Use natural academic language
- Reduce repetitive AI-style phrases
""",

        "Aggressive": """
Rewrite extensively.

Requirements:
- Preserve citations exactly
- Preserve numerical values exactly
- Preserve findings exactly
- Reorganize ideas
- Rewrite sentence structures
- Mix short and long sentences
- Use academic storytelling
- Improve burstiness
- Improve readability
- Reduce textual similarity as much as possible
"""
    }

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0.9,
        messages=[
            {
                "role": "system",
                "content": prompts[mode]
            },
            {
                "role": "user",
                "content": text
            }
        ]
    )

    return response.choices[0].message.content


# --------------------------------
# ANALYSIS
# --------------------------------

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


def readability(text):

    if textstat is None:
        return "N/A"

    try:

        return round(
            textstat.flesch_reading_ease(text),
            2
        )

    except Exception:
        return "N/A"


# --------------------------------
# UI
# --------------------------------

st.title("📚 Academic Humanizer")

st.markdown("""
### Features

✅ Preserve citations

✅ Preserve statistics

✅ Preserve key findings

✅ GPT-powered rewriting

✅ Similarity analysis

✅ Readability analysis

✅ Download rewritten text
""")

rewrite_level = st.selectbox(
    "Rewrite Mode",
    [
        "Light",
        "Medium",
        "Aggressive"
    ]
)

input_text = st.text_area(
    "Paste Academic Text",
    height=300
)


if st.button("✨ Rewrite"):

    if not input_text.strip():

        st.warning(
            "Please enter text."
        )

    else:

        with st.spinner("Rewriting..."):

            text, citation_map = lock_citations(
                input_text
            )

            text, number_map = lock_numbers(
                text
            )

            rewritten = llm_rewrite(
                text,
                rewrite_level
            )

            rewritten = restore_numbers(
                rewritten,
                number_map
            )

            rewritten = restore_citations(
                rewritten,
                citation_map
            )

            st.session_state[
                "original"
            ] = input_text

            st.session_state[
                "rewritten"
            ] = rewritten


# --------------------------------
# RESULTS
# --------------------------------

if (
    "original" in st.session_state
    and
    "rewritten" in st.session_state
):

    original = st.session_state[
        "original"
    ]

    rewritten = st.session_state[
        "rewritten"
    ]

    similarity = similarity_score(
        original,
        rewritten
    )

    originality = originality_score(
        original,
        rewritten
    )

    reading = readability(
        rewritten
    )

    st.divider()

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            "Similarity",
            f"{similarity}%"
        )

    with col2:
        st.metric(
            "Originality",
            f"{originality}%"
        )

    with col3:
        st.metric(
            "Readability",
            reading
        )

    st.divider()

    c1, c2 = st.columns(2)

    with c1:

        st.subheader(
            "Original"
        )

        st.text_area(
            "",
            original,
            height=400
        )

    with c2:

        st.subheader(
            "Rewritten"
        )

        st.text_area(
            "",
            rewritten,
            height=400
        )

    st.download_button(
        "📥 Download TXT",
        rewritten,
        file_name="rewritten.txt",
        mime="text/plain"
    )
