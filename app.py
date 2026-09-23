import os
import re
import math
import random
import requests
import streamlit as st

# ==========================================
# 1. ADVANCED AI BYPASS PROMPTS
# ==========================================

PROMPT_PASS_1 = """You are a top-tier academic editor specializing in high-perplexity prose. 
Your task is to completely rewrite the provided academic text so that no two consecutive sentences follow the same grammatical structure.

STRICT LINGUISTIC CONSTRAINTS:
1. BURSTINESS EXTREMES: Alternate aggressively between very brief statements (3 to 6 words) and extended, multi-clause academic sentences (28+ words).
2. SYNTACTIC VARIATION: Begin sentences with prepositional phrases, dependent clauses, or single adverbs (e.g., "Granted,", "Historically,", "Crucially,"). Never start two consecutive sentences with the subject.
3. FORBIDDEN AI TRANSITIONS: NEVER use: "Furthermore", "Moreover", "In conclusion", "Additionally", "It is important to note", "Consequently", "Thus", "In summary".
4. FORBIDDEN AI VOCABULARY: Do NOT use: "delve", "testament", "tapestry", "pivotal", "beacon", "fostering", "seamlessly", "robust", "interplay", "realm", "ecosystem", "underscores", "highlighting".
5. PRESERVE ACCURACY: Keep all academic citations [e.g., Smith et al., 2023], mathematical variables, figures, and technical terms 100% intact.
6. Return ONLY the rewritten text without introductions or commentary.
"""

PROMPT_PASS_2 = """You are an expert humanizer tasked with introducing human writing quirks and breaking structural predictability.

INSTRUCTIONS:
1. INSERT EM-DASHES: Integrate 1–2 em-dashes (—) into complex thoughts to interrupt sentence flow naturally.
2. INJECT RHETORICAL BREAKS: Convert one passive sentence into an active, direct observation or rhetorical reflection (e.g., "Why does this matter?", "Consider the alternative.").
3. SHORT FRAGMENTS: Break up one uniform paragraph by inserting a standalone 3-to-5 word emphatic sentence.
4. PRESERVE CITATIONS: Keep all citations and statistical data exact.
5. Return ONLY the final output without preamble.
"""

# ==========================================
# 2. ALGORITHMIC POST-PROCESSING (PYTHON)
# ==========================================

def post_process_mutator(text: str) -> str:
    """
    Programmatically strips remaining robotic artifacts and enforces
    structural unpredictability at the code level.
    """
    # Remove LLM meta-talk
    text = re.sub(r"^(Here is|Below is|Sure|Here's)[\s\S]*?:\n*", "", text, flags=re.IGNORECASE)
    
    # Banned transition removal
    banned_patterns = [
        r"\bFurthermore,\b", r"\bMoreover,\b", r"\bIn conclusion,\b",
        r"\bIt is important to note that\b", r"\bTestament to\b",
        r"\bDelve into\b", r"\bIn the realm of\b", r"\bSeamlessly integrated?\b",
        r"\bAdditionally,\b", r"\bConsequently,\b"
    ]
    for pattern in banned_patterns:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE)

    # Clean double spaces
    text = re.sub(r" +", " ", text)
    
    # Programmatic sentence structure randomization (Split long uniform runs)
    sentences = re.split(r'(?<=[.!?]) +', text.strip())
    processed_sentences = []
    
    for idx, sentence in enumerate(sentences):
        words = sentence.split()
        # If two long sentences occur back-to-back, randomly inject a comma-clause break or dash
        if len(words) > 22 and idx > 0 and len(sentences[idx-1].split()) > 20:
            if "—" not in sentence and len(words) > 10:
                midpoint = len(words) // 2
                words.insert(midpoint, "—")
                sentence = " ".join(words)
        processed_sentences.append(sentence)

    return " ".join(processed_sentences).strip()

# ==========================================
# 3. BURSTINESS & METRICS ANALYZER
# ==========================================

