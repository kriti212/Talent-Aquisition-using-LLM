import streamlit as st
import os
import tempfile
from database import TalentDB
import parser
import matcher
import interview
import llm_client
import config
import base64
import io
import requests
import json
from datetime import datetime
from gtts import gTTS
from streamlit_mic_recorder import mic_recorder
from streamlit_geolocation import streamlit_geolocation

# =====================================================
# GEOLOCATION RESOLVER
# =====================================================

def get_geolocation_location(location_data):
    """
    Resolves browser coordinates to a city/country via Nominatim API,
    falling back to IP Geolocation if coordinates are not available.
    """
    if location_data and location_data.get("latitude") and location_data.get("longitude"):
        lat = location_data["latitude"]
        lon = location_data["longitude"]
        try:
            url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lon}"
            headers = {"User-Agent": "TalentAcquisitionAppV2/2.0"}
            r = requests.get(url, headers=headers, timeout=5)
            if r.status_code == 200:
                address = r.json().get("address", {})
                city = address.get("city") or address.get("town") or address.get("village") or address.get("suburb", "")
                country = address.get("country", "")
                if city and country:
                    return f"{city}, {country}"
                elif country:
                    return country
        except Exception as e:
            print(f"Error reverse geocoding browser coordinates: {e}")
            
    # Fallback to IP geolocation
    try:
        r = requests.get("http://ip-api.com/json/", timeout=5)
        if r.status_code == 200:
            data = r.json()
            city = data.get("city", "")
            country = data.get("country", "")
            if city and country:
                return f"{city}, {country}"
    except Exception as e:
        print(f"Error in fallback IP Geolocation: {e}")
        
    return ""

# =====================================================
# HUMAN-LIKE VOICE SYNTHESIS (gTTS)
# =====================================================

@st.cache_data(show_spinner=False)
def generate_gtts_audio(text):
    """
    Generates natural human-like MP3 audio bytes using gTTS (Google Text-to-Speech).
    Cached to prevent duplicate API requests.
    """
    if not text:
        return None
    try:
        clean_text = text.strip().replace("\n", " ")
        tts = gTTS(text=clean_text, lang='en', slow=False)
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        fp.seek(0)
        return fp.getvalue()
    except Exception as e:
        print(f"Error generating gTTS audio: {e}")
        return None

# =====================================================
# AUDIO RECORDING COMPRESSION & SPEECH RECOGNITION
# =====================================================

def google_speech_to_text(audio_bytes: bytes) -> str:
    """Fallback: Google Speech Recognition for voice input."""
    try:
        import speech_recognition as sr
        recognizer = sr.Recognizer()
        with sr.AudioFile(io.BytesIO(audio_bytes)) as source:
            audio_data = recognizer.record(source)
            text = recognizer.recognize_google(audio_data)
            return text
    except sr.UnknownValueError:
        st.error("Could not understand audio clearly. Please try speaking again or typing.")
        return ""
    except Exception as e:
        st.error(f"Error transcribing voice: {e}")
        return ""

def compress_wav(wav_bytes):
    try:
        import wave
        import audioop
        in_io = io.BytesIO(wav_bytes)
        with wave.open(in_io, 'rb') as wav_in:
            params = wav_in.getparams()
            nchannels, sampwidth, framerate, nframes = params[:4]
            raw_frames = wav_in.readframes(nframes)
            
        if nchannels > 1:
            raw_frames = audioop.tomono(raw_frames, sampwidth, 1, 1)
            nchannels = 1
            
        target_rate = 16000
        if framerate != target_rate:
            raw_frames, _ = audioop.ratecv(raw_frames, sampwidth, nchannels, framerate, target_rate, None)
            framerate = target_rate
            
        out_io = io.BytesIO()
        with wave.open(out_io, 'wb') as wav_out:
            wav_out.setnchannels(nchannels)
            wav_out.setsampwidth(sampwidth)
            wav_out.setframerate(framerate)
            wav_out.writeframes(raw_frames)
            
        return out_io.getvalue()
    except Exception as e:
        print(f"Error compressing WAV: {e}")
        return wav_bytes

