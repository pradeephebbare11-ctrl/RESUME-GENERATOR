import streamlit as st
import time
import os
import re
import subprocess
import sys
from io import BytesIO
from pathlib import Path
import requests
from fpdf import FPDF


st.set_page_config(page_title="CareerPilot AI", layout="wide")

# ============ API Configuration ============
DEFAULT_API_BASE_URLS = [
    os.getenv("API_BASE_URL"),
    os.getenv("BACKEND_URL"),
    "http://127.0.0.1:8000",
    "http://localhost:8000",
]
GROQ_BASE_URL = "https://api.groq.com/openai/v1"
GROQ_MODELS = [
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
    "openai/gpt-oss-20b",
]
GROQ_STT_MODEL = "whisper-large-v3-turbo"
GROQ_TTS_MODEL = "canopylabs/orpheus-v1-english"
GROQ_TTS_VOICE = "austin"

# ============ Session State Initialization ============
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "token" not in st.session_state:
    st.session_state.token = None
if "user_name" not in st.session_state:
    st.session_state.user_name = None
if "user_email" not in st.session_state:
    st.session_state.user_email = None
if "current_questions" not in st.session_state:
    st.session_state.current_questions = None
if "question_count" not in st.session_state:
    st.session_state.question_count = 0
if "study_plan" not in st.session_state:
    st.session_state.study_plan = None
if "answer_feedback" not in st.session_state:
    st.session_state.answer_feedback = {}
if "answer_transcripts" not in st.session_state:
    st.session_state.answer_transcripts = {}
if "question_audio" not in st.session_state:
    st.session_state.question_audio = {}
if "feedback_audio" not in st.session_state:
    st.session_state.feedback_audio = {}
if "voice_current_questions" not in st.session_state:
    st.session_state.voice_current_questions = None
if "voice_question_count" not in st.session_state:
    st.session_state.voice_question_count = 0
if "voice_answer_feedback" not in st.session_state:
    st.session_state.voice_answer_feedback = {}
if "voice_answer_transcripts" not in st.session_state:
    st.session_state.voice_answer_transcripts = {}
if "voice_question_audio" not in st.session_state:
    st.session_state.voice_question_audio = {}
if "voice_feedback_audio" not in st.session_state:
    st.session_state.voice_feedback_audio = {}
if "voice_interview_role" not in st.session_state:
    st.session_state.voice_interview_role = None
if "voice_interview_level" not in st.session_state:
    st.session_state.voice_interview_level = None
if "voice_interview_domain" not in st.session_state:
    st.session_state.voice_interview_domain = None
if "voice_live_active" not in st.session_state:
    st.session_state.voice_live_active = False
if "voice_live_question" not in st.session_state:
    st.session_state.voice_live_question = None
if "voice_live_question_audio" not in st.session_state:
    st.session_state.voice_live_question_audio = None
if "voice_live_pending_autoplay_turn" not in st.session_state:
    st.session_state.voice_live_pending_autoplay_turn = None
if "voice_live_last_autoplayed_turn" not in st.session_state:
    st.session_state.voice_live_last_autoplayed_turn = 0
if "voice_live_feedback" not in st.session_state:
    st.session_state.voice_live_feedback = None
if "voice_live_feedback_audio" not in st.session_state:
    st.session_state.voice_live_feedback_audio = None
if "voice_live_history" not in st.session_state:
    st.session_state.voice_live_history = []
if "voice_live_round" not in st.session_state:
    st.session_state.voice_live_round = 0
if "voice_live_transcript" not in st.session_state:
    st.session_state.voice_live_transcript = None
if "voice_live_complete" not in st.session_state:
    st.session_state.voice_live_complete = False
if "voice_live_messages" not in st.session_state:
    st.session_state.voice_live_messages = []
if "interview_role" not in st.session_state:
    st.session_state.interview_role = None
if "interview_level" not in st.session_state:
    st.session_state.interview_level = None
if "interview_domain" not in st.session_state:
    st.session_state.interview_domain = None
if "api_key" not in st.session_state:
    st.session_state.api_key = os.getenv(
        "GROQ_API_KEY",
        "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",
    )
if "backend_url" not in st.session_state:
    st.session_state.backend_url = None
if "backend_autostart_attempted" not in st.session_state:
    st.session_state.backend_autostart_attempted = False

# ============ Helper Functions ============
def _candidate_backend_urls():
    seen = set()
    urls = []
    for url in DEFAULT_API_BASE_URLS:
        if not url:
            continue
        cleaned = url.rstrip("/")
        if cleaned not in seen:
            seen.add(cleaned)
            urls.append(cleaned)
    return urls


def _backend_is_reachable(base_url, timeout=1.5):
    try:
        response = requests.get(f"{base_url}/", timeout=timeout)
        return response.ok
    except requests.RequestException:
        return False


def _start_local_backend():
    repo_root = Path(__file__).resolve().parents[1]
    backend_entry = repo_root / "backend" / "backend" / "main.py"
    if not backend_entry.exists():
        return False

    try:
        subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "backend.backend.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                "8000",
            ],
            cwd=repo_root,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        return False

    for _ in range(10):
        time.sleep(0.5)
        if _backend_is_reachable("http://127.0.0.1:8000"):
            return True
    return False