def analyze_cadence(text: str) -> dict:
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

    # Standard Deviation >= 9.5 indicates strong sentence length variation (Burstiness)
    if std_dev >= 9.5:
        risk = "0% - 15% (Human Equivalent)"
    elif std_dev >= 6.5:
        risk = "25% - 45% (Moderate Risk)"
    else:
        risk = "60%+ (High AI Risk)"

    return {
        "word_count": total_words,
        "avg_len": round(avg_len, 1),
        "std_dev": round(std_dev, 2),
        "risk": risk
    }

# ==========================================
# 4. TWO-PASS LLM PIPELINE
# ==========================================

def execute_groq_request(messages: list, api_key: str, model_name: str, temp: float) -> str:
    headers = {
        "Authorization": f"Bearer {api_key.strip()}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": model_name.strip(),
        "messages": messages,
        "temperature": temp,        # High temperature forces token unpredictability
        "top_p": 0.82,               # Nucleus sampling filters out standard robotic sequences
        "presence_penalty": 0.95,   # Strongly discourages repeated token patterns
        "frequency_penalty": 0.85   # Strongly reduces phrase repetition
    }
    
    response = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers=headers,
        json=payload,
        timeout=60
    )
    
    if response.status_code != 200:
        raise Exception(f"Groq API Error ({response.status_code}): {response.text}")

    return response.json()["choices"][0]["message"]["content"]

def process_two_pass_humanize(text: str, api_key: str, model_name: str) -> str:
    # Pass 1: High-Perplexity Paraphrase
    pass1_messages = [
        {"role": "system", "content": PROMPT_PASS_1},
        {"role": "user", "content": f"Source Text:\n{text}"}
    ]
    pass1_output = execute_groq_request(pass1_messages, api_key, model_name, temp=1.2)

    # Pass 2: Syntactic & Rhythm Humanization
    pass2_messages = [
        {"role": "system", "content": PROMPT_PASS_2},
        {"role": "user", "content": f"Draft Text:\n{pass1_output}"}
    ]
    pass2_output = execute_groq_request(pass2_messages, api_key, model_name, temp=1.0)

    # Python Algorithmic Mutation
    final_output = post_process_mutator(pass2_output)
    return final_output

# ==========================================
# 5. STREAMLIT INTERFACE
# ==========================================

def main():
    st.set_page_config(page_title="Academic Anti-Detection Studio", layout="wide")
    st.title("🎓 Academic Anti-Detection Studio (Two-Pass Pipeline)")

    st.sidebar.header("Configuration")
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
        st.subheader("Source Text")
        input_text = st.text_area("Paste draft here...", height=400)
        run_btn = st.button("Humanize & Bypass AI Detectors", type="primary", use_container_width=True)

    with col2:
        st.subheader("Humanized Output (Bypass Ready)")
        output_placeholder = st.empty()

    if run_btn:
        if not input_text.strip():
            st.warning("Please enter text to process.")
            return

        if not api_key:
            st.error("Missing Groq API Key.")
            return

        with st.spinner("Running Two-Pass Humanization Pipeline..."):
            try:
                result = process_two_pass_humanize(input_text, api_key, model_name)
                output_placeholder.text_area("Final Output", value=result, height=400)
                
                # Metrics Evaluation
                metrics = analyze_cadence(result)
                st.markdown("---")
                st.subheader("📊 Output Structural Metrics")
                
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Word Count", metrics["word_count"])
                m2.metric("Avg Sentence Length", f"{metrics['avg_len']} words")
                m3.metric("Burstiness (StdDev)", metrics["std_dev"], help="Aim for > 9.5 for Turnitin/GPTZero bypass")
                
                if "0%" in metrics["risk"]:
                    m4.success(f"**Predicted AI Score:**\n{metrics['risk']}")
                elif "25%" in metrics["risk"]:
                    m4.warning(f"**Predicted AI Score:**\n{metrics['risk']}")
                else:
                    m4.error(f"**Predicted AI Score:**\n{metrics['risk']}")

            except Exception as e:
                st.error(f"Error: {str(e)}")

if __name__ == "__main__":
    main()
