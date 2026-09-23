import os
import re
import math
import requests
import streamlit as st

# ==========================================
# 1. SYSTEM PROMPTS FOR AI & PLAGIARISM BYPASS
# ==========================================

PROMPT_HUMANIZE = """You are an elite academic editor. Your task is to rewrite the input text to bypass structural AI detection tools (GPTZero, Turnitin AI) while preserving formal academic rigor.

Linguistic Rules:
1. MAXIMIZE BURSTINESS: Heavily vary sentence lengths. Alternate short, punchy statements (4-7 words) with complex, multi-clause sentences (25+ words).
2. HIGH PERPLEXITY SYNTAX: Avoid predictable phrasing. Use precise domain vocabulary rather than common LLM filler.
3. FORBIDDEN AI WORDS: Never use "delve", "testament", "tapestry", "pivotal", "beacon", "fostering", "seamlessly", "robust", "interplay", "realm", "ecosystem".
4. FORBIDDEN TRANSITIONS: Do NOT use "Furthermore,", "Moreover,", "In addition,", "Consequently,", or "In conclusion,". Connect logic directly through sentence structure.
5. PRESERVE ACCURACY: Keep all citations [e.g., [1], Smith et al., 2023], mathematical figures, and technical variables 100% intact.
6. OUTPUT ONLY the rewritten text without preambles, intros, or meta-commentary.
"""

PROMPT_PLAGIARISM_REMOVE = """You are a deep paraphrasing engine. Your task is to rewrite the text to eliminate verbatim string-matching plagiarism while bypassing AI detection.

Rules:
1. CLAUSE FLIPPING: Invert sentence structures (e.g., swap active and passive voice, or reverse dependent/independent clauses).
2. NO 5-WORD MATCHES: Ensure no sequence of 5 or more consecutive words matches the source text (excluding technical terms and citations).
3. CADENCE VARIATION: Combine short fragments into longer arguments and split uniform paragraphs.
4. CITATION LOCK: Keep all in-text references, data points, and proper nouns unchanged.
5. OUTPUT ONLY the processed academic text without meta-commentary or chat intros.
"""

# ==========================================
# 2. REGEX CLEANING FUNCTION
# ==========================================

def clean_ai_leftovers(text: str) -> str:
    """
    Scrubs remaining telltale robotic transitions and leftover AI conversational phrasing.
    """
    ai_patterns = [
        r"\bFurthermore,\b", 
        r"\bMoreover,\b", 
        r"\bIn conclusion,\b", 
        r"\bIt is important to note that\b",
        r"\bTestament to\b",
        r"\bDelve into\b",
        r"\bIn the realm of\b",
        r"\bSeamlessly integrated?\b",
        r"^Here is the rewritten text:\s*",
        r"^Here is the humanized version:\s*"
    ]
    
    cleaned_text = text
    for pattern in ai_patterns:
        cleaned_text = re.sub(pattern, "", cleaned_text, flags=re.IGNORECASE)
    
    cleaned_text = re.sub(r" +", " ", cleaned_text)
    return cleaned_text.strip()

# ==========================================
# 3. TEXT ANALYTICS ENGINE
# ==========================================

def analyze_text_cadence(text: str) -> dict:
    """
    Calculates sentence length metrics, burstiness index, and AI risk profile.
    """
    sentences = [s.strip() for s in re.split(r'[.!?]+', text) if s.strip()]
    
    if not sentences:
        return {
            "sentence_count": 0,
            "word_count": 0,
            "avg_sentence_len": 0.0,
            "std_dev_burstiness": 0.0,
            "ai_risk_level": "Unknown",
            "detected_buzzwords": []
        }

    sentence_lengths = [len(re.findall(r'\b\w+\b', sentence)) for sentence in sentences]
    sentence_lengths = [length for length in sentence_lengths if length > 0]
    
    total_words = sum(sentence_lengths)
    total_sentences = len(sentence_lengths)
    
    if total_sentences == 0:
        avg_len = 0.0
        std_dev = 0.0
    else:
        avg_len = total_words / total_sentences
        variance = sum((x - avg_len) ** 2 for x in sentence_lengths) / total_sentences
        std_dev = math.sqrt(variance)

    buzzword_list = [
        "delve", "testament", "tapestry", "pivotal", "beacon", 
        "fostering", "seamlessly", "robust", "interplay", "realm", "ecosystem"
    ]
    detected_buzzwords = [
        word for word in buzzword_list 
        if re.search(r'\b' + re.escape(word) + r'\b', text, re.IGNORECASE)
    ]

    if std_dev >= 8.0 and len(detected_buzzwords) == 0:
        risk_level = "Low (Human-like Burstiness)"
    elif std_dev >= 5.0 and len(detected_buzzwords) <= 1:
        risk_level = "Moderate (Acceptable Cadence)"
    else:
        risk_level = "High Risk (Robotic/Uniform Sentence Cadence)"

    return {
        "sentence_count": total_sentences,
        "word_count": total_words,
        "avg_sentence_len": round(avg_len, 1),
        "std_dev_burstiness": round(std_dev, 2),
        "ai_risk_level": risk_level,
        "detected_buzzwords": list(set(detected_buzzwords))
    }

# ==========================================
# 4. LLM API EXECUTION ENGINE
# ==========================================

def process_text_ollama(text: str, mode: str, model_name: str, endpoint: str) -> str:
    """Executes the request through a local Ollama server."""
    system_prompt = PROMPT_HUMANIZE if mode == "Humanize (AI Bypass)" else PROMPT_PLAGIARISM_REMOVE
    
    payload = {
        "model": model_name.strip(),
        "prompt": f"{system_prompt}\n\nDraft Text:\n{text}",
        "stream": False,
        "options": {
            "temperature": 0.88,
            "top_p": 0.92,
            "presence_penalty": 0.7,
            "frequency_penalty": 0.5
        },
        "keep_alive": 0
    }
    
    response = requests.post(endpoint, json=payload, timeout=90)
    response.raise_for_status()
    raw_output = response.json().get("response", "")
    return clean_ai_leftovers(raw_output)