def get_api_base_url():
    current_url = st.session_state.backend_url
    if current_url and _backend_is_reachable(current_url):
        return current_url

    for candidate in _candidate_backend_urls():
        if _backend_is_reachable(candidate):
            st.session_state.backend_url = candidate
            return candidate

    if not st.session_state.backend_autostart_attempted:
        st.session_state.backend_autostart_attempted = True
        if _start_local_backend():
            st.session_state.backend_url = "http://127.0.0.1:8000"
            return st.session_state.backend_url

    st.session_state.backend_url = _candidate_backend_urls()[0]
    return st.session_state.backend_url


def get_groq_client(api_key=None):
    api_key = api_key or st.session_state.api_key
    if not api_key:
        raise ValueError("API key not set. Please go to Settings and add your Groq API key.")
    return OpenAI(api_key=api_key, base_url=GROQ_BASE_URL)


def generate_text(prompt, system_prompt, models=None):
    client = get_groq_client()
    model_list = models or GROQ_MODELS

    for model in model_list:
        for attempt in range(2):
            try:
                response = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt},
                    ],
                )
                content = response.choices[0].message.content
                if content:
                    return content
            except Exception as e:
                if "429" in str(e) or "rate limit" in str(e).lower():
                    time.sleep(2)
                else:
                    continue

    raise RuntimeError("Unable to generate a response with the configured Groq models.")


def transcribe_audio(uploaded_audio):
    client = get_groq_client()
    transcription = client.audio.transcriptions.create(
        file=(uploaded_audio.name or "answer.wav", uploaded_audio.getvalue()),
        model=GROQ_STT_MODEL,
        language="en",
        response_format="json",
        temperature=0.0,
    )
    return transcription.text.strip()


def generate_speech_audio(text):
    client = get_groq_client()
    try:
        speech_response = client.audio.speech.create(
            model=GROQ_TTS_MODEL,
            voice=GROQ_TTS_VOICE,
            input=text,
            response_format="wav",
        )
    except Exception as e:
        error_text = str(e).lower()
        if "model_terms_required" in error_text or "requires terms acceptance" in error_text:
            raise RuntimeError(
                "Voice output is unavailable until Groq TTS terms are accepted for "
                f"`{GROQ_TTS_MODEL}`. Ask your org admin to accept them at "
                "https://console.groq.com/playground?model=canopylabs%2Forpheus-v1-english"
            ) from e
        raise
    if hasattr(speech_response, "read"):
        return speech_response.read()
    if hasattr(speech_response, "content"):
        return speech_response.content
    return bytes(speech_response)


def parse_questions(question_text):
    questions = []
    for line in question_text.splitlines():
        cleaned = line.strip()
        if not cleaned:
            continue
        match = re.match(r"^\d+[\).\:-]?\s*(.+)$", cleaned)
        if match:
            questions.append(match.group(1).strip())
    if questions:
        return questions
    return [line.strip("- ").strip() for line in question_text.splitlines() if line.strip()]


def generate_interview_questions(role, level, domain, num_questions):
    prompt = f"""Generate {num_questions} interview questions for a {level} level candidate applying for the role of {role} in {domain}.

Include a mix of:
- Technical questions (50%)
- Behavioral questions (50%)

Format ONLY the questions, numbered 1-{num_questions}. Keep it concise. Example:
1. What is your experience with [technology]?
2. Tell me about a time when...

DO NOT include ideal answers or evaluation criteria in this response."""

    return generate_text(
        prompt,
        "You are an expert interviewer who creates realistic and well-balanced interview question sets.",
    )


def generate_answer_feedback(role, level, domain, question_number, question_text, user_answer):
    feedback_prompt = f"""As an expert interviewer, evaluate this answer to the interview question.

Question for {role} position ({level} level, {domain}):
Question {question_number}: {question_text}

User's Answer:
{user_answer}

Provide evaluation in this exact format:

**FEEDBACK ON YOUR ANSWER:**

**Strengths:**
- [strength 1]
- [strength 2]

**Areas for Improvement:**
- [improvement 1]
- [improvement 2]

**Score: X/10**

**Why this score:** [brief explanation]

**Tips to Improve:**
[specific advice]

---

**IDEAL ANSWER (for reference):**
[Provide what a great answer would look like]

**Evaluation Criteria:**
- [criterion 1]
- [criterion 2]"""

    return generate_text(
        feedback_prompt,
        "You are an expert interviewer who gives fair, specific, and actionable interview feedback.",
    )


def format_voice_history(history):
    if not history:
        return "No interview history yet."

    parts = []
    for item in history:
        parts.append(
            f"Round {item['round']}\nQuestion: {item['question']}\nAnswer: {item['answer']}\n"
        )
    return "\n".join(parts)


def start_live_voice_interview(role, level, domain):
    prompt = f"""You are conducting a realistic live interview.

Candidate target role: {role}
Candidate experience level: {level}
Domain/tech stack: {domain}

Ask the very first interview question only.

Rules:
- Ask exactly one question.
- Make it natural and conversational.
- Tailor it to the role and domain.
- Do not include evaluation, tips, headings, bullet points, or multiple questions.
- Keep it under 45 words."""

    return generate_text(
        prompt,
        "You are a professional interviewer running a realistic one-question-at-a-time live interview.",
    ).strip()


