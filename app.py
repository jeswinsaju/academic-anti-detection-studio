import os
import re
import math
import random
import requests
import streamlit as st

# ==========================================
# 1. CHECKLIST-DRIVEN SYSTEM PROMPT
# ==========================================

SYSTEM_PROMPT = """You are an academic copyeditor. Rewrite the text while strictly following these rules:

1. PURGE AI TRANSITIONS: Never use "Furthermore", "Moreover", "In conclusion", "Consequently", "Thus", "Additionally", "It is important to note".
2. PURGE AI VOCABULARY: Never use "delve", "tapestry", "pivotal", "underscore", "foster", "seamlessly", "robust", "interplay", "realm".
3. ACTIVE VOICE: Shift passive statements into direct, active assertions.
4. CITATIONS & DATA: Keep all academic citations [e.g., Smith et al., 2023], numbers, and technical terms 100% exact.
5. OUTPUT ONLY THE REWRITTEN TEXT: No intros, explanations, or quotes.
"""

# ==========================================
# 2. PYTHON RULE ENGINE (ENFORCES CHECKLIST)
# ==========================================

# Banned AI transition replacements
TRANSITION_MAP = {
    r"\bFurthermore,\b": "Beyond this,",
    r"\bMoreover,\b": "In addition,",
    r"\bConsequently,\b": "As a result,",
    r"\bIn conclusion,\b": "Ultimately,",
    r"\bIt is important to note that\b": "Noticeably,",
    r"\bAdditionally,\b": "Also,",
    r"\bThus,\b": "Hence,"
}

# Banned AI vocabulary replacements
VOCAB_MAP = {
    r"\bdelve into\b": "examine",
    r"\btapestry\b": "structure",
    r"\bpivotal\b": "key",
    r"\bunderscores\b": "highlights",
    r"\bfostering\b": "building",
    r"\bseamlessly\b": "smoothly",
    r"\brobust\b": "strong",
    r"\brealm\b": "area"
}

def enforce_checklist_rules(text: str) -> str:
    """
    Applies strict Python regex rules to strip AI tells and inject 
    structural burstiness directly into the text stream.
    """
    if not text:
        return ""

    # Rule A: Remove AI metadata/preamble
    text = re.sub(r"^```[\w]*\n", "", text)
    text = re.sub(r"\n```$", "", text)
    text = re.sub(r"^(Here is|Below is|Sure|Here's)[\s\S]*?:\n*", "", text, flags=re.IGNORECASE)

    # Rule B: Replace Banned AI Transitions
    for pattern, replacement in TRANSITION_MAP.items():
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

    # Rule C: Replace Banned Vocabulary
    for pattern, replacement in VOCAB_MAP.items():
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

    # Rule D: Inject Burstiness (Break uniform sentence lengths)
    sentences = re.split(r'(?<=[.!?]) +', text.strip())
    mutated_sentences = []

    for idx, sentence in enumerate(sentences):
        words = sentence.split()
        
        # If two consecutive sentences are medium-long (>16 words), force an em-dash interruption
        if len(words) > 16 and idx > 0 and len(sentences[idx-1].split()) > 15:
            if "—" not in sentence and len(words) >= 10:
                insert_pos = len(words) // 2
                words.insert(insert_pos, "—")
                sentence = " ".join(words)

        mutated_sentences.append(sentence)

    processed_text = " ".join(mutated_sentences)
    return re.sub(r" +", " ", processed_text).strip()

# ==========================================
# 3. CADENCE & METRICS ANALYZER
# ==========================================

