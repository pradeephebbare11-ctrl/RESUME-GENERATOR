import streamlit as st
import time
import os
import re
from io import BytesIO
from fpdf import FPDF
from openai import OpenAI

st.set_page_config(page_title="CareerPilot AI", layout="wide")

# ============ API CONFIG ============
GROQ_BASE_URL = "https://api.groq.com/openai/v1"

GROQ_MODELS = [
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
]

# ============ SESSION ============
if "api_key" not in st.session_state:
    st.session_state.api_key = os.getenv("GROQ_API_KEY", "")

# ============ FUNCTIONS ============
def get_client():
    if not st.session_state.api_key:
        raise ValueError("Add your Groq API key in Settings ⚙️")
    return OpenAI(api_key=st.session_state.api_key, base_url=GROQ_BASE_URL)


def generate_text(prompt, system):
    client = get_client()
    response = client.chat.completions.create(
        model=GROQ_MODELS[0],
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
    )
    return response.choices[0].message.content


def generate_resume(name, email, phone, skills, projects, education):
    prompt = f"""
Create a professional ATS-friendly resume.

Name: {name}
Email: {email}
Phone: {phone}

Education:
{education}

Skills:
{skills}

Projects:
{projects}
"""
    return generate_text(prompt, "You are a resume expert.")


def build_pdf(text, name):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=11)

    for line in text.split("\n"):
        pdf.multi_cell(0, 7, line)

    return BytesIO(pdf.output(dest="S").encode("latin-1"))


def generate_questions(role, level, domain, n):
    prompt = f"Generate {n} interview questions for {role} ({level}) in {domain}"
    return generate_text(prompt, "You are an interviewer.")


def generate_study_plan(role, level, domain):
    prompt = f"Create study plan for {role} ({level}) in {domain}"
    return generate_text(prompt, "You are a mentor.")


# ============ UI ============
st.title("📄 CareerPilot AI")

tab1, tab2, tab3 = st.tabs(["📝 Resume", "🎤 Interview", "⚙️ Settings"])

# ================== RESUME ==================
with tab1:
    st.subheader("Resume Builder")

    name = st.text_input("Name")
    email = st.text_input("Email")
    phone = st.text_input("Phone")

    education = st.text_area("Education")
    skills = st.text_area("Skills")
    projects = st.text_area("Projects")

    if st.button("Generate Resume"):
        if not name or not email:
            st.error("Fill required fields")
        else:
            with st.spinner("Generating..."):
                resume = generate_resume(name, email, phone, skills, projects, education)

                st.success("Done!")
                st.markdown(resume)

                pdf = build_pdf(resume, name)

                st.download_button("Download PDF", pdf, file_name="resume.pdf")


# ================== INTERVIEW ==================
with tab2:
    st.subheader("Interview Prep")

    role = st.text_input("Role")
    level = st.selectbox("Level", ["Beginner", "Intermediate", "Advanced"])
    domain = st.text_input("Domain")

    if st.button("Generate Questions"):
        with st.spinner("Generating..."):
            questions = generate_questions(role, level, domain, 5)
            st.markdown(questions)

    if st.button("Generate Study Plan"):
        with st.spinner("Generating..."):
            plan = generate_study_plan(role, level, domain)
            st.markdown(plan)


# ================== SETTINGS ==================
with tab3:
    st.subheader("API Settings")

    key = st.text_input("Groq API Key", type="password")

    if st.button("Save Key"):
        st.session_state.api_key = key
        st.success("Saved!")

    st.info("Get API key from https://console.groq.com/keys")