def continue_live_voice_interview(role, level, domain, history, current_round):
    prompt = f"""You are conducting a realistic live interview.

Candidate target role: {role}
Candidate experience level: {level}
Domain/tech stack: {domain}
Current round completed: {current_round}

Interview history:
{format_voice_history(history)}

Based on the candidate's most recent answer, ask exactly one next interview question.

Rules:
- Sound like a real interviewer.
- Ask exactly one question and nothing else.
- Do not give feedback, evaluation, scores, headings, or explanations.
- Do not use bullet points.
- Make the next question adapt to the candidate's previous answer.
- Continue the interview naturally instead of trying to end it.
- Keep it concise and natural, under 35 words."""

    response = generate_text(
        prompt,
        "You are a professional interviewer running a realistic one-question-at-a-time live interview.",
    )
    return response.strip()


def finish_live_voice_interview(role, level, domain, history):
    prompt = f"""You have completed a realistic live interview for this candidate.

Candidate target role: {role}
Candidate experience level: {level}
Domain/tech stack: {domain}

Interview history:
{format_voice_history(history)}

Provide a concise final evaluation in exactly this format:

FINAL_SUMMARY:
[3-5 sentences summarizing overall performance]

STRENGTHS:
- [strength 1]
- [strength 2]

IMPROVEMENTS:
- [improvement 1]
- [improvement 2]

FINAL_RECOMMENDATION:
[1 sentence on what the candidate should do next]
"""

    return generate_text(
        prompt,
        "You are a professional interviewer giving a short final wrap-up after a live interview.",
    ).strip()


def render_interview_answer_section(questions_text, role, level, domain, voice_mode=False, prefix="text"):
    feedback_key = "answer_feedback" if prefix == "text" else "voice_answer_feedback"
    transcript_key = "answer_transcripts" if prefix == "text" else "voice_answer_transcripts"
    question_audio_key = "question_audio" if prefix == "text" else "voice_question_audio"
    feedback_audio_key = "feedback_audio" if prefix == "text" else "voice_feedback_audio"

    questions = parse_questions(questions_text)

    st.markdown("---")
    st.markdown("### Interview Questions")
    st.markdown(questions_text)

    st.markdown("---")
    st.subheader("📝 Answer the Questions")
    if voice_mode:
        st.write("Record your answers with your microphone or add text notes before you submit.")
    else:
        st.write("Type your answers below and submit each one for AI feedback.")

    for idx, question_text in enumerate(questions, start=1):
        with st.expander(f"Question {idx}", expanded=False):
            st.markdown(f"**Question {idx}:** {question_text}")

            if voice_mode:
                if st.button("🔊 Generate Question Audio", key=f"{prefix}_play_question_audio_{idx}"):
                    with st.spinner("Generating spoken question..."):
                        try:
                            st.session_state[question_audio_key][idx] = generate_speech_audio(question_text)
                        except Exception as e:
                            st.error(f"Error generating question audio: {str(e)}")

                if idx in st.session_state[question_audio_key]:
                    st.audio(st.session_state[question_audio_key][idx], format="audio/wav")

            user_answer = st.text_area(
                f"Your answer to Q{idx}:",
                placeholder="Type your answer here...",
                height=120,
                key=f"{prefix}_answer_{idx}"
            )

            recorded_answer = None
            if voice_mode:
                recorded_answer = st.audio_input(
                    f"Record answer for Q{idx}",
                    key=f"{prefix}_audio_answer_{idx}",
                    help="Use your microphone to record a spoken answer.",
                )
                if idx in st.session_state[transcript_key]:
                    st.caption(f"Latest transcript: {st.session_state[transcript_key][idx]}")

            if st.button(f"📊 Submit Answer {idx}", type="secondary", key=f"{prefix}_submit_{idx}"):
                final_answer = user_answer.strip()
                try:
                    if recorded_answer is not None:
                        with st.spinner("🔄 Transcribing your answer..."):
                            transcript = transcribe_audio(recorded_answer)
                            st.session_state[transcript_key][idx] = transcript
                        if transcript:
                            final_answer = transcript if not final_answer else f"{final_answer}\n\nVoice transcript:\n{transcript}"

                    if not final_answer.strip():
                        st.error("⚠️ Please type an answer or record a voice response.")
                    else:
                        with st.spinner("🔄 Evaluating your answer..."):
                            feedback_text = generate_answer_feedback(
                                role,
                                level,
                                domain,
                                idx,
                                question_text,
                                final_answer,
                            )
                            st.session_state[feedback_key][idx] = feedback_text
                except Exception as e:
                    if "429" in str(e) or "rate limit" in str(e).lower():
                        st.error("⚠️ **Groq Rate Limit Reached**\n\nPlease wait a moment and retry, or check your Groq plan and usage limits.")
                    else:
                        st.error(f"Error: {str(e)}")

            if idx in st.session_state[feedback_key]:
                st.info(st.session_state[feedback_key][idx])

                if voice_mode:
                    if st.button("🗣️ Generate Spoken Feedback", key=f"{prefix}_play_feedback_audio_{idx}"):
                        with st.spinner("Generating spoken feedback..."):
                            try:
                                spoken_feedback = st.session_state[feedback_key][idx][:1800]
                                st.session_state[feedback_audio_key][idx] = generate_speech_audio(spoken_feedback)
                            except Exception as e:
                                st.error(f"Error generating spoken feedback: {str(e)}")

                    if idx in st.session_state[feedback_audio_key]:
                        st.audio(st.session_state[feedback_audio_key][idx], format="audio/wav")