def wav_to_mp3(wav_bytes):
    try:
        import wave
        import lameenc
        wav_io = io.BytesIO(wav_bytes)
        with wave.open(wav_io, 'rb') as wav_file:
            num_channels = wav_file.getnchannels()
            sample_width = wav_file.getsampwidth()
            sample_rate = wav_file.getframerate()
            num_frames = wav_file.getnframes()
            pcm_data = wav_file.readframes(num_frames)
            
        encoder = lameenc.Encoder()
        encoder.set_bit_rate(128)
        encoder.set_in_sample_rate(sample_rate)
        encoder.set_channels(num_channels)
        encoder.set_quality(2)
        
        mp3_data = encoder.encode(pcm_data)
        mp3_data += encoder.flush()
        return mp3_data
    except Exception as e:
        print(f"Error encoding to MP3: {e}")
        return wav_bytes

# =====================================================
# PAGE CONFIGURATION & CUSTOM CSS (PREMIUM DARK MODE)
# =====================================================

st.set_page_config(
    page_title="Talent AI - Candidate Portal",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap');

html, body, [class*="css"] {
    font-family: 'Plus Jakarta Sans', sans-serif;
    font-size: 14px !important;
}

/* Hide Streamlit Sidebar completely */
[data-testid="stSidebar"] {
    display: none !important;
}

.main-header {
    text-align: center;
    max-width: 800px;
    margin: 0 auto 2rem auto;
}

.main-title {
    background: linear-gradient(135deg, #6366f1, #a855f7);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    font-weight: 800;
    font-size: 2.4rem;
    margin-bottom: 0.5rem;
    text-align: center;
}

.subtitle {
    color: #94a3b8;
    font-size: 1.05rem;
    text-align: center;
    margin-bottom: 2rem;
}

.centered-container {
    max-width: 800px;
    margin: 0 auto;
    background: rgba(30, 41, 59, 0.45);
    backdrop-filter: blur(12px);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 16px;
    padding: 30px;
    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.25);
}

.role-card {
    background: rgba(30, 41, 59, 0.45);
    backdrop-filter: blur(8px);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 12px;
    padding: 20px;
    margin-bottom: 15px;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.role-card:hover {
    transform: translateY(-3px);
    border-color: #6366f1;
    box-shadow: 0 10px 25px rgba(99, 102, 241, 0.15);
}

.score-badge {
    background: linear-gradient(135deg, #3b82f6, #1d4ed8);
    color: white;
    padding: 4px 12px;
    border-radius: 9999px;
    font-size: 0.85rem;
    font-weight: 700;
}

.chat-bubble {
    padding: 16px 20px;
    border-radius: 14px;
    margin-bottom: 14px;
    line-height: 1.6;
}

.chat-interviewer {
    background-color: rgba(99, 102, 241, 0.12);
    border: 1px solid rgba(99, 102, 241, 0.25);
    border-top-left-radius: 4px;
}

.chat-candidate {
    background-color: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-top-right-radius: 4px;
}

.nav-link {
    display: inline-block;
    color: #818cf8;
    text-decoration: none;
    font-weight: 600;
    margin-bottom: 15px;
}
</style>
""", unsafe_allow_html=True)

# =====================================================
# INITIALIZE SESSION STATE
# =====================================================

if "step" not in st.session_state:
    st.session_state.step = "UPLOAD"
if "candidate_id" not in st.session_state:
    st.session_state.candidate_id = None
if "geolocation_data" not in st.session_state:
    st.session_state.geolocation_data = None
if "parsed_profile" not in st.session_state:
    st.session_state.parsed_profile = None
if "recommended_roles" not in st.session_state:
    st.session_state.recommended_roles = []
if "selected_role" not in st.session_state:
    st.session_state.selected_role = None
if "interview_qas" not in st.session_state:
    st.session_state.interview_qas = []
if "current_question" not in st.session_state:
    st.session_state.current_question = ""
if "selected_model" not in st.session_state:
    st.session_state.selected_model = config.LLM_MODEL
if "candidate_answer" not in st.session_state:
    st.session_state.candidate_answer = ""
if "voice_enabled" not in st.session_state:
    st.session_state.voice_enabled = True
if "current_audio_b64" not in st.session_state:
    st.session_state.current_audio_b64 = None

# =====================================================
# INITIALIZE DATABASE
# =====================================================

@st.cache_resource(show_spinner=False)
def get_db():
    db = TalentDB()
    db.seed_roles()
    return db

db = get_db()

# Top Navigation Header Link to Recruiter App
st.markdown("""
<div style="display: flex; justify-content: space-between; align-items: center; padding: 10px 0 20px 0;">
    <div style="display: flex; align-items: center; gap: 10px;">
        <svg width="36" height="36" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <defs>
                <linearGradient id="headerGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                    <stop offset="0%" stop-color="#6366f1" />
                    <stop offset="100%" stop-color="#a855f7" />
                </linearGradient>
            </defs>
            <rect width="24" height="24" rx="5" fill="url(#headerGrad)"/>
            <path d="M7 9C7 8.44772 7.44772 8 8 8H16C16.5523 8 17 8.44772 17 9V15C17 15.5523 16.5523 16 16 16H8C7.44772 16 7 15.5523 7 15V9Z" stroke="white" stroke-width="1.5" stroke-linejoin="round"/>
        </svg>
        <span style="font-size: 1.2rem; font-weight: 800; color: #f8fafc;">Talent AI</span>
    </div>
    <a href="http://localhost:8502" target="_blank" style="color: #818cf8; text-decoration: none; font-weight: 600; font-size: 0.9rem;">
        📊 Open HR Admin Portal ↗
    </a>
</div>
""", unsafe_allow_html=True)

# =====================================================
# STEP 1: SINGLE-COLUMN CENTERED UPLOAD & RESUME TABS
# =====================================================

if st.session_state.step == "UPLOAD":
    st.markdown('<div class="main-title">AI Talent Acquisition Portal</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">Upload your resume to begin an automated technical interview, or resume an incomplete interview session.</div>', unsafe_allow_html=True)
    
    # Single-column centered UI card
    st.markdown('<div class="centered-container">', unsafe_allow_html=True)
    
    tab_new, tab_resume = st.tabs(["🚀 Start New Interview", "🔄 Resume Incomplete Interview"])
    
    # -------------------------------------------------
    # TAB 1: START NEW INTERVIEW
    # -------------------------------------------------
    with tab_new:
        st.subheader("Upload Candidate Resume")
        st.caption("Supported formats: PDF, TXT (Max size 10MB)")
        
        uploaded_file = st.file_uploader(
            "Upload Resume File",
            type=["pdf", "txt"],
            label_visibility="collapsed"
        )
        
        if uploaded_file is not None:
            file_size_mb = len(uploaded_file.getvalue()) / (1024 * 1024)
            if file_size_mb > 10.0:
                st.error("File exceeds 10MB limit. Please upload a smaller file.")
            else:
                if st.button("Process Resume & Match Roles", type="primary", use_container_width=True):
                    with st.spinner("Extracting candidate profile and calculating role recommendations..."):
                        file_ext = uploaded_file.name.split(".")[-1]
                        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file_ext}") as tmp:
                            tmp.write(uploaded_file.getvalue())
                            tmp_path = tmp.name
                            
                        try:
                            all_roles = db.get_all_roles()
                            if not all_roles:
                                st.error("No job roles found in database.")
                                os.unlink(tmp_path)
                            else:
                                geo_address = get_geolocation_location(None)
                                raw_text, resume_embedding, parsed_profile, recommended = parser.process_resume_hybrid_rerank(
                                    tmp_path, 
                                    file_ext, 
                                    all_roles,
                                    model_name=st.session_state.selected_model,
                                    current_location=geo_address
                                )
                                os.unlink(tmp_path)
                                
                                st.session_state.parsed_profile = parsed_profile
                                st.session_state.recommended_roles = recommended
                                
                                cand_id = db.create_candidate(parsed_profile, raw_text, resume_embedding=resume_embedding)
                                st.session_state.candidate_id = cand_id
                                st.session_state.step = "SELECT_ROLE"
                                st.rerun()
                        except Exception as e:
                            st.error(f"Error processing resume: {str(e)}")
                            if os.path.exists(tmp_path):
                                os.unlink(tmp_path)

    # -------------------------------------------------
    # TAB 2: RESUME INCOMPLETE INTERVIEW (CONNECTION RESTORATION)
    # -------------------------------------------------
    with tab_resume:
        st.subheader("Restore Incomplete Interview Session")
        st.caption("If your interview was interrupted by a network issue or power loss, enter your email address to pick up right where you left off.")
        
        resume_email = st.text_input("Enter Registered Email Address", placeholder="e.g. rahul.sharma@example.com")
        
        if st.button("Restore Active Interview", type="primary", use_container_width=True):
            if not resume_email.strip():
                st.warning("Please enter your email address.")
            else:
                with st.spinner("Searching for active interview session in MongoDB..."):
                    candidate_doc = db.find_incomplete_candidate_by_email(resume_email)
                    if not candidate_doc:
                        st.error("❌ No active, incomplete interview session found for this email address. Please start a new interview.")
                    else:
                        # Restore complete state into session_state
                        st.session_state.candidate_id = str(candidate_doc["_id"])
                        st.session_state.selected_role = candidate_doc.get("selected_role")
                        st.session_state.parsed_profile = {
                            "name": candidate_doc.get("personal_info", {}).get("name", "Candidate"),
                            "email": candidate_doc.get("personal_info", {}).get("email", ""),
                            "phone": candidate_doc.get("personal_info", {}).get("phone", ""),
                            "current_location": candidate_doc.get("personal_info", {}).get("current_location", ""),
                            "skills": candidate_doc.get("extracted_skills", []),
                            "projects": candidate_doc.get("projects", []),
                            "years_of_experience": candidate_doc.get("years_of_experience", 0.0)
                        }
                        
                        existing_qas = candidate_doc.get("qas", [])
                        st.session_state.interview_qas = existing_qas
                        
                        if existing_qas:
                            # If last question has answer, generate next question or resume
                            last_qa = existing_qas[-1]
                            if last_qa.get("answer"):
                                role_data = db.get_role_by_name(candidate_doc.get("selected_role"))
                                role_desc = role_data.get("job_description", "") if role_data else ""
                                next_q = interview.generate_next_question(
                                    candidate_doc.get("selected_role"),
                                    role_desc,
                                    st.session_state.parsed_profile.get("skills", []),
                                    st.session_state.parsed_profile.get("projects", []),
                                    existing_qas,
                                    model_name=st.session_state.selected_model
                                )
                                db.add_interview_qa(st.session_state.candidate_id, next_q)
                                st.session_state.interview_qas.append({"question": next_q, "answer": ""})
                                st.session_state.current_question = next_q
                            else:
                                st.session_state.current_question = last_qa.get("question", "")
                        else:
                            # Generate first question
                            role_data = db.get_role_by_name(candidate_doc.get("selected_role"))
                            role_desc = role_data.get("job_description", "") if role_data else ""
                            first_q = interview.generate_next_question(
                                candidate_doc.get("selected_role"),
                                role_desc,
                                st.session_state.parsed_profile.get("skills", []),
                                st.session_state.parsed_profile.get("projects", []),
                                [],
                                model_name=st.session_state.selected_model
                            )
                            db.add_interview_qa(st.session_state.candidate_id, first_q)
                            st.session_state.interview_qas = [{"question": first_q, "answer": ""}]
                            st.session_state.current_question = first_q

                        st.session_state.step = "INTERVIEW"
                        st.success(f"Welcome back {candidate_doc.get('personal_info', {}).get('name')}! Resuming your interview...")
                        st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)

# =====================================================
# STEP 2: SELECT ROLE
# =====================================================

elif st.session_state.step == "SELECT_ROLE":
    st.markdown('<div class="main-title">Select Job Role</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">Review your extracted profile and pick the target role to interview for.</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("Parsed Profile")
        profile = st.session_state.parsed_profile
        st.text_input("Name", value=profile.get("name", ""), disabled=True)
        st.text_input("Email", value=profile.get("email", ""), disabled=True)
        st.text_input("Phone", value=profile.get("phone", ""), disabled=True)
        st.text_input("Location", value=profile.get("current_location", ""), disabled=True)
        st.number_input("Experience (Years)", value=float(profile.get("years_of_experience") or 0.0), disabled=True)
        st.markdown("**Skills Found:**")
        st.write(", ".join(profile.get("skills", [])) or "None")
        
    with col2:
        st.subheader("Recommended Roles (Top 5 Vector Matches)")
        for idx, rec in enumerate(st.session_state.recommended_roles):
            role_name = rec["job_role"]
            score = rec["match_score"]
            desc = rec["job_description"]
            skills_req = rec["skills"]
            
            with st.container():
                st.markdown(f"""
                <div class="role-card">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <h4 style="margin: 0; color: #818cf8;">{role_name}</h4>
                        <span class="score-badge">Match: {score}%</span>
                    </div>
                    <p style="font-size: 0.9rem; margin-top: 10px; color: #cbd5e1;">{desc[:220]}...</p>
                    <div style="font-size: 0.8rem; color: #94a3b8;">
                        <b>Key Skills:</b> {", ".join([s.get("skill_name", "") for s in skills_req])}
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                if st.button(f"Apply & Begin Technical Interview - {role_name}", key=f"btn_role_{idx}"):
                    db.update_candidate_role(st.session_state.candidate_id, role_name)
                    st.session_state.selected_role = role_name
                    
                    with st.spinner("Generating your first interview question..."):
                        first_q = interview.generate_next_question(
                            role_name, 
                            desc, 
                            profile.get("skills", []), 
                            profile.get("projects", []), 
                            [], 
                            model_name=st.session_state.selected_model
                        )
                        st.session_state.current_question = first_q
                        db.add_interview_qa(st.session_state.candidate_id, first_q)
                        st.session_state.interview_qas = [{"question": first_q, "answer": ""}]
                        
                    st.session_state.step = "INTERVIEW"
                    st.rerun()

# =====================================================
# STEP 3: TECHNICAL INTERVIEW (gTTS VOICE & SKIP BUTTON)
# =====================================================

elif st.session_state.step == "INTERVIEW":
    role_name = st.session_state.selected_role
    role_data = db.get_role_by_name(role_name)
    role_desc = role_data.get("job_description", "") if role_data else ""
    
    st.markdown(f'<div class="main-title">Interview: {role_name}</div>', unsafe_allow_html=True)
    
    q_count = len(st.session_state.interview_qas)
    progress_val = q_count / 5.0
    st.progress(progress_val, text=f"Question {q_count} of 5")
    
    # -------------------------------------------------
    # INLINE CONTROLS HEADER (Voice toggle & Replay)
    # -------------------------------------------------
    col_ctrl1, col_ctrl2 = st.columns([3, 1])
    with col_ctrl1:
        st.session_state.voice_enabled = st.checkbox(
            "🔊 Enable Human-like Voice Reader (gTTS)",
            value=st.session_state.voice_enabled,
            help="Automatically play natural human voice readout for each question."
        )
    with col_ctrl2:
        if st.button("🔊 Replay Question", use_container_width=True):
            st.session_state.last_played_audio_text = None # Force replay
            
    st.write("---")
    st.write("### Conversation History")
    
    # Render Q&A bubbles
    for qa in st.session_state.interview_qas:
        st.markdown(f"""
        <div class="chat-bubble chat-interviewer">
            <b>Interviewer (AI)</b><br/>{qa['question']}
        </div>
        """, unsafe_allow_html=True)
        
        if qa.get("answer"):
            ans_display = "⏩ *Question Skipped*" if qa.get("answer") == "Skipped" else qa['answer']
            st.markdown(f"""
            <div class="chat-bubble chat-candidate">
                <b>You</b><br/>{ans_display}
            </div>
            """, unsafe_allow_html=True)

    # -------------------------------------------------
    # HUMAN-LIKE VOICE READ-OUT (gTTS)
    # -------------------------------------------------
    if st.session_state.voice_enabled and st.session_state.current_question:
        mp3_audio = generate_gtts_audio(st.session_state.current_question)
        if mp3_audio:
            st.audio(mp3_audio, format="audio/mp3", autoplay=True)

    # -------------------------------------------------
    # CANDIDATE RESPONSE INPUT & SKIP BUTTON
    # -------------------------------------------------
    last_qa = st.session_state.interview_qas[-1]
    
    if not last_qa.get("answer"):
        st.write("🎙️ **Record Voice or Type Answer:**")
        col_rec, col_clear = st.columns([3, 1])
        
        with col_rec:
            audio = mic_recorder(
                start_prompt="🎙️ Start Recording",
                stop_prompt="⏹️ Stop & Transcribe",
                format="wav",
                key=f"audio_rec_{q_count}"
            )
            if audio:
                audio_bytes = audio['bytes']
                if st.session_state.get("last_processed_audio_bytes") != audio_bytes:
                    st.session_state.last_processed_audio_bytes = audio_bytes
                    compressed_bytes = compress_wav(audio_bytes)
                    mp3_bytes = wav_to_mp3(compressed_bytes)
                    audio_b64 = base64.b64encode(mp3_bytes).decode('utf-8')
                    st.session_state.current_audio_b64 = audio_b64
                    
                    with st.spinner("Transcribing your voice response..."):
                        transcription = google_speech_to_text(compressed_bytes)
                        if transcription:
                            st.session_state.candidate_answer = transcription
                            st.success(f"📝 Transcribed: {transcription}")
                            st.rerun()

        with col_clear:
            if st.button("🗑️ Clear", use_container_width=True):
                st.session_state.candidate_answer = ""
                st.session_state.current_audio_b64 = None
                if "last_processed_audio_bytes" in st.session_state:
                    del st.session_state["last_processed_audio_bytes"]
                st.rerun()

        user_answer = st.text_area(
            "Your Answer:", 
            value=st.session_state.candidate_answer, 
            height=140, 
            placeholder="Type your response here or record your voice above..."
        )
        
        col_sub, col_skip = st.columns([2, 1])
        
        with col_sub:
            submitted = st.button("Submit Answer ➔", type="primary", use_container_width=True)
            
        with col_skip:
            skipped = st.button("⏩ Skip Question", use_container_width=True)

        # Handle Submission
        if submitted:
            final_answer = user_answer.strip()
            if not final_answer:
                st.warning("Please enter an answer or click 'Skip Question' if you prefer to move on.")
            else:
                st.session_state.interview_qas[-1]["answer"] = final_answer
                db.update_last_qa_answer(st.session_state.candidate_id, final_answer, st.session_state.current_audio_b64)
                
                st.session_state.candidate_answer = ""
                st.session_state.current_audio_b64 = None
                if "last_processed_audio_bytes" in st.session_state:
                    del st.session_state["last_processed_audio_bytes"]
                
                if q_count < 5:
                    with st.spinner("Evaluating response quality and generating next question..."):
                        next_q = interview.generate_next_question(
                            role_name,
                            role_desc,
                            st.session_state.parsed_profile.get("skills", []),
                            st.session_state.parsed_profile.get("projects", []),
                            st.session_state.interview_qas,
                            model_name=st.session_state.selected_model
                        )
                        db.add_interview_qa(st.session_state.candidate_id, next_q)
                        st.session_state.interview_qas.append({"question": next_q, "answer": ""})
                        st.session_state.current_question = next_q
                    st.rerun()
                else:
                    # DIRECT FLOW TO EVALUATION & THANK YOU REPORT
                    with st.spinner("AI evaluating complete interview transcript & generating scores..."):
                        evaluation = interview.evaluate_candidate(
                            st.session_state.parsed_profile.get("name", "Candidate"),
                            st.session_state.selected_role,
                            st.session_state.interview_qas,
                            model_name=st.session_state.selected_model
                        )
                        db.save_evaluation(st.session_state.candidate_id, evaluation)
                    st.session_state.step = "REPORT"
                    st.rerun()

        # Handle Skipping
        if skipped:
            st.session_state.interview_qas[-1]["answer"] = "Skipped"
            db.update_last_qa_answer(st.session_state.candidate_id, "Skipped", None)
            
            st.session_state.candidate_answer = ""
            st.session_state.current_audio_b64 = None
            if "last_processed_audio_bytes" in st.session_state:
                del st.session_state["last_processed_audio_bytes"]
            
            if q_count < 5:
                with st.spinner("Moving to next question..."):
                    next_q = interview.generate_next_question(
                        role_name,
                        role_desc,
                        st.session_state.parsed_profile.get("skills", []),
                        st.session_state.parsed_profile.get("projects", []),
                        st.session_state.interview_qas,
                        model_name=st.session_state.selected_model
                    )
                    db.add_interview_qa(st.session_state.candidate_id, next_q)
                    st.session_state.interview_qas.append({"question": next_q, "answer": ""})
                    st.session_state.current_question = next_q
                st.rerun()
            else:
                # DIRECT FLOW TO EVALUATION & THANK YOU REPORT
                with st.spinner("AI evaluating complete interview transcript & generating scores..."):
                    evaluation = interview.evaluate_candidate(
                        st.session_state.parsed_profile.get("name", "Candidate"),
                        st.session_state.selected_role,
                        st.session_state.interview_qas,
                        model_name=st.session_state.selected_model
                    )
                    db.save_evaluation(st.session_state.candidate_id, evaluation)
                st.session_state.step = "REPORT"
                st.rerun()

# =====================================================
# STEP 4: DIRECT REPORT & THANK YOU PAGE
# =====================================================

elif st.session_state.step == "REPORT":
    st.markdown("""
    <div style="text-align: center; padding: 50px 25px; background: rgba(30, 41, 59, 0.45); backdrop-filter: blur(12px); border-radius: 16px; border: 1px solid rgba(255, 255, 255, 0.08); max-width: 800px; margin: 40px auto;">
        <h1 style="color: #22c55e; font-size: 2.8rem; margin-bottom: 20px; font-weight: 800;">🎉 Application Submitted!</h1>
        <h3 style="color: #cbd5e1; font-weight: 500; margin-bottom: 25px;">Your interview has been completed and graded successfully.</h3>
        <p style="color: #94a3b8; font-size: 1.05rem; line-height: 1.6; margin-bottom: 35px;">
            Your profile, audio recordings, and graded evaluation scores have been securely stored in MongoDB.
            Our HR recruitment team will review your scorecard shortly and reach out regarding next steps.
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        if st.button("Start New Application", type="primary", use_container_width=True):
            for key in ["step", "candidate_id", "parsed_profile", "recommended_roles", "selected_role", "interview_qas", "current_question", "candidate_answer", "current_audio_b64"]:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()
