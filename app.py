import streamlit as st
import re
from difflib import SequenceMatcher
from groq import Groq

try:
    import textstat
except:
    textstat = None


# --------------------------------------------------
# CONFIG
# --------------------------------------------------

st.set_page_config(
    page_title="Academic Editor",
    page_icon="📚",
    layout="wide"
)

# --------------------------------------------------
# GROQ
# --------------------------------------------------

if "GROQ_API_KEY" not in st.secrets:
    st.error("Missing GROQ_API_KEY")
    st.stop()

client = Groq(
    api_key=st.secrets["GROQ_API_KEY"]
)


@st.cache_data(ttl=3600)
def get_models():

    fallback = [
        "llama-3.1-8b-instant",
        "llama-3.3-70b-versatile",
        "deepseek-r1-distill-llama-70b"
    ]

    try:

        models = client.models.list()

        names = []

        for m in models.data:

            if any(
                x in m.id.lower()
                for x in [
                    "whisper",
                    "embed",
                    "tts",
                    "guard"
                ]
            ):
                continue

            names.append(m.id)

        return names if names else fallback

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


# --------------------------------------------------
# PASS 1
# --------------------------------------------------

def rewrite_pass1(text, model):

    prompt = f"""
Preserve every placeholder token exactly.

Requirements:

- Preserve meaning.
- Preserve findings.
- Preserve technical content.
- Preserve all placeholder tokens.

Rewrite the text in concise academic English.

Text:

{text}
"""

    response = client.chat.completions.create(
        model=model,
        temperature=0.6,
        max_tokens=2000,
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
Preserve every placeholder token exactly.

Revise the following academic text.

Requirements:

- Preserve factual meaning.
- Preserve findings.
- Preserve placeholder tokens.
- Improve readability.
- Improve organization.
- Vary sentence structures.
- Reduce repetition.
- Improve flow between ideas.

Return only the revised text.

Text:

{text}
"""

    response = client.chat.completions.create(
        model=model,
        temperature=0.9,
        max_tokens=2000,
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

def similarity(original, rewritten):

    return round(
        SequenceMatcher(
            None,
            original,
            rewritten
        ).ratio() * 100,
        2
    )


def originality(original, rewritten):

    return round(
        100 - similarity(
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


# --------------------------------------------------
# UI
# --------------------------------------------------

st.title("📚 Academic Editor")

st.markdown(
"""
### Features

✅ Citation preservation

✅ Statistics preservation

✅ Two-pass academic 