def generate_resume(name, email, phone, skills, projects, education):
    prompt = f"""
    Generate a professional ATS-friendly resume.

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

    try:
        return generate_text(
            prompt,
            "You write polished, ATS-friendly resumes that are concise and professional.",
        )
    except Exception as e:
        if "api key" in str(e).lower() or "authentication" in str(e).lower():
            return f"⚠️ Error: {str(e)}"
        return f"⚠️ Error generating resume: {str(e)}"

    return "⚠️ Groq request failed. Please try again in a few minutes or check your Groq API plan and rate limits."


def build_resume_pdf(resume_text, candidate_name):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, f"{candidate_name} Resume", ln=True)
    pdf.ln(4)
    pdf.set_font("Arial", size=11)

    for raw_line in resume_text.splitlines():
        line = raw_line.strip()
        if not line:
            pdf.ln(4)
            continue
        safe_line = line.encode("latin-1", "replace").decode("latin-1")
        pdf.multi_cell(0, 7, safe_line)

    pdf_bytes = pdf.output(dest="S").encode("latin-1")
    return BytesIO(pdf_bytes)


def generate_study_plan(role, level, domain):
    prompt = f"""Create a structured study plan for a candidate preparing for a {level} level {role} interview in {domain}.

Return the response in markdown using exactly these sections:

## Study Concepts & Topic Preparation
A 2-3 sentence overview of what matters most for this role.

## Progressive Learning Path
### Stage 1: Foundations
- 4 to 6 core concepts

### Stage 2: Applied Skills
- 4 to 6 practical topics to practice

### Stage 3: Interview-Focused Mastery
- 4 to 6 advanced topics, tradeoffs, and scenario-based preparation points

## Role-Specific Topics to Revise
- 6 to 8 targeted concepts for {role} in {domain}

## Practice Activities
- 4 to 6 exercises, mock tasks, or mini-projects

## Study Material Suggestions
- Recommend free learning resources by type only, such as documentation, tutorials, videos, blogs, courses, and mock interview practice

## Final Revision Checklist
- 6 to 8 concise checklist items

