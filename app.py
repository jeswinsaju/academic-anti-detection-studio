import os
import re
import math
import requests
import streamlit as st

# ==========================================
# 1. EXTREME HUMANIZER PROMPT (HIGH PERPLEXITY)
# ==========================================

PROMPT_HUMANIZE = """You are a senior academic writer known for an unconventional, distinct writing style. Your task is to completely rewrite the input text so it passes human writing evaluation and advanced AI detectors (GPTZero, Turnitin).

CRITICAL STYLISTIC INSTRUCTIONS:
1. EXTREME BURSTINESS: Force massive contrast in sentence structures. 
   - Write short 3-6 word sentences. 
   - Follow them with long, complex 30+ word sentences featuring parenthetical breaks, em-dashes (—), or subordinate clauses.
2. PERPLEXITY & PHRASING: Avoid typical LLM phrasing. Use rare academic terminology, active voice, and unexpected sentence openers (e.g., starting sentences with "Granted,", "Conversely,", or prepositional phrases).
3. NO ARTIFICIAL TRANSITIONS: Never use "Furthermore,", "Moreover,", "In conclusion,", "It is essential to note", "Additionally,".
4. FORBIDDEN WORDS: Completely avoid: "delve", "testament", "tapestry", "pivotal", "beacon", "fostering", "seamlessly", "robust", "interplay", "realm", "ecosystem", "underscores", "highlighting".
5. CITATIONS & DATA: Preserve all citations [e.g., Smith et al., 2023], numbers, and technical terms verbatim.
6. OUTPUT ONLY the final rewritten text. No introductory remarks.
"""

PROMPT_PLAGIARISM_REMOVE = """You are a deep structural paraphrasing engine. Rewrite the following academic text to eliminate all verbatim string matching and robotic syntax.

Instructions:
1. Invert sentence clauses completely (place the dependent clause at the beginning).
2. Replace generic verbs with precise, context-specific academic verbs.
3. Split monotonous paragraphs into varied structural rhythms.
4. Keep all citations, formulas, and statistical values untouched.
5. OUTPUT ONLY the refactored text.
"""

# ==========================================
# 2. POST-PROCESSING STRUCTURAL MUTATOR
# ==========================================

def mutate_sentence_structure(text: str) -> str:
    """
    Programmatically cleans AI markers and adds structural variation.
    """
    # Remove AI intro fillers
    text = re.sub(r"^(Here is|Below is|Sure|Here's)[\s\S]*?:\n*", "", text, flags=re.IGNORECASE)
    
    # Remove banned robotic transitions
    banned_patterns = [
        r"\bFurthermore,\b", r"\bMoreover,\b", r"\bIn conclusion,\b",
        r"\bIt is important to note that\b", r"\bTestament to\b",
        r"\bDelve into\b", r"\bIn the realm of\b", r"\bSeamlessly integrated?\b"
    ]
    for pattern in banned_patterns:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE)

    # Clean multi-spaces
    text = re.sub(r" +", " ", text)
    return text.strip()

# ==========================================
# 3. TEXT CADENCE & BURSTINESS ANALYZER
# ==========================================

def analyze_text_cadence(text: str) -> dict:
    sentences = [s.strip() for s in re.split(r'[.!?]+', text) if s.strip()]
    if not sentences:
        return {"word_count": 0, "avg_len": 0, "std_dev": 0, "risk": "High"}

    lengths = [len(re.findall(r'\b\w+\b', s)) for s in sentences if len(re.findall(r'\b\w+\b', s)) > 0]
    if not lengths:
        return {"word_count": 0, "avg_len": 0, "std_dev": 0, "risk": "High"}

    total_words = sum(lengths)
    avg_len = total_words / len(lengths)
    variance = sum((x - avg_len) ** 2 for x in lengths) / len(lengths)
    std_dev = math.sqrt(variance)

    # Assess Risk based on Standard Deviation (Burstiness)
    if std_dev >= 10.0:
        risk = "Low Risk (Human-like Variation)"
    elif std_dev >= 6.5:
        risk = "Moderate Risk (Slightly Uniform)"
    else:
        risk = "High Risk (Likely Triggers AI Detectors)"

    return {
        "word_count": total_words,
        "avg_len": round(avg_len, 1),
        "std_dev": round(std_dev, 2),
        "risk": risk
    }