def process_text_groq(text: str, mode: str, api_key: str, model_name: str) -> str:
    """Executes the request via Groq Cloud API with exact available model targets."""
    system_prompt = PROMPT_HUMANIZE if mode == "Humanize (AI Bypass)" else PROMPT_PLAGIARISM_REMOVE
    
    headers = {
        "Authorization": f"Bearer {api_key.strip()}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": model_name.strip(),
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Draft Text:\n{text}"}
        ],
        "temperature": 0.88,
        "top_p": 0.92,
        "presence_penalty": 0.7,
        "frequency_penalty": 0.5
    }
    
    response = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=40)
    
    if response.status_code == 404:
        try:
            models_resp = requests.get("https://api.groq.com/openai/v1/models", headers=headers, timeout=10)
            if models_resp.status_code == 200:
                available_models = [m["id"] for m in models_resp.json().get("data", [])]
                raise Exception(
                    f"Model '{model_name}' was not found on Groq (404 Error).\n\n"
                    f"Active models available to your API key: {', '.join(available_models)}"
                )
        except Exception as inner_e:
            if "Active models available" in str(inner_e):
                raise inner_e
                
        raise Exception(
            f"Model '{model_name}' was not found on Groq (404 Error). "
            "Please switch to 'openai/gpt-oss-120b' or 'openai/gpt-oss-20b' in the sidebar."
        )
        
    elif response.status_code == 401:
        raise Exception("Invalid Groq API Key (401 Unauthorized). Please check your key under Streamlit Secrets or sidebar inputs.")
        
    response.raise_for_status()
    raw_output = response.json()["choices"][0]["message"]["content"]
    return clean_ai_leftovers(raw_output)

# ==========================================
# 5. STREAMLIT UI LAYOUT
# ==========================================

def main():
    st.set_page_config(page_title="Academic Anti-Detection Studio", layout="wide")
    st.title("🎓 Academic Anti-Detection Studio & Burstiness Analyzer")

    # Sidebar Controls
    st.sidebar.header("Backend Setup")
    backend = st.sidebar.radio("LLM Backend Provider", ["Groq Cloud API", "Ollama (Local)"])
    
    if backend == "Groq Cloud API":
        api_key = st.sidebar.text_input("Groq API Key", type="password", value=os.environ.get("GROQ_API_KEY", ""))
        model_name = st.sidebar.selectbox(
            "Groq Model Target",
            [
                "openai/gpt-oss-120b",
                "openai/gpt-oss-20b",
                "canopylabs/orpheus-v1-english",
                "allam-2-7b"
            ]
        )
    else:
        model_name = st.sidebar.text_input("Ollama Model Target", value="llama3.1:8b")
        ollama_url = st.sidebar.text_input("Ollama Endpoint", value="http://localhost:11434/api/generate")

    mode = st.sidebar.selectbox(
        "Processing Objective",
        ["Humanize (AI Bypass)", "Plagiarism Removal (Clause Flipping)"]
    )

    # Input/Output Columns
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Source Text")
        input_text = st.text_area("Paste draft paragraphs below...", height=350)
        
        if input_text.strip():
            in_metrics = analyze_text_cadence(input_text)
            st.info(
                f"**Source Metrics:** {in_metrics['word_count']} Words | "
                f"Avg Length: {in_metrics['avg_sentence_len']} words | "
                f"Burstiness (StdDev): {in_metrics['std_dev_burstiness']}"
            )

        run_btn = st.button("Process & Refactor", type="primary", use_container_width=True)

    with col2:
        st.subheader("Refactored Output")
        output_placeholder = st.empty()

    if run_btn:
        if not input_text.strip():
            st.warning("Please enter text to process.")
            return

        with st.spinner("Processing anti-detection algorithms..."):
            try:
                if backend == "Groq Cloud API":
                    if not api_key:
                        st.error("Missing Groq API Key. Add it in the sidebar or under Streamlit Cloud Secrets.")
                        return
                    result = process_text_groq(input_text, mode, api_key, model_name)
                else:
                    result = process_text_ollama(input_text, mode, model_name, ollama_url)
                
                output_placeholder.text_area("Refactored Output", value=result, height=350)
                
                # Output Metrics Breakdown
                st.markdown("---")
                st.subheader("📊 Output Text Cadence & AI Risk Profile")
                
                out_metrics = analyze_text_cadence(result)
                
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Word Count", out_metrics["word_count"])
                m2.metric("Avg Sentence Length", f"{out_metrics['avg_sentence_len']} words")
                m3.metric("Burstiness (StdDev)", out_metrics["std_dev_burstiness"], help="Values > 8.0 reflect high human-like sentence length variation.")
                
                risk_str = out_metrics["ai_risk_level"]
                if "Low" in risk_str:
                    m4.success(f"**Risk Profile:**\n{risk_str}")
                elif "Moderate" in risk_str:
                    m4.warning(f"**Risk Profile:**\n{risk_str}")
                else:
                    m4.error(f"**Risk Profile:**\n{risk_str}")

                if out_metrics["detected_buzzwords"]:
                    st.warning(f"⚠️ **Lingering AI Buzzwords Detected:** {', '.join(out_metrics['detected_buzzwords'])}")

            except Exception as e:
                st.error(f"Execution Error: {str(e)}")

if __name__ == "__main__":
    main()
