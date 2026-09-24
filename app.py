import streamlit as st
import re
import random
from difflib import SequenceMatcher

try:
    import textstat
except ImportError:
    textstat = None


# ---------------------------------
# Citation & Number Protection
# ---------------------------------

def lock_citations(text):
    citations = re.findall(r"\[\d+(?:[-–]\d+)?\]", text)

    mapping = {}

    for i, citation in enumerate(citations):
        placeholder = f"__CIT_{i}__"
        mapping[placeholder] = citation
        text = text.replace(citation, placeholder, 1)

    return text, mapping


def restore_citations(text, mapping):
    for key, value in mapping.items():
        text = text.replace(key, value)

    return text


def lock_numbers(text):
    numbers = re.findall(r"\d+(?:\.\d+)?%?", text)

    mapping = {}

    for i, number in enumerate(numbers):
        placeholder = f"__NUM_{i}__"
        mapping[placeholder] = number
        text = text.replace(number, placeholder, 1)

    return text, mapping


def restore_numbers(text, mapping):
    for key, value in mapping.items():
        text = text.replace(key, value)

    return text


# ---------------------------------
# Humanizer
# ---------------------------------

def rewrite_phrases(text):
    replacements = {
        "However": [
            "Still",
            "Even so",
            "That said"
        ],
        "Furthermore": [
            "In addition",
            "Another observation is that",
            "More importantly"
        ],
        "Moreover": [
            "Beyond that",
            "Interestingly",
            "There's another perspective"
        ],
        "Recent studies": [
            "Recent findings",
            "Researchers have increasingly observed",
            "A growing body of evidence suggests"
        ],
        "At the same time": [
            "Meanwhile",
            "In parallel",
            "Still"
        ]
    }

    for phrase, options in replacements.items():
        text = re.sub(
            phrase,
            random.choice(options),
            text,
            flags=re.IGNORECASE
        )

    return text


def add_human_variation(text):
    sentences = re.split(
        r'(?<=[.!?])\s+',
        text
    )

    result = []

    injections = [
        "That matters.",
        "An interesting detail.",
        "Something worth noting.",
        "A small point, but an important one.",
        "Not perfect. Still useful."
    ]

    for sentence in sentences:
        if sentence.strip():

            result.append(sentence)

            if len(sentence.split()) > 22:
                if random.random() > 0.6:
                    result.append(
                        random.choice(injections)
                    )

    return " ".join(result)


def humanize_text(text):
    text = rewrite_phrases(text)
    text = add_human_variation(text)

    return text


# ---------------------------------
# Analysis
# ---------------------------------

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


def detect_ai_phrases(text):
    patterns = [
        "Furthermore",
        "Moreover",
        "In conclusion",
        "It is important to note",
        "Recent studies suggest",
        "Consequently",
        "Notably"
    ]

    found = []

    for pattern in patterns:
        if pattern.lower() in text.lower():
            found.append(pattern)

    return found


# ---------------------------------
# Streamlit UI
# ---------------------------------

st.set_page_config(
    page_title="Academic Humanizer",
    page_icon="📚",
    layout="wide"
)

st.title("📚 Academic Humanizer")

st.markdown(
    """
### Preserve

- Citations
- Statistics
- Research findings

### Improve

- Readability
- Narrative flow
- Human-like writing style
"""
)

tab1, tab2 = st.tabs(
    ["Rewrite", "Analysis"]
)

# ---------------------------------
# Rewrite Tab
# ---------------------------------

with tab1:

    input_text = st.text_area(
        "Paste Academic Text",
        height=350
    )

    rewrite_level = st.selectbox(
        "Rewrite Strength",
        [
            "Light",
            "Medium",
            "Aggressive"
        ]
    )

    if st.button("✨ Humanize"):

        if input_text.strip():

            text, citation_map = lock_citations(
                input_text
            )

            text, number_map = lock_numbers(
                text
            )

            if rewrite_level == "Light":
                rewritten = humanize_text(text)

            elif rewrite_level == "Medium":
                rewritten = humanize_text(
                    humanize_text(text)
                )

            else:
                rewritten = humanize_text(
                    humanize_text(
                        humanize_text(text)
                    )
                )

            rewritten = restore_numbers(
                rewritten,
                number_map
            )

            rewritten = restore_citations(
                rewritten,
                citation_map
            )

            st.session_state["original"] = input_text
            st.session_state["rewritten"] = rewritten

            st.subheader("Humanized Output")

            st.write(rewritten)

            st.download_button(
                label="📥 Download TXT",
                data=rewritten,
                file_name="humanized_text.txt",
                mime="text/plain"
            )

        else:
            st.warning(
                "Please enter some text."
            )

# ---------------------------------
# Analysis Tab
# ---------------------------------

with tab2:

    if (
        "original" in st.session_state
        and
        "rewritten" in st.session_state
    ):

        original = st.session_state["original"]
        rewritten = st.session_state["rewritten"]

        similarity = similarity_score(
            original,
            rewritten
        )

        originality = originality_score(
            original,
            rewritten
        )

        reading_score = readability(
            rewritten
        )

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
                reading_score
            )

        st.progress(
            min(int(originality), 100)
        )

        st.subheader("AI Phrase Detection")

        phrases = detect_ai_phrases(
            rewritten
        )

        if phrases:

            for phrase in phrases:
                st.warning(
                    f"Detected: {phrase}"
                )

        else:
            st.success(
                "No common AI-style phrases detected."
            )

    else:
        st.info(
            "Generate a rewritten version first."
        )