# ==========================================
# 4. GROQ LLM EXECUTION ENGINE
# ==========================================

def process_text_groq(text: str, mode: str, api_key: str, model_name: str) -> str:
    system_prompt = PROMPT_HUMANIZE if mode == "Humanize (AI Bypass)" else PROMPT_PLAGIARISM_REMOVE
    
    headers = {
        "Authorization": f"Bearer {api_key.strip()}",
        "Content-Type": "application/json"
    }
    
    # Advanced parameters tuned specifically for high-perplexity generation
    payload = {
        "model": model_name.strip(),
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Source Text to Rewrite:\n{text}"}
        ],
        "temperature": 1.15,       # Higher temperature increases token unpredictability
        "top_p": 0.85,              # Nucleus sampling forces less conventional word sequences
        "presence_penalty": 0.8,    # Penalizes words that have already appeared
        "frequency_penalty": 0.7    # Reduces repetitive sentence patterns
    }
    
    response = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=45)
    
    if response.status_code != 200:
        raise Exception(f"Groq API Error ({response.status_code}): {response.text}")

    raw_output = response.json()["choices"][0]["message"]["content"]
    return mutate_sentence_structure(raw_output)

# ==========================================
# 5. STREAMLIT INTERFACE
# ==========================================

def main():
    st.set_page_config(page_title="Academic Anti-Detection Studio", layout="wide")
    st.title("🎓 Academic Anti-Detection Studio (High-Perplexity Engine)")

    st.sidebar.header("Backend Configuration")
    api_key = st.sidebar.text_input("Groq API Key", type="password", value=os.environ.get("GROQ_API_KEY", ""))
    
    model_name = st.sidebar.selectbox(
        "Model Target",
        [
            "openai/gpt-oss-120b",
            "openai/gpt-oss-20b",
            "canopylabs/orpheus-v1-english"
        ]
    )

    mode = st.sidebar.selectbox(
        "Refactoring Mode",
        ["Humanize (AI Bypass)", "Plagiarism Removal (Clause Flipping)"]
    )

    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Source Draft")
        input_text = st.text_area("Paste draft here...", height=380)
        run_btn = st.button("Humanize & Refactor Text", type="primary", use_container_width=True)

    with col2:
        st.subheader("Humanized Output")
        output_placeholder = st.empty()

    if run_btn:
        if not input_text.strip():
            st.warning("Please enter text to process.")
            return

        if not api_key:
            st.error("Missing Groq API Key.")
            return

        with st.spinner("Refactoring sentence structures for AI bypass..."):
            try:
                result = process_text_groq(input_text, mode, api_key, model_name)
                output_placeholder.text_area("Bypass Ready Output", value=result, height=380)
                
                # Metrics Evaluation
                metrics = analyze_text_cadence(result)
                st.markdown("---")
                st.subheader("📊 Output Structural Analysis")
                
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Word Count", metrics["word_count"])
                m2.metric("Avg Sentence Length", f"{metrics['avg_len']} words")
                m3.metric("Burstiness (StdDev)", metrics["std_dev"], help="Aim for > 10.0 for passing Turnitin/GPTZero")
                
                if "Low Risk" in metrics["risk"]:
                    m4.success(metrics["risk"])
                elif "Moderate" in metrics["risk"]:
                    m4.warning(metrics["risk"])
                else:
                    m4.error(metrics["risk"])

            except Exception as e:
                st.error(f"Error: {str(e)}")

if __name__ == "__main__":
    main()
