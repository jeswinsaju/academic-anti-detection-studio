import os
import re
import math
import requests
import streamlit as st

# ==========================================
# 1. AGGRESSIVE ANTI-DETECTION SYSTEM PROMPT
# ==========================================

SYSTEM_HUMANIZE_PROMPT = """You are a senior academic editor. Your task is to completely rewrite the user's academic text so that it passes Turnitin and GPTZero as 100% human-written.

STRICT LINGUISTIC CONSTRAINTS:
1. HIGH BURSTINESS (SENTENCE VARIATION): You must aggressively alternate sentence lengths. Write a short 3-5 word statement. Then write a complex 25+ word sentence. 
2. INSERT EM-DASHES & PARENTHESES: Break up complex ideas using em-dashes (—) or parenthetical observations to break synthetic flow.
3. FORBIDDEN AI TRANSITIONS: NEVER use: "Furthermore", "Moreover", "In conclusion", "Additionally", "It is important to note that", "Consequently", "Thus", "In summary", "Overall".
4. FORBIDDEN AI VOCABULARY: NEVER use: "delve", "testament", "tapestry", "pivotal", "beacon", "fostering", "seamlessly", "robust", "interplay", "realm", "ecosystem", "underscores", "highlighting".
5. PRESERVE CITATIONS: Keep all academic citations [e.g., Smith et al., 2023], mathematical variables, data, and technical terms 100% intact.
6. OUTPUT ONLY THE REWRITTEN TEXT: Do not include intros, conversational chat, quotes, or markdown wrappers.
"""

# ==========================================
# 2. POST-PROCESSING MUTATOR
# ==========================================

def mutate_and_clean_text(text: str) -> str:
    """
    Strips robotic preamble and enforces structural cleanups.
    """
    if not text:
        return ""

    # Clean markdown wrappers if returned
    text = re.sub(r"^```[\w]*\n", "", text)
    text = re.sub(r"\n```$", "", text)
    
    # Strip AI intros
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
    return text.strip()

# ==========================================
# 3. CADENCE ANALYZER
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

    if std_dev >= 8.5:
        risk = "Low Risk (0-15% AI Score)"
    elif std_dev >= 5.5:
        risk = "Moderate Risk (25-40% AI Score)"
    else:
        risk = "High Risk (>60% AI Score)"

    return {
        "word_count": total_words,
        "avg_len": round(avg_len, 1),
        "std_dev": round(std_dev, 2),
        "risk": risk
    }

# ==========================================
# 4. API CALL ENGINE
# ==========================================

def process_groq_humanize(text: str, api_key: str, model_name: str) -> str:
    headers = {
        "Authorization": f"Bearer {api_key.strip()}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": model_name.strip(),
        "messages": [
            {"role": "system", "content": SYSTEM_HUMANIZE_PROMPT},
            {"role": "user", "content": f"Rewrite this text to bypass AI detection completely:\n\n{text}"}
        ],
        "temperature": 0.95,
        "top_p": 0.88,
        "presence_penalty": 0.6,
        "frequency_penalty": 0.5
    }
    
    response = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers=headers,
        json=payload,
        timeout=60
    )
    
    if response.status_code != 200:
        raise Exception(f"API Error ({response.status_code}): {response.text}")

    res_json = response.json()
    
    if "choices" in res_json and len(res_json["choices"]) > 0:
        content = res_json["choices"][0]["message"]["content"]
        return mutate_and_clean_text(content)
    else:
        raise Exception(f"Invalid Response Payload from API: {res_json}")

# ==========================================
# 5. STREAMLIT INTERFACE
# ==========================================

def main():
    st.set_page_config(page_title="Academic Anti-Detection Studio", layout="wide")
    st.title("🎓 Academic Anti-Detection Studio")

    st.sidebar.header("Groq API Setup")
    api_key = st.sidebar.text_input("Groq API Key", type="password", value=os.environ.get("GROQ_API_KEY", ""))
    
    model_name = st.sidebar.selectbox(
        "Model Target",
        [
            "openai/gpt-oss-120b",
            "openai/gpt-oss-20b",
            "canopylabs/orpheus-v1-english",
            "allam-2-7b"
        ]
    )

    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Source Draft")
        input_text = st.text_area("Paste original academic text here...", height=400)
        run_btn = st.button("Humanize & Bypass AI", type="primary", use_container_width=True)

    with col2:
        st.subheader("Refactored Output")
        
        # Session state handling to ensure text stays visible after rerenders
        if "humanized_text" not in st.session_state:
            st.session_state.humanized_text = ""
            
        output_box = st.text_area(
            "Output Text",
            value=st.session_state.humanized_text,
            height=400,
            key="output_field"
        )

    if run_btn:
        if not input_text.strip():
            st.warning("Please paste source text first.")
            return

        if not api_key.strip():
            st.error("Groq API Key is missing.")
            return

        with st.spinner("Processing anti-detection algorithms..."):
            try:
                result = process_groq_humanize(input_text, api_key, model_name)
                
                if result:
                    st.session_state.humanized_text = result
                    st.rerun()
                else:
                    st.error("The API returned an empty output. Try changing the Model Target in the sidebar.")

            except Exception as e:
                st.error(f"Execution Failure: {str(e)}")

    # Show Metrics if output exists
    if st.session_state.humanized_text:
        st.markdown("---")
        st.subheader("📊 Cadence & Burstiness Metrics")
        metrics = analyze_cadence(st.session_state.humanized_text)
        
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Word Count", metrics["word_count"])
        m2.metric("Avg Sentence Length", f"{metrics['avg_len']} words")
        m3.metric("Burstiness (StdDev)", metrics["std_dev"])
        
        if "Low Risk" in metrics["risk"]:
            m4.success(metrics["risk"])
        elif "Moderate" in metrics["risk"]:
            m4.warning(metrics["risk"])
        else:
            m4.error(metrics["risk"])

if __name__ == "__main__":
    main()
