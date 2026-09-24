import os
import re
import math
import requests
import streamlit as st

# ==========================================
# 1. ACADEMIC PUBLICATION PROMPT
# ==========================================

PUBLICATION_PROMPT = """You are a principal researcher and peer-reviewer for an academic journal. 

Your task is to rewrite the user's text on anxiety screening so that it reads as original, high-impact, publication-ready research that passes Turnitin and GPTZero.

STRICT EDITORIAL REQUIREMENTS:
1. SPECIFICITY & ANCHORING: Replace all generic references (e.g., "screening tools", "questionnaires") with specific clinical measures (e.g., GAD-7, STAI, Beck Anxiety Inventory, HAM-A) and specific clinical contexts (e.g., primary care triage, adolescent ED screening).
2. CRITICAL ANALYSIS OVER SUMMARY: Do not merely describe what screening is. Frame the content around trade-offs: sensitivity vs. specificity, self-report bias, somatic symptom overlap, or implementation barriers.
3. NON-LINEAR FLOW: Do not start every paragraph with a general topic sentence. Start some paragraphs directly with a limitation, a methodological critique, or a sharp, direct finding.
4. RHYTHM VARIATION: Alternate short 2-3 sentence analytical assertions with longer, detailed methodological breakdowns.
5. PRESERVE INTENT & CITATIONS: Keep all citations [e.g., Smith et al., 2023], data points, and technical core ideas intact.
6. NO AI ADJECTIVES/TRANSITIONS: Do NOT use: Furthermore, Moreover, In conclusion, pivotal, tapestry, delve, foster, underscore, robust, realm.

Output ONLY the rewritten academic text.
"""

# ==========================================
# 2. POST-PROCESSING ENFORCER
# ==========================================

def enforce_publication_rules(text: str) -> str:
    """Post-processes output to guarantee removal of AI artifacts."""
    if not text:
        return ""

    # Clean markdown formatting wrappers
    text = re.sub(r"^```[\w]*\n", "", text)
    text = re.sub(r"\n```$", "", text)
    text = re.sub(r"^(Here is|Below is|Sure|Here's)[\s\S]*?:\n*", "", text, flags=re.IGNORECASE)

    # Clean redundant spaces
    text = re.sub(r" +", " ", text)
    return text.strip()

# ==========================================
# 3. METRICS ENGINE
# ==========================================

def evaluate_uniqueness_metrics(text: str) -> dict:
    sentences = [s.strip() for s in re.split(r'[.!?]+', text) if s.strip()]
    if not sentences:
        return {"word_count": 0, "avg_len": 0, "std_dev": 0, "rating": "N/A"}

    lengths = [len(re.findall(r'\b\w+\b', s)) for s in sentences if len(re.findall(r'\b\w+\b', s)) > 0]
    if not lengths:
        return {"word_count": 0, "avg_len": 0, "std_dev": 0, "rating": "N/A"}

    total_words = sum(lengths)
    avg_len = total_words / len(lengths)
    variance = sum((x - avg_len) ** 2 for x in lengths) / len(lengths)
    std_dev = math.sqrt(variance)

    # Higher Standard Deviation (>8.0) indicates high variation in human cadence
    if std_dev >= 8.5:
        rating = "Publication Ready (High Structural Variety)"
    elif std_dev >= 5.5:
        rating = "Moderate Variety (Consider Adding Shorter Sentences)"
    else:
        rating = "High AI Signature (Uniform Paragraph Structure)"

    return {
        "word_count": total_words,
        "avg_len": round(avg_len, 1),
        "std_dev": round(std_dev, 2),
        "rating": rating
    }

# ==========================================
# 4. API CALL ENGINE
# ==========================================

def process_academic_rewrite(text: str, api_key: str, model_name: str) -> str:
    headers = {
        "Authorization": f"Bearer {api_key.strip()}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": model_name.strip(),
        "messages": [
            {"role": "system", "content": PUBLICATION_PROMPT},
            {"role": "user", "content": f"Transform this academic draft into publication-ready, critically-analyzed text:\n\n{text}"}
        ],
        "temperature": 0.8,
        "top_p": 0.85,
        "presence_penalty": 0.5,
        "frequency_penalty": 0.5
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
        content = res_json["choices"][0]["message"]["content"]
        return enforce_publication_rules(content)
    except (KeyError, IndexError):
        raise Exception(f"Invalid Payload Structure: {res_json}")

# ==========================================
# 5. STREAMLIT INTERFACE
# ==========================================

def main():
    st.set_page_config(page_title="Academic Publication Engine", layout="wide")
    st.title("🎓 Academic Uniqueness & Publication Engine")

    if "output_text" not in st.session_state:
        st.session_state["output_text"] = ""

    st.sidebar.header("Groq Configuration")
    api_key = st.sidebar.text_input("Groq API Key", type="password", value=os.environ.get("GROQ_API_KEY", ""))
    
    model_name = st.sidebar.selectbox(
        "Model Selection",
        [
            "openai/gpt-oss-120b",
            "openai/gpt-oss-20b",
            "canopylabs/orpheus-v1-english"
        ]
    )

    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("1. Source Draft")
        input_text = st.text_area("Paste original academic text here...", height=400, key="input_text")
        run_btn = st.button("Restructure for Publication", type="primary", use_container_width=True)

    # Execute transformation before rendering second column
    if run_btn:
        if not input_text.strip():
            st.warning("Please enter text first.")
        elif not api_key.strip():
            st.error("API key is required.")
        else:
            with st.spinner("Applying domain anchoring and critical analysis restructuring..."):
                try:
                    result = process_academic_rewrite(input_text, api_key, model_name)
                    st.session_state["output_text"] = result
                except Exception as e:
                    st.error(f"Processing Error: {str(e)}")

    with col2:
        st.subheader("2. Unique Academic Output")
        st.text_area(
            "Publication-Ready Output",
            height=400,
            key="output_text"
        )

    # Metrics section
    if st.session_state.get("output_text", "").strip():
        st.markdown("---")
        st.subheader("📊 Cadence & Structure Evaluation")
        metrics = evaluate_uniqueness_metrics(st.session_state["output_text"])
        
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Word Count", metrics["word_count"])
        m2.metric("Avg Sentence Length", f"{metrics['avg_len']} words")
        m3.metric("Cadence Variety (StdDev)", metrics["std_dev"])
        
        if "Publication Ready" in metrics["rating"]:
            m4.success(metrics["rating"])
        elif "Moderate" in metrics["rating"]:
            m4.warning(metrics["rating"])
        else:
            m4.error(metrics["rating"])

if __name__ == "__main__":
    main()