def calculate_burstiness(text: str) -> dict:
    sentences = [s.strip() for s in re.split(r'[.!?]+', text) if s.strip()]
    if not sentences:
        return {"word_count": 0, "avg_len": 0, "std_dev": 0, "score": "Unknown"}

    lengths = [len(re.findall(r'\b\w+\b', s)) for s in sentences if len(re.findall(r'\b\w+\b', s)) > 0]
    if not lengths:
        return {"word_count": 0, "avg_len": 0, "std_dev": 0, "score": "Unknown"}

    total_words = sum(lengths)
    avg_len = total_words / len(lengths)
    variance = sum((x - avg_len) ** 2 for x in lengths) / len(lengths)
    std_dev = math.sqrt(variance)

    # High Standard Deviation (>8.0) means high burstiness (Human Signature)
    if std_dev >= 8.0:
        score = "0% - 15% (High Human Probability)"
    elif std_dev >= 5.0:
        score = "20% - 40% (Moderate Risk)"
    else:
        score = "60%+ (High AI Risk - Needs More Short Sentences)"

    return {
        "word_count": total_words,
        "avg_len": round(avg_len, 1),
        "std_dev": round(std_dev, 2),
        "score": score
    }

# ==========================================
# 4. API CALL ENGINE
# ==========================================

def run_groq_request(text: str, api_key: str, model_name: str) -> str:
    headers = {
        "Authorization": f"Bearer {api_key.strip()}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": model_name.strip(),
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Rewrite this draft:\n\n{text}"}
        ],
        "temperature": 0.85,
        "top_p": 0.9,
        "presence_penalty": 0.6,
        "frequency_penalty": 0.6
    }
    
    response = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers=headers,
        json=payload,
        timeout=60
    )
    
    if response.status_code != 200:
        raise Exception(f"API Connection Error ({response.status_code}): {response.text}")

    res_json = response.json()
    
    try:
        raw_output = res_json["choices"][0]["message"]["content"]
        # Apply the Python Rule Engine to guarantee the checklist is enforced
        final_output = enforce_checklist_rules(raw_output)
        return final_output
    except (KeyError, IndexError):
        raise Exception(f"Unexpected JSON structure returned: {res_json}")

# ==========================================
# 5. STREAMLIT INTERFACE
# ==========================================

def main():
    st.set_page_config(page_title="Checklist Anti-Detection Engine", layout="wide")
    st.title("🛡️ Checklist-Driven AI Bypass Studio")

    st.sidebar.header("Settings")
    api_key = st.sidebar.text_input("Groq API Key", type="password", value=os.environ.get("GROQ_API_KEY", ""))
    
    model_name = st.sidebar.selectbox(
        "Model Target",
        [
            "openai/gpt-oss-120b",
            "openai/gpt-oss-20b",
            "canopylabs/orpheus-v1-english"
        ]
    )

    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("1. Source Text")
        input_text = st.text_area("Paste draft here...", height=380)
        run_btn = st.button("Refactor & Enforce Checklist", type="primary", use_container_width=True)

    with col2:
        st.subheader("2. Humanized Output")
        # Direct container rendering avoids Streamlit widget key bugs
        output_container = st.empty()
        
        # Default placeholder box
        if "final_result" not in st.session_state:
            st.session_state["final_result"] = ""
            
        output_container.text_area("Final Result", value=st.session_state["final_result"], height=380, key="display_box")

    if run_btn:
        if not input_text.strip():
            st.warning("Please paste source text first.")
            return

        if not api_key.strip():
            st.error("Groq API Key missing.")
            return

        with st.spinner("Executing rule engine and high-perplexity refactoring..."):
            try:
                result = run_groq_request(input_text, api_key, model_name)
                st.session_state["final_result"] = result
                # Update output area immediately
                output_container.text_area("Final Result", value=result, height=380, key="display_box_updated")
                st.success("Checklist enforced and refactoring complete!")
            except Exception as e:
                st.error(f"Execution Error: {str(e)}")

    # Display Metrics if output exists
    if st.session_state["final_result"]:
        st.markdown("---")
        st.subheader("📊 Output Burstiness Evaluation")
        metrics = calculate_burstiness(st.session_state["final_result"])
        
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Word Count", metrics["word_count"])
        m2.metric("Avg Sentence Length", f"{metrics['avg_len']} words")
        m3.metric("Burstiness (StdDev)", metrics["std_dev"], help="Higher StdDev (>8.0) means higher sentence length variation.")
        
        if "0%" in metrics["score"]:
            m4.success(metrics["score"])
        elif "20%" in metrics["score"]:
            m4.warning(metrics["score"])
        else:
            m4.error(metrics["score"])

if __name__ == "__main__":
    main()
