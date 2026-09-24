import streamlit as st
import re
from difflib import SequenceMatcher
from groq import Groq

try:
    import textstat
except:
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
# GROQ CLIENT
# -----------------------------

client = Groq(
    api_key=st.secrets["GROQ_API_KEY"]
)

# -----------------------------
# CITATION LOCKING
# -----------------------------

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

    for token, citation in mapping.items():
        text = text.replace(
            token,
            citation
        )

    return text


# -----------------------------
# NUMBER LOCKING
# -----------------------------

def lock_numbers(text):

    pattern = r"\d+(?:\.\d+)?%?"

    nums = re.findall(
        pattern,
        text
    )

    mapping = {}

    for i, num in enumerate(nums):

        token = f"__NUM_{i}__"

        mapping[token] = num

        text = text.replace(
            num,
            token,
            1
        )

    return text, mapping


def restore_numbers(text, mapping):

    for token, value in mapping.items():
        text = text.replace(
            token,
            value
        )

    return text


# -----------------------------
# LLM REWRITE
# -----------------------------

def rewrite_text(text, mode):

    prompts = {

        "Light": """
Rewrite lightly.

Requirements:
- Preserve citations exactly.
- Preserve numbers exactly.
- Preserve findings.
- Improve readability.
- Keep technical meaning unchanged.
""",

        "Medium": """
Rewrite academically.

Requirements:
- Preserve citations exactly.
- Preserve percentages exactly.
- Preserve findings exactly.
- Reduce textual similarity.
- Vary sentence lengths.
- Improve readability.
- Use natural academic writing.
- Avoid repetitive AI-style wording.
""",

        "Aggressive": """
Rewrite extensively.

Requirements:
- Preserve citations exactly.
- Preserve statistics exactly.
- Preserve findings exactly.

Rewrite by:
- Reorganizing ideas.
- Splitting long sentences.
- Combining short sentences.
- Using academic storytelling.
- Increasing burstiness.
- Reducing repetitive AI patterns.
- Minimizing textual similarity while preserving meaning.
"""
    }

    completion = client.chat.completions.create(
        model="llama3-70b-8192",
        temperature=0.9,
        max_tokens=4096,
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

    return completion.choices[0].message.content


# -----------------------------
# SIMILARITY
# -----------------------------

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
        100 -
        similarity_score(
            original,
            rewritten
        ),
        2
    )


# -----------------------------
# READABILITY
# -----------------------------

def readability_score(text):

    if textstat is None:
        return "N/A"

    try:

        return round(
            textstat.flesch_reading_ease(text),
            2
        )

    except:

        return "N/A"


# -----------------------------
# UI
# -----------------------------

st.title("📚 Academic Humanizer Pro")

st.markdown("""
### Features

✅ Citation Preservation

✅ Numerical Preservation

✅ Research Finding Preservation

✅ Llama 3.3 (70B) Rewriting

✅ Similarity Analysis

✅ Readability Analysis

✅ Download Output
""")


rewrite_mode = st.selectbox(
    "Rewrite Strength",
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


if st.button("✨ Rewrite Text"):

    if not input_text.strip():

        st.warning(
            "Please enter text."
        )

    else:

        with st.spinner(
            "Rewriting text..."
        ):

            text, citation_map = lock_citations(
                input_text
            )

            text, number_map = lock_numbers(
                text
            )

            rewritten = rewrite_text(
                text,
                rewrite_mode
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


# -----------------------------
# RESULTS
# -----------------------------

if (
    "original" in st.session_state and
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

    readability = readability_score(
        rewritten
    )

    st.divider()

    c1, c2, c3 = st.columns(3)

    with c1:
        st.metric(
            "Similarity",
            f"{similarity}%"
        )

    with c2:
        st.metric(
            "Originality",
            f"{originality}%"
        )

    with c3:
        st.metric(
            "Readability",
            readability
        )

    st.divider()

    left, right = st.columns(2)

    with left:

        st.subheader(
            "Original"
        )

        st.text_area(
            "",
            original,
            height=450
        )

    with right:

        st.subheader(
            "Rewritten"
        )

        st.text_area(
            "",
            rewritten,
            height=450
        )

    st.download_button(
        "📥 Download TXT",
        rewritten,
        file_name="humanized_text.txt",
        mime="text/plain"
    )
