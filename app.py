import streamlit as st
import os
import tempfile
from database import TalentDB
import parser
import matcher
import interview
import llm_client
import base64
import io
import requests
import json
from datetime import datetime
import streamlit.components.v1 as components
from streamlit_mic_recorder import mic_recorder
from streamlit_geolocation import streamlit_geolocation

# =====================================================
# PAGE CONFIGURATION
# =====================================================

st.set_page_config(
    page_title="Talent AI - Smart Hiring Platform",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =====================================================
# CUSTOM CSS FOR MODERN UI & SIDEBAR
# =====================================================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap');

html, body, [class*="css"] {
    font-family: 'Plus Jakarta Sans', sans-serif;
    font-size: 14px !important;
}

/* Sidebar styling */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0f172a 0%, #1e1b4b 100%);
    border-right: 1px solid rgba(255, 255, 255, 0.08);
}

.sidebar-brand {
    background: linear-gradient(135deg, #6366f1, #a855f7);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    font-weight: 800;
    font-size: 1.5rem;
    margin-bottom: 0px;
}

.sidebar-badge {
    background: rgba(99, 102, 241, 0.15);
    border: 1px solid rgba(99, 102, 241, 0.3);
    color: #818cf8;
    padding: 4px 10px;
    border-radius: 9999px;
    font-size: 0.75rem;
    font-weight: 600;
    display: inline-block;
    margin-bottom: 15px;
}

.step-card {
    background: rgba(30, 41, 59, 0.5);
    border: 1px solid rgba(255, 255, 255, 0.06);
    border-radius: 10px;
    padding: 12px;
    margin-bottom: 8px;
}

.step-card-active {
    background: linear-gradient(135deg, rgba(99, 102, 241, 0.2), rgba(168, 85, 247, 0.2));
    border: 1px solid rgba(99, 102, 241, 0.4);
    border-radius: 10px;
    padding: 12px;
    margin-bottom: 8px;
}

.main-header {
    background: linear-gradient(135deg, #6366f1, #a855f7);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    font-weight: 800;
    font-size: 2.2rem;
    margin-bottom: 5px;
}

.sub-header {
    color: #94a3b8;
    font-size: 0.95rem;
    margin-bottom: 25px;
}

.role-card {
    background: rgba(30, 41, 59, 0.45);
    backdrop-filter: blur(8px);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 12px;
    padding: 20px;
    margin-bottom: 15px;
    transition: all 0.2s ease;
}

.role-card:hover {
    border-color: rgba(99, 102, 241, 0.4);
}

.question-box {
    background: linear-gradient(135deg, rgba(30, 41, 59, 0.8), rgba(15, 23, 42, 0.9));
    border: 1px solid rgba(99, 102, 241, 0.3);
    border-radius: 12px;
    padding: 24px;
    margin-bottom: 20px;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
}

.score-tag {
    background: linear-gradient(135deg, #22c55e, #16a34a);
    color: white;
    padding: 4px 12px;
    border-radius: 9999px;
    font-weight: 700;
    font-size: 0.85rem;
}
</style>
""", unsafe_allow_html=True)

# =====================================================
# INITIALIZE DATABASE & SESSION STATE
# =====================================================

@st.cache_resource(show_spinner=False)
def get_db():
    db = TalentDB()
    db.seed_roles()
    return db

def text_to_speech_gtts(text):
    """
    Generates ultra-realistic, human-like neural voice MP3 audio using Microsoft Azure Neural TTS (edge-tts).
    Falls back gracefully to gTTS if edge-tts is unavailable.
    """
    import asyncio
    try:
        import edge_tts
        async def _async_generate():
            communicate = edge_tts.Communicate(text, "en-US-AriaNeural")
            audio_data = b""
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_data += chunk["data"]
            return audio_data

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        audio_bytes = loop.run_until_complete(_async_generate())
        loop.close()
        if audio_bytes:
            return audio_bytes
    except Exception as e:
        print(f"Error in edge-tts neural voice generation: {e}")

    try:
        from gtts import gTTS
        import io
        tts = gTTS(text=text, lang='en', tld='co.uk')
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        fp.seek(0)
        return fp.read()
    except Exception as e:
        print(f"Error generating fallback gTTS audio: {e}")
        return None

def get_geolocation_location(location_data):
    """
    Resolves browser coordinates to a city/country via Nominatim API,
    falling back to IP Geolocation if coordinates are not available.
    """
    pass

db = get_db()

# Initialize session state variables
if "candidate_id" not in st.session_state:
    st.session_state.candidate_id = None
if "candidate_profile" not in st.session_state:
    st.session_state.candidate_profile = None
if "resume_text" not in st.session_state:
    st.session_state.resume_text = ""
if "matched_roles" not in st.session_state:
    st.session_state.matched_roles = []
if "selected_role" not in st.session_state:
    st.session_state.selected_role = None
if "qas_history" not in st.session_state:
    st.session_state.qas_history = []
if "current_question" not in st.session_state:
    st.session_state.current_question = None
if "interview_finished" not in st.session_state:
    st.session_state.interview_finished = False
if "evaluation_report" not in st.session_state:
    st.session_state.evaluation_report = None
if "nav_page" not in st.session_state:
    st.session_state.nav_page = "Upload Resume"

# =====================================================
# SIDEBAR NAVIGATION & BRANDING
# =====================================================

with st.sidebar:
    st.markdown('<div class="sidebar-brand">Talent AI</div>', unsafe_allow_html=True)
    st.markdown('<div class="sidebar-badge">Candidate Portal</div>', unsafe_allow_html=True)
    st.markdown("---")

    # Navigation buttons
    st.subheader("🧭 Navigation")
    if st.button("📄 1. Upload Resume", use_container_width=True, type="primary" if st.session_state.nav_page == "Upload Resume" else "secondary"):
        st.session_state.nav_page = "Upload Resume"
        st.rerun()

    if st.button("🎤 2. Take / Resume Interview", use_container_width=True, type="primary" if st.session_state.nav_page == "Take / Resume Interview" else "secondary"):
        st.session_state.nav_page = "Take / Resume Interview"
        st.rerun()

    st.markdown("---")

    # Active Candidate Status Badge
    if st.session_state.candidate_profile:
        cand_name = st.session_state.candidate_profile.get("name", "Active Candidate")
        st.markdown("### 👤 Active Candidate")
        st.success(f"**{cand_name}**")
        if st.session_state.selected_role:
            st.caption(f"Role: **{st.session_state.selected_role.get('job_role')}**")
        if st.button("🚪 Clear & Start Fresh", use_container_width=True):
            st.session_state.candidate_id = None
            st.session_state.candidate_profile = None
            st.session_state.selected_role = None
            st.session_state.qas_history = []
            st.session_state.current_question = None
            st.session_state.interview_finished = False
            st.session_state.evaluation_report = None
            st.session_state.nav_page = "Upload Resume"
            st.rerun()
        st.markdown("---")

    # Resume In-Progress Interview Selector
    st.markdown("### 🔁 Resume Existing Application")
    in_progress_candidates = list(db.candidates_col.find({"interview_status": {"$in": ["IN_PROGRESS", "PENDING"]}}))
    
    if in_progress_candidates:
        cand_options = {"Select candidate to resume...": None}
        for c in in_progress_candidates:
            c_name = c.get("personal_info", {}).get("name", "Unnamed Candidate")
            c_role = c.get("selected_role") or "No Role Selected"
            cand_options[f"{c_name} ({c_role})"] = c
            
        selected_cand_label = st.selectbox("Choose Candidate", list(cand_options.keys()))
        selected_cand_doc = cand_options[selected_cand_label]
        
        if selected_cand_doc and st.button("▶️ Resume Selected Interview", use_container_width=True):
            st.session_state.candidate_id = str(selected_cand_doc["_id"])
            st.session_state.candidate_profile = selected_cand_doc.get("personal_info", {})
            st.session_state.candidate_profile["skills"] = selected_cand_doc.get("extracted_skills", [])
            st.session_state.candidate_profile["projects"] = selected_cand_doc.get("projects", [])
            st.session_state.resume_text = selected_cand_doc.get("resume_text", "")
            st.session_state.qas_history = selected_cand_doc.get("qas", [])
            
            # Load role if selected
            role_name = selected_cand_doc.get("selected_role")
            if role_name:
                st.session_state.selected_role = db.get_role_by_name(role_name)
                
            st.session_state.interview_finished = (selected_cand_doc.get("interview_status") == "COMPLETED")
            st.session_state.nav_page = "Take / Resume Interview"
            st.rerun()
    else:
        st.caption("No pending interviews to resume.")

# =====================================================
# PAGE 1: UPLOAD RESUME & MATCH ROLES
# =====================================================

if st.session_state.nav_page == "Upload Resume":
    st.markdown('<div class="main-header">Smart Talent Sourcing</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Start a new application or restore an in-progress interview seamlessly.</div>', unsafe_allow_html=True)

    tab_new, tab_resume = st.tabs(["📄 Start New Application", "🔁 Resume Incomplete Interview"])

    with tab_new:
        uploaded_file = st.file_uploader("Upload Resume (PDF format)", type=["pdf"])

        if uploaded_file is not None:
            with st.spinner("📄 Reading PDF and extracting structured profile via AI..."):
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                    tmp.write(uploaded_file.read())
                    tmp_path = tmp.name

                resume_text = parser.extract_text_from_pdf(tmp_path)
                os.remove(tmp_path)

                if not resume_text:
                    st.error("Failed to extract text from the PDF. Please try another PDF.")
                else:
                    profile = parser.parse_resume_text_with_llm(resume_text)
                    st.session_state.resume_text = resume_text
                    st.session_state.candidate_profile = profile

                    # Perform BERT Semantic Reranking
                    with st.spinner("🤖 Computing BERT Vector Similarity with Job Roles..."):
                        all_roles = db.get_all_roles()
                        matched_roles = matcher.vector_search_jobs(resume_text, all_roles)
                        st.session_state.matched_roles = matched_roles
                        resume_emb = None

                    # Save candidate to MongoDB
                    cand_id = db.create_candidate(profile, resume_text, resume_emb)
                    st.session_state.candidate_id = cand_id
                    st.success("✅ Resume parsed and candidate profile created successfully!")

    with tab_resume:
        st.subheader("🔍 Resume Your Incomplete Interview")
        st.caption("Enter the email address registered on your application to restore your session.")
        
        email_input = st.text_input("Registered Email Address:", placeholder="candidate@example.com")
        if st.button("🔍 Find & Resume Interview", type="primary"):
            if not email_input.strip():
                st.warning("Please enter your registered email address.")
            else:
                with st.spinner("Searching database for active interview session..."):
                    cand_doc = db.find_incomplete_candidate_by_email(email_input)
                    if cand_doc:
                        st.session_state.candidate_id = str(cand_doc["_id"])
                        st.session_state.candidate_profile = cand_doc.get("personal_info", {})
                        st.session_state.candidate_profile["skills"] = cand_doc.get("extracted_skills", [])
                        st.session_state.candidate_profile["projects"] = cand_doc.get("projects", [])
                        st.session_state.resume_text = cand_doc.get("resume_text", "")
                        st.session_state.qas_history = cand_doc.get("qas", [])
                        
                        role_name = cand_doc.get("selected_role")
                        if role_name:
                            st.session_state.selected_role = db.get_role_by_name(role_name)
                            
                        st.session_state.interview_finished = (cand_doc.get("interview_status") == "COMPLETED")
                        st.session_state.nav_page = "Take / Resume Interview"
                        st.success("✅ Session restored successfully! Redirecting to your interview...")
                        st.rerun()
                    else:
                        st.warning("⚠️ No active in-progress interview was found for this email address. Please upload your resume to start a new application.")

    # Display Parsed Profile & Top Matched Roles
    if st.session_state.candidate_profile and st.session_state.matched_roles:
        st.markdown("---")
        col_prof, col_roles = st.columns([1, 1])

        with col_prof:
            st.subheader("📋 Parsed Candidate Profile")
            prof = st.session_state.candidate_profile
            st.write(f"**Name:** {prof.get('name', 'N/A')}")
            st.write(f"**Email:** `{prof.get('email', 'N/A')}`")
            st.write(f"**Phone:** `{prof.get('phone', 'N/A')}`")
            st.write(f"**Location:** {prof.get('current_location', 'N/A')}")
            st.write(f"**Years of Experience:** {prof.get('years_of_experience', 0.0)}")

            st.write("**Extracted Skills:**")
            skills = prof.get("skills", [])
            if skills:
                st.write(", ".join([f"`{s}`" for s in skills]))
            else:
                st.caption("No specific skills extracted.")

        with col_roles:
            st.subheader("🎯 Top 5 Recommended Job Roles")
            for idx, role_item in enumerate(st.session_state.matched_roles[:5]):
                role_name = role_item["job_role"]
                score = role_item["vector_score"]
                role_doc = role_item["role_document"]

                with st.container():
                    st.markdown(f"""
                    <div class="role-card">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <h4 style="margin: 0; color: #818cf8;">{role_name}</h4>
                            <span class="score-tag">Match: {score}%</span>
                        </div>
                        <p style="font-size: 0.85rem; color: #cbd5e1; margin-top: 8px;">
                            {role_doc.get("job_description", "")[:120]}...
                        </p>
                    </div>
                    """, unsafe_allow_html=True)

                    if st.button(f"Apply for {role_name}", key=f"apply_{idx}", type="primary", use_container_width=True):
                        st.session_state.selected_role = role_doc
                        # Update DB with selected role
                        db.update_selected_role(st.session_state.candidate_id, role_name)
                        st.session_state.nav_page = "Take / Resume Interview"
                        st.rerun()

# =====================================================
# PAGE 2: TAKE / RESUME INTERVIEW
# =====================================================

elif st.session_state.nav_page == "Take / Resume Interview":
    st.markdown('<div class="main-header">Voice Technical Interview</div>', unsafe_allow_html=True)

    if not st.session_state.candidate_id:
        st.warning("⚠️ No active candidate selected. Please upload a resume first or select an existing candidate from the sidebar.")
    elif not st.session_state.selected_role:
        st.info("ℹ️ Please select a job role on the 'Upload Resume' page before starting the interview.")
    else:
        role_doc = st.session_state.selected_role
        job_role_name = role_doc.get("job_role", "Target Role")
        job_desc = role_doc.get("job_description", "")

        # Check if interview is already finished
        if st.session_state.interview_finished or len(st.session_state.qas_history) >= 5:
            st.session_state.interview_finished = True
            st.markdown("### 🏆 Technical Interview Completed")
            st.success(f"Interview for **{job_role_name}** is completed! Generating final evaluation report...")

            # Run evaluation if not already computed
            if not st.session_state.evaluation_report:
                with st.spinner("🤖 LLM synthesizing technical skills and soft skills scorecard..."):
                    cand_name = st.session_state.candidate_profile.get("name", "Candidate")
                    eval_res = interview.evaluate_candidate(cand_name, job_role_name, st.session_state.qas_history)
                    st.session_state.evaluation_report = eval_res
                    # Save to MongoDB
                    db.save_evaluation(st.session_state.candidate_id, eval_res)

            report = st.session_state.evaluation_report
            if report:
                st.markdown("---")
                st.markdown("### 📊 Final AI Assessment Scorecard")
                col_r1, col_r2 = st.columns(2)

                with col_r1:
                    st.markdown(f"**Overall Recommendation:** `{report.get('recommendation', 'N/A')}`")
                    st.markdown(f"**Communication & Soft Skills Score:** **{report.get('soft_skills_score', 0.0)}%**")
                    st.markdown("**Technical Assessment Summary:**")
                    st.info(report.get("technical_summary", "Evaluation complete."))

                with col_r2:
                    st.markdown("**Communication & Style Summary:**")
                    st.success(report.get("soft_skill_summary", "Evaluation complete."))

                # Display Question Transcripts & Short Bulleted Feedback
                st.markdown("---")
                st.markdown("### 📝 Interview Transcript & Feedback")
                for idx, qa in enumerate(st.session_state.qas_history):
                    with st.expander(f"Q{idx+1}: {qa.get('question')}", expanded=True):
                        st.write(f"💬 **Answer:** *\"{qa.get('answer')}\"*")
                        st.markdown(f"**Feedback:**\n{qa.get('feedback', 'No feedback.')}")

        else:
            # INTERVIEW IN PROGRESS FLOW (MAX 5 QUESTIONS)
            q_num = len(st.session_state.qas_history) + 1
            st.write(f"Role: **{job_role_name}** | Question **{q_num} of 5**")
            st.progress(q_num / 5)

            # Generate Next Question if needed
            if not st.session_state.current_question:
                with st.spinner("🤖 AI Interviewer generating next role-specific question..."):
                    cand_skills = st.session_state.candidate_profile.get("skills", [])
                    cand_projects = st.session_state.candidate_profile.get("projects", [])
                    next_q = interview.generate_next_question(
                        job_role=job_role_name,
                        job_description=job_desc,
                        candidate_skills=cand_skills,
                        candidate_projects=cand_projects,
                        qas_history=st.session_state.qas_history
                    )
                    st.session_state.current_question = next_q

            question_text = st.session_state.current_question

            # Render Question Box
            st.markdown(f"""
            <div class="question-box">
                <span style="color: #6366f1; font-weight: 700; font-size: 0.85rem; text-transform: uppercase;">Question {q_num} of 5</span>
                <h3 style="margin-top: 5px; color: #f8fafc;">{question_text}</h3>
            </div>
            """, unsafe_allow_html=True)

            # Human-like Voice Reader (gTTS with Session State Caching & Autoplay)
            if st.session_state.get("tts_question_key") != question_text:
                st.session_state.current_tts_audio = text_to_speech_gtts(question_text)
                st.session_state.tts_question_key = question_text

            if st.session_state.get("current_tts_audio"):
                st.write("🔊 **AI Interviewer Audio (Natural Human Voice):**")
                st.audio(st.session_state.current_tts_audio, format="audio/mp3", autoplay=True)

            # Answer Input Methods: Voice or Text
            st.subheader("Your Answer")
            col_audio, col_skip = st.columns([3, 1])

            with col_audio:
                st.write("🎙️ **Record Voice Answer:**")
                audio = mic_recorder(
                    start_prompt="Start Recording 🔴",
                    stop_prompt="Stop & Transcribe ⏹️",
                    key=f"rec_{q_num}"
                )

            transcribed_text = ""
            if audio:
                st.audio(audio['bytes'], format='audio/wav')
                # Transcribe using SpeechRecognition
                with st.spinner("🎙️ Transcribing audio using SpeechRecognition..."):
                    try:
                        import speech_recognition as sr
                        r = sr.Recognizer()
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_wav:
                            tmp_wav.write(audio['bytes'])
                            tmp_wav_path = tmp_wav.name
                        
                        with sr.AudioFile(tmp_wav_path) as source:
                            audio_data = r.record(source)
                            transcribed_text = r.recognize_google(audio_data)
                        os.remove(tmp_wav_path)
                        st.success(f"Transcribed: *\"{transcribed_text}\"*")
                    except Exception as err:
                        st.warning("Could not transcribe speech automatically. You can type your answer below.")

            answer_input = st.text_area("Or type your response:", value=transcribed_text, height=120, key=f"txt_{q_num}")

            col_submit, col_skip_btn = st.columns([2, 1])

            with col_submit:
                if st.button("📤 Submit Answer", type="primary", use_container_width=True):
                    if not answer_input.strip():
                        st.warning("Please provide or record an answer before submitting, or click Skip.")
                    else:
                        with st.spinner("🤖 Evaluating answer accuracy and soft skills..."):
                            t_score, s_score, feedback, extra_eval = interview.evaluate_single_qa(job_role_name, question_text, answer_input)
                            
                            # Encode audio bytes to MP3 Base64 if available
                            b64_audio = ""
                            if audio:
                                try:
                                    import lameenc
                                    encoder = lameenc.Encoder()
                                    encoder.set_bit_rate(64)
                                    encoder.set_in_sample_rate(16000)
                                    encoder.set_channels(1)
                                    encoder.set_quality(5)
                                    mp3_data = encoder.encode(audio['bytes']) + encoder.flush()
                                    b64_audio = base64.b64encode(mp3_data).decode('utf-8')
                                except Exception:
                                    b64_audio = base64.b64encode(audio['bytes']).decode('utf-8')

                            qa_record = {
                                "question": question_text,
                                "answer": answer_input,
                                "technical_score": t_score,
                                "soft_skills_score": s_score,
                                "feedback": feedback,
                                "extra_eval": extra_eval,
                                "audio_b64": b64_audio
                            }
                            
                            st.session_state.qas_history.append(qa_record)
                            db.append_qa(st.session_state.candidate_id, qa_record)
                            
                            st.session_state.current_question = None
                            if len(st.session_state.qas_history) >= 5:
                                st.session_state.interview_finished = True
                                cand_name = st.session_state.candidate_profile.get("name", "Candidate") if st.session_state.candidate_profile else "Candidate"
                                eval_res = interview.evaluate_candidate(cand_name, job_role_name, st.session_state.qas_history)
                                st.session_state.evaluation_report = eval_res
                                db.save_evaluation(st.session_state.candidate_id, eval_res)
                            st.rerun()

            with col_skip_btn:
                # SKIP QUESTION BUTTON (Requirement 5)
                if st.button("⏭️ Skip Question", use_container_width=True):
                    qa_record = {
                        "question": question_text,
                        "answer": "[Question Skipped]",
                        "technical_score": 0.0,
                        "soft_skills_score": 0.0,
                        "feedback": "• Question was skipped by the candidate.",
                        "extra_eval": {},
                        "audio_b64": ""
                    }
                    st.session_state.qas_history.append(qa_record)
                    db.append_qa(st.session_state.candidate_id, qa_record)
                    
                    st.session_state.current_question = None
                    if len(st.session_state.qas_history) >= 5:
                        st.session_state.interview_finished = True
                        cand_name = st.session_state.candidate_profile.get("name", "Candidate") if st.session_state.candidate_profile else "Candidate"
                        eval_res = interview.evaluate_candidate(cand_name, job_role_name, st.session_state.qas_history)
                        st.session_state.evaluation_report = eval_res
                        db.save_evaluation(st.session_state.candidate_id, eval_res)
                    st.rerun()
