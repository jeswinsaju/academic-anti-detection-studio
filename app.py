import streamlit as st
import re
import random
from difflib import SequenceMatcher

try:
    import textstat
except:
    textstat = None


# -----------------------------
# Citation & Number Protection
# -----------------------------
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


# -----------------------------
# Humanizer
# -----------------------------
def rewrite_phrases(text):

    replacements = {

        "However": [
            "Still",
            "Even so",
            "That said"
        ],

        "Furthermore": [
            "Another observation is that",
            "In addition",
            "More importantly"
        ],

        "Moreover": [
            "Beyond that",
            "Interestingly",
            "There's another side to this"
        ],

        "Recent studies": [
            "Recent findings",
            "Researchers have increasingly observed",
            "A growing body of evidence suggests"
        ],

        "At the same time": [
            "Meanwhile",
            "Still",
            "In parallel"
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
        "A small point, but an important one.",
        "Not perfect. Still useful.",
        "Something worth noting."
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


# -----------------------------
# Analysis
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
    except:
        return "N/A"


def detect_ai_phrases(text):

    patterns = [

        "Furthermore",
        "Moreover",
        "In conclusion",
        "It is important to note",
        "Recent studies suggest",
        "Notably",
        "Consequently"
    ]

    found = []

    for pattern in patterns:

        if pattern.lower() in text.lower():
            found.append(pattern)

    return found


# -----------------------------
# Streamlit UI
# -----------------------------
st.set_page_config(
    page_title="Academic Humanizer",
    page_icon="📚",
    layout="wide"
)

st.title("📚 Academic Humanizer")

st.markdown("""
Preserve:
- Citations
- Statistics
- Research findings

Improve:
- Readability
-