Keep the plan practical, progressive, and easy to scan. Do not mention that you are an AI."""

    return generate_text(
        prompt,
        "You create clear, structured interview preparation roadmaps for job candidates.",
    )

def login_user(email, password):
    # Truncate password to 72 bytes (bcrypt limitation)
    password = password[:72]
    api_base_url = get_api_base_url()
    
    try:
        response = requests.post(f"{api_base_url}/api/login", json={
            "email": email,
            "password": password
        }, timeout=5)
        if response.status_code == 200:
            data = response.json()
            st.session_state.authenticated = True
            st.session_state.token = data["access_token"]
            st.session_state.user_name = data["user_name"]
            st.session_state.user_email = email
            return True, "Login successful!"
        else:
            error_detail = response.json().get("detail", "Login failed")
            return False, f"Login failed: {error_detail}"
    except requests.exceptions.ConnectionError:
        return False, (
            "Backend connection error. Start the FastAPI server with "
            "`uvicorn backend.backend.main:app --host 127.0.0.1 --port 8000` "
            f"or set `API_BASE_URL`. Tried: {api_base_url}"
        )
    except requests.exceptions.Timeout:
        return False, "Backend request timed out"
    except Exception as e:
        return False, f"Error: {str(e)}"

def register_user(name, email, password, confirm_password):
    if password != confirm_password:
        return False, "Passwords do not match"
    
    # Truncate password to 72 bytes (bcrypt limitation)
    password = password[:72]
    api_base_url = get_api_base_url()
    
    try:
        response = requests.post(f"{api_base_url}/api/register", json={
            "name": name,
            "email": email,
            "password": password
        }, timeout=5)
        
        # Debug: Show raw response
        if response.status_code == 200:
            data = response.json()
            st.session_state.authenticated = True
            st.session_state.token = data["access_token"]
            st.session_state.user_name = data["user_name"]
            st.session_state.user_email = email
            return True, "Registration successful!"
        else:
            try:
                error_detail = response.json().get("detail", "Registration failed")
            except:
                error_detail = f"Backend error (Status {response.status_code}): {response.text}"
            return False, f"Registration failed: {error_detail}"
    except requests.exceptions.ConnectionError:
        return False, (
            "Backend connection error. Start the FastAPI server with "
            "`uvicorn backend.backend.main:app --host 127.0.0.1 --port 8000` "
            f"or set `API_BASE_URL`. Tried: {api_base_url}"
        )
    except requests.exceptions.Timeout:
        return False, "Backend request timed out"
    except Exception as e:
        return False, f"Error: {str(e)}"

def logout_user():
    st.session_state.authenticated = False
    st.session_state.token = None
    st.session_state.user_name = None
    st.session_state.user_email = None

# ============ Main App ============
if not st.session_state.authenticated:
    # Show Login/Register Page
    st.title("📄 CareerPilot AI")
    
    tab1, tab2 = st.tabs(["Login", "Register"])
    
    with tab1:
        st.subheader("Login to Your Account")
        login_email = st.text_input("Email", key="login_email", placeholder="your@email.com")
        login_password = st.text_input("Password", type="password", key="login_password")
        
        if st.button("Login", type="primary", use_container_width=True):
            if not login_email or not login_password:
                st.error("⚠️ Please fill in all fields")
            else:
                success, message = login_user(login_email, login_password)
                if success:
                    st.success(message)
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error(message)
                    st.write(f"**Backend URL:** {get_api_base_url()}")
        
        st.markdown("---")
        st.write("**Demo Credentials:**")
        st.info("Email: demo@example.com\nPassword: demo123")
    
    with tab2:
        st.subheader("Create a New Account")
        reg_name = st.text_input("Full Name", key="reg_name", placeholder="John Doe")
        reg_email = st.text_input("Email", key="reg_email", placeholder="your@email.com")
        reg_password = st.text_input("Password", type="password", key="reg_password")
        reg_confirm = st.text_input("Confirm Password", type="password", key="reg_confirm")
        
        if st.button("Register", type="primary", use_container_width=True):
            if not all([reg_name, reg_email, reg_password, reg_confirm]):
                st.error("⚠️ Please fill in all fields")
            else:
                success, message = register_user(reg_name, reg_email, reg_password, reg_confirm)
                if success:
                    st.success(message)
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error(message)
                    st.write(f"**Backend URL:** {get_api_base_url()}")

else:
    # Show Resume Generator Page
    st.title("📄 CareerPilot AI")
    
    # Top right logout button
    col1, col2 = st.columns([4, 1])
    with col2:
        if st.button("Logout"):
            logout_user()
            st.rerun()
    
    # Welcome message
    st.write(f"Welcome, **{st.session_state.user_name}**! 👋")
    
    # Main Navigation Tabs
    tab1, tab2, tab3, tab4 = st.tabs(["📝 Resume Builder", "🎤 Interview Prep", "🎙️ Voice Mock Interview", "⚙️ Settings"])
    
    with tab1:
        st.subheader("Fill in your information to generate a professional ATS-friendly resume.")
        st.markdown("---")
        
        col1, col2 = st.columns(2)
        
        with col1:
            name = st.text_input("Full Name *", placeholder="John Doe")
            email = st.text_input("Email *", placeholder="john@example.com")
            
        with col2:
            phone = st.text_input("Phone Number (Optional)", placeholder="123-456-7890")
        
        education = st.text_area("Education *", placeholder="Bachelor of Science in Computer Science, XYZ University, 2020")
        skills = st.text_area("Skills *", placeholder="Python, JavaScript, React, Django, SQL")
        projects = st.text_area("Projects (Optional)", placeholder="Project 1: Description\nProject 2: Description")
        
        if st.button("Generate Resume", type="primary", use_container_width=True):
            if not all([name, email, skills, education]):
                st.error("⚠️ Please fill in all required fields (marked with *).")
            else:
                with st.spinner("🔄 Generating your resume..."):
                    resume = generate_resume(name, email, phone, skills, projects, education)
                    st.success("✅ Resume generated!")
                    st.markdown("---")
                    st.markdown(resume)

                    resume_pdf = build_resume_pdf(resume, name)
                    download_col1, download_col2 = st.columns(2)

                    with download_col1:
                        st.download_button(
                            label="⬇️ Download Resume as Text",
                            data=resume,
                            file_name=f"{name.replace(' ', '_')}_resume.txt",
                            mime="text/plain",
                            use_container_width=True
                        )

                    with download_col2:
                        st.download_button(
                            label="⬇️ Download Resume as PDF",
                            data=resume_pdf.getvalue(),
                            file_name=f"{name.replace(' ', '_')}_resume.pdf",
                            mime="application/pdf",
                            use_container_width=True
                        )
    
    with tab2:
        st.subheader("🎤 Interview Q&A Generator")
        st.write("Prepare for your interview with AI-generated questions, written answers, feedback, and study planning.")
        st.markdown("---")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            interview_role = st.text_input("Target Role *", placeholder="e.g., Senior Software Engineer")
        
        with col2:
            interview_level = st.selectbox("Experience Level *", 
                                           ["Beginner", "Intermediate", "Advanced", "Expert"])
        
        with col3:
            interview_domain = st.text_input("Domain/Tech Stack *", placeholder="e.g., Python, Web Development")
        
        num_questions = st.slider("Number of Questions", min_value=1, max_value=10, value=5)

        study_col1, study_col2 = st.columns(2)

        with study_col1:
            if st.button("📚 Generate Study Plan", type="secondary", use_container_width=True):
                if not all([interview_role, interview_domain]):
                    st.error("⚠️ Please fill in Role and Domain.")
                else:
                    with st.spinner("🔄 Building your study roadmap..."):
                        try:
                            study_plan = generate_study_plan(interview_role, interview_level, interview_domain)
                            st.session_state.study_plan = study_plan
                            st.session_state.interview_role = interview_role
                            st.session_state.interview_level = interview_level
                            st.session_state.interview_domain = interview_domain
                            st.success("✅ Study plan generated!")
                        except Exception as e:
                            if "429" in str(e) or "rate limit" in str(e).lower():
                                st.error("⚠️ **Groq Rate Limit Reached**\n\nPlease wait a moment and retry, or check your Groq plan and usage limits.")
                            else:
                                st.error(f"Error generating study plan: {str(e)}")
        
        if st.button("🎯 Generate Interview Questions", type="primary", use_container_width=True):
            if not all([interview_role, interview_domain]):
                st.error("⚠️ Please fill in Role and Domain.")
            else:
                with st.spinner("🔄 Generating interview questions..."):
                    try:
                        interview_questions = generate_interview_questions(
                            interview_role,
                            interview_level,
                            interview_domain,
                            num_questions,
                        )

                        st.session_state.current_questions = interview_questions
                        st.session_state.question_count = num_questions
                        st.session_state.interview_role = interview_role
                        st.session_state.interview_level = interview_level
                        st.session_state.interview_domain = interview_domain
                        st.session_state.answer_feedback = {}
                        st.session_state.answer_transcripts = {}
                        st.session_state.question_audio = {}
                        st.session_state.feedback_audio = {}
                        st.success("✅ Interview questions generated!")

                    except Exception as e:
                        if "429" in str(e) or "rate limit" in str(e).lower():
                            st.error("⚠️ **Groq Rate Limit Reached**\n\nPlease wait a moment and retry, or check your Groq plan and usage limits.")
                        else:
                            st.error(f"Error generating questions: {str(e)}")

        if st.session_state.current_questions:
            render_interview_answer_section(
                st.session_state.current_questions,
                st.session_state.interview_role,
                st.session_state.interview_level,
                st.session_state.interview_domain,
                voice_mode=False,
                prefix="text",
            )

        if st.session_state.study_plan:
            st.markdown("---")
            st.subheader("📘 Study Concepts & Topic Preparation")
            if st.session_state.interview_role and st.session_state.interview_domain:
                st.caption(
                    f"Learning path for {st.session_state.interview_role} ({st.session_state.interview_level}) in {st.session_state.interview_domain}"
                )
            st.markdown(st.session_state.study_plan)

    with tab3:
        st.subheader("🎙️ Voice AI Mock Interview")
        st.write("Practice a live one-question-at-a-time interview where the AI listens to your answer and asks the next question on the spot.")
        st.markdown("---")

        vcol1, vcol2, vcol3 = st.columns(3)

        with vcol1:
            voice_role = st.text_input(
                "Target Role *",
                value=st.session_state.voice_interview_role or "",
                placeholder="e.g., Frontend Developer",
                key="voice_role_input",
            )

        with vcol2:
            default_voice_level = st.session_state.voice_interview_level or "Intermediate"
            voice_level = st.selectbox(
                "Experience Level *",
                ["Beginner", "Intermediate", "Advanced", "Expert"],
                index=["Beginner", "Intermediate", "Advanced", "Expert"].index(default_voice_level),
                key="voice_level_input",
            )

        with vcol3:
            voice_domain = st.text_input(
                "Domain/Tech Stack *",
                value=st.session_state.voice_interview_domain or "",
                placeholder="e.g., React, UI performance, accessibility",
                key="voice_domain_input",
            )

        st.info("🎙️ The AI asks one question at a time and continues the interview naturally based on your answers until you stop it.")

        controls_col1, controls_col2 = st.columns(2)

        with controls_col1:
            if st.button("🎧 Start Live Interview", type="primary", use_container_width=True):
                if not all([voice_role, voice_domain]):
                    st.error("⚠️ Please fill in Role and Domain.")
                else:
                    with st.spinner("🔄 Starting live interview..."):
                        try:
                            first_question = start_live_voice_interview(
                                voice_role,
                                voice_level,
                                voice_domain,
                            )
                            st.session_state.voice_interview_role = voice_role
                            st.session_state.voice_interview_level = voice_level
                            st.session_state.voice_interview_domain = voice_domain
                            st.session_state.voice_live_round = 1
                            st.session_state.voice_live_question = first_question
                            st.session_state.voice_live_history = []
                            st.session_state.voice_live_messages = [
                                {"speaker": "AI Interviewer", "text": first_question}
                            ]
                            st.session_state.voice_live_feedback = None
                            st.session_state.voice_live_transcript = None
                            st.session_state["live_voice_text_notes_1"] = ""
                            st.session_state.voice_live_complete = False
                            st.session_state.voice_live_active = True
                            st.session_state.voice_live_feedback_audio = None
                            st.session_state.voice_live_pending_autoplay_turn = 1
                            st.session_state.voice_live_last_autoplayed_turn = 0
                            try:
                                st.session_state.voice_live_question_audio = generate_speech_audio(first_question)
                            except Exception as audio_error:
                                st.session_state.voice_live_question_audio = None
                                st.session_state.voice_live_pending_autoplay_turn = None
                                st.warning(str(audio_error))
                            st.success("✅ Live voice interview started!")
                            st.rerun()
                        except Exception as e:
                            if "429" in str(e) or "rate limit" in str(e).lower():
                                st.error("⚠️ **Groq Rate Limit Reached**\n\nPlease wait a moment and retry, or check your Groq plan and usage limits.")
                            else:
                                st.error(f"Error starting live interview: {str(e)}")

        with controls_col2:
            if st.button("🛑 Stop Interview", use_container_width=True):
                if st.session_state.voice_live_history:
                    with st.spinner("Preparing final interview summary..."):
                        try:
                            final_summary = finish_live_voice_interview(
                                st.session_state.voice_interview_role,
                                st.session_state.voice_interview_level,
                                st.session_state.voice_interview_domain,
                                st.session_state.voice_live_history,
                            )
                            st.session_state.voice_live_feedback = final_summary
                            try:
                                st.session_state.voice_live_feedback_audio = generate_speech_audio(final_summary[:1800])
                            except Exception as audio_error:
                                st.session_state.voice_live_feedback_audio = None
                                st.warning(str(audio_error))
                            st.session_state.voice_live_complete = True
                        except Exception as e:
                            st.error(f"Error finishing interview: {str(e)}")
                st.session_state.voice_live_active = False
                st.session_state.voice_live_question = None
                st.session_state.voice_live_question_audio = None
                st.session_state.voice_live_pending_autoplay_turn = None
                st.rerun()

        if st.session_state.voice_live_active and st.session_state.voice_live_question:
            st.markdown("---")
            st.subheader(f"Live Interview Turn {st.session_state.voice_live_round}")
            st.markdown("### Live Conversation")
            for message in st.session_state.voice_live_messages:
                if message["speaker"] == "AI Interviewer":
                    st.markdown(f"**AI Interviewer:** {message['text']}")
                else:
                    st.markdown(f"**You:** {message['text']}")
            st.markdown("---")
            if st.session_state.voice_live_question_audio:
                st.info("🔊 Use Play/Replay Question to hear the AI question before answering.")
            else:
                st.markdown(f"**Current Question:** {st.session_state.voice_live_question}")

            live_audio_col1, live_audio_col2 = st.columns(2)

            with live_audio_col1:
                if st.session_state.voice_live_question_audio:
                    should_autoplay = (
                        st.session_state.voice_live_pending_autoplay_turn == st.session_state.voice_live_round
                        and st.session_state.voice_live_last_autoplayed_turn < st.session_state.voice_live_round
                    )
                    st.audio(
                        st.session_state.voice_live_question_audio,
                        format="audio/wav",
                        autoplay=should_autoplay,
                    )
                    if should_autoplay:
                        st.session_state.voice_live_last_autoplayed_turn = st.session_state.voice_live_round
                        st.session_state.voice_live_pending_autoplay_turn = None
                    st.caption(f"Question text reference: {st.session_state.voice_live_question}")
                else:
                    st.warning("Voice output is not available right now, so the current question is shown as text.")

            with live_audio_col2:
                if st.button("🔊 Replay Question", key="replay_live_question", use_container_width=True):
                    with st.spinner("Generating question audio..."):
                        try:
                            st.session_state.voice_live_question_audio = generate_speech_audio(
                                st.session_state.voice_live_question
                            )
                        except Exception as e:
                            st.warning(str(e))

            current_turn = st.session_state.voice_live_round
            spoken_answer = st.audio_input(
                "Record your answer",
                key=f"live_voice_answer_{current_turn}",
                help="Answer the current interview question by voice.",
            )
            live_text_notes = st.text_area(
                "Optional text notes",
                placeholder="Add brief notes only if needed. The interview is designed for voice-first answers.",
                height=100,
                key=f"live_voice_text_notes_{current_turn}",
            )

            if st.session_state.voice_live_transcript:
                st.caption(f"Latest transcript: {st.session_state.voice_live_transcript}")

            if st.button("➡️ Submit Live Answer", type="primary", use_container_width=True):
                try:
                    final_answer = live_text_notes.strip()

                    if spoken_answer is not None:
                        with st.spinner("🔄 Transcribing your answer..."):
                            transcript = transcribe_audio(spoken_answer)
                            st.session_state.voice_live_transcript = transcript
                        if transcript:
                            final_answer = transcript if not final_answer else f"{transcript}\n\nExtra notes:\n{final_answer}"

                    if not final_answer.strip():
                        st.error("⚠️ Please record your answer before submitting.")
                    else:
                        current_question = st.session_state.voice_live_question
                        history_item = {
                            "round": st.session_state.voice_live_round,
                            "question": current_question,
                            "answer": final_answer,
                        }
                        st.session_state.voice_live_history.append(history_item)
                        st.session_state.voice_live_messages.append(
                            {"speaker": "You", "text": final_answer}
                        )

                        with st.spinner("🔄 Interviewer is responding..."):
                            next_question = continue_live_voice_interview(
                                st.session_state.voice_interview_role,
                                st.session_state.voice_interview_level,
                                st.session_state.voice_interview_domain,
                                st.session_state.voice_live_history,
                                st.session_state.voice_live_round,
                            )
                            st.session_state.voice_live_feedback = None
                            st.session_state.voice_live_feedback_audio = None
                            st.session_state.voice_live_round += 1
                            st.session_state.voice_live_transcript = None
                            st.session_state.voice_live_question = next_question
                            st.session_state.voice_live_messages.append(
                                {"speaker": "AI Interviewer", "text": next_question}
                            )
                            st.session_state[f"live_voice_text_notes_{st.session_state.voice_live_round}"] = ""
                            st.session_state.voice_live_pending_autoplay_turn = st.session_state.voice_live_round
                            try:
                                st.session_state.voice_live_question_audio = generate_speech_audio(next_question)
                            except Exception as audio_error:
                                st.session_state.voice_live_question_audio = None
                                st.session_state.voice_live_pending_autoplay_turn = None
                                st.warning(str(audio_error))
                            st.rerun()
                except Exception as e:
                    if "429" in str(e) or "rate limit" in str(e).lower():
                        st.error("⚠️ **Groq Rate Limit Reached**\n\nPlease wait a moment and retry, or check your Groq plan and usage limits.")
                    else:
                        st.error(f"Error during live interview: {str(e)}")

        if st.session_state.voice_live_feedback:
            st.markdown("---")
            st.subheader("🏁 Final Interview Summary")
            st.markdown(st.session_state.voice_live_feedback)

            if st.session_state.voice_live_feedback_audio:
                st.audio(
                    st.session_state.voice_live_feedback_audio,
                    format="audio/wav",
                    autoplay=True,
                )

        if st.session_state.voice_live_history:
            with st.expander("Interview Transcript", expanded=False):
                for item in st.session_state.voice_live_history:
                    st.markdown(f"**Round {item['round']}**")
                    st.markdown(f"**Question:** {item['question']}")
                    st.markdown(f"**Your answer:** {item['answer']}")
                    st.markdown("---")
    
    with tab4:
        st.subheader("⚙️ Settings - Groq API Configuration")
        st.markdown("---")

        st.write("Configure your Groq API key to use CareerPilot AI features including Resume Builder, Interview Prep, Study Plan, and Voice Mock Interview.")
        st.info("💡 **Tip**: Create and manage your Groq API keys at https://console.groq.com/keys")

        st.markdown("### Current API Key Status")
        if st.session_state.api_key:
            st.success(f"✅ **Active** - API key configured (last 4 chars: ...{st.session_state.api_key[-4:]})")
        else:
            st.warning("❌ **Inactive** - No API key set. AI-powered features will not work.")

        st.markdown("---")
        st.markdown("### Configure Your API Key")

        api_key_input = st.text_input(
            "Groq API Key",
            value=st.session_state.api_key,
            type="password",
            placeholder="Paste your Groq API key here",
            help="Your API key will only be stored in this session and not saved to disk"
        )

        col1, col2 = st.columns(2)

        with col1:
            if st.button("💾 Save API Key", type="primary", use_container_width=True):
                if not api_key_input:
                    st.error("⚠️ Please enter an API key")
                else:
                    st.session_state.api_key = api_key_input
                    st.success("✅ API key saved! Groq is now configured for the app.")
                    st.rerun()

        with col2:
            if st.button("🔄 Test API Key", type="secondary", use_container_width=True):
                if not api_key_input:
                    st.error("⚠️ Please enter an API key first")
                else:
                    with st.spinner("Testing API key..."):
                        try:
                            test_client = get_groq_client(api_key_input)
                            response = test_client.chat.completions.create(
                                model=GROQ_MODELS[0],
                                messages=[
                                    {"role": "system", "content": "You are a helpful assistant."},
                                    {"role": "user", "content": "Say 'API key is working!'"},
                                ],
                            )
                            if response.choices[0].message.content:
                                st.success("✅ **API key is valid and working!**")
                                st.session_state.api_key = api_key_input
                                st.rerun()
                        except Exception as e:
                            if "401" in str(e) or "403" in str(e) or "authentication" in str(e).lower():
                                st.error("❌ **Invalid Groq API Key** - Please check and try again at https://console.groq.com/keys")
                            elif "429" in str(e) or "rate limit" in str(e).lower():
                                st.error("⚠️ **Groq Rate Limit Reached** - Your key appears valid, but the current plan or rate limit blocked the test request.")
                                st.session_state.api_key = api_key_input
                            else:
                                st.error(f"❌ **Test Failed** - {str(e)}")

        st.markdown("---")
        st.markdown("### How to Get Your Groq API Key")

        st.write("""
1. **Visit Groq Console**: https://console.groq.com/keys
2. **Sign in** to your Groq account
3. **Create an API key**
4. **Copy** the generated key
5. **Paste** it in the field above
6. **Click "Test API Key"** to verify it works
        """)

        st.markdown("### Models Used")
        st.caption("Primary: llama-3.3-70b-versatile")
        st.caption("Fallback: llama-3.1-8b-instant")
        st.caption("Backup: openai/gpt-oss-20b")

        st.info("📊 **Note**: Resume generation, interview question generation, study plan creation, speech transcription, and spoken feedback each make Groq API requests.")

        st.markdown("---")
        st.link_button("📖 View Groq Pricing", "https://groq.com/pricing")
