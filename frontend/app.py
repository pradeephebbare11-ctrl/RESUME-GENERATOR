import streamlit as st
import os
from io import BytesIO
from fpdf import FPDF
from openai import OpenAI

st.set_page_config(page_title="CareerPilot AI", layout="wide")

# ===== CUSTOM CSS =====
st.markdown("""
<style>
.main {
    background: linear-gradient(120deg, #0f172a, #1e293b);
    color: white;
}
h1, h2, h3 {
    color: #38bdf8;
}
.stButton>button {
    border-radius: 10px;
    padding: 10px;
    background: #38bdf8;
    color: black;
    font-weight: bold;
}
.stTextInput>div>div>input {
    border-radius: 8px;
}
.block-container {
    padding-top: 2rem;
}
.card {
    background: #1e293b;
    padding: 20px;
    border-radius: 15px;
    box-shadow: 0px 4px 20px rgba(0,0,0,0.3);
}
</style>
""", unsafe_allow_html=True)

# ===== API CONFIG =====
GROQ_BASE_URL = "https://api.groq.com/openai/v1"

if "api_key" not in st.session_state:
    st.session_state.api_key = os.getenv("GROQ_API_KEY", "")

def get_client():
    return OpenAI(api_key=st.session_state.api_key, base_url=GROQ_BASE_URL)

def generate_text(prompt, system):
    client = get_client()
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
    )
    return response.choices[0].message.content

def build_pdf(text):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=11)
    for line in text.split("\n"):
        pdf.multi_cell(0, 7, line)
    return BytesIO(pdf.output(dest="S").encode("latin-1"))

# ===== HEADER =====
st.markdown("""
<h1 style='text-align:center;'>🚀 CareerPilot AI</h1>
<p style='text-align:center; color:gray;'>Build Resume • Prepare Interviews • Get Hired</p>
""", unsafe_allow_html=True)

tab1, tab2, tab3 = st.tabs(["📄 Resume", "🎤 Interview", "⚙️ Settings"])

# ===== RESUME =====
with tab1:
    st.markdown('<div class="card">', unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        name = st.text_input("👤 Name")
        email = st.text_input("📧 Email")
    with col2:
        phone = st.text_input("📱 Phone")

    education = st.text_area("🎓 Education")
    skills = st.text_area("🧠 Skills")
    projects = st.text_area("💼 Projects")

    if st.button("✨ Generate Resume"):
        if not name or not email:
            st.error("Fill required fields")
        else:
            with st.spinner("Generating..."):
                prompt = f"""
                Create ATS resume:
                Name:{name}
                Email:{email}
                Phone:{phone}
                Education:{education}
                Skills:{skills}
                Projects:{projects}
                """
                resume = generate_text(prompt, "You are resume expert")
                st.success("Done!")
                st.markdown(resume)

                pdf = build_pdf(resume)
                st.download_button("⬇ Download PDF", pdf, "resume.pdf")

    st.markdown('</div>', unsafe_allow_html=True)

# ===== INTERVIEW =====
with tab2:
    st.markdown('<div class="card">', unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)
    with col1:
        role = st.text_input("🎯 Role")
    with col2:
        level = st.selectbox("📊 Level", ["Beginner","Intermediate","Advanced"])
    with col3:
        domain = st.text_input("💻 Domain")

    if st.button("🔥 Generate Questions"):
        with st.spinner("Thinking..."):
            q = generate_text(
                f"Generate 5 interview questions for {role} {level} {domain}",
                "You are interviewer"
            )
            st.markdown(q)

    if st.button("📚 Study Plan"):
        with st.spinner("Planning..."):
            plan = generate_text(
                f"Create study plan for {role} {level} {domain}",
                "You are mentor"
            )
            st.markdown(plan)

    st.markdown('</div>', unsafe_allow_html=True)

# ===== SETTINGS =====
with tab3:
    st.markdown('<div class="card">', unsafe_allow_html=True)

    key = st.text_input("🔑 Groq API Key", type="password")

    if st.button("Save Key"):
        st.session_state.api_key = key
        st.success("Saved!")

    st.info("Get key: https://console.groq.com/keys")

    st.markdown('</div>', unsafe_allow_html=True)