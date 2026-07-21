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

# =====================================================
# PAGE CONFIGURATION
# =====================================================

st.set_page_config(
    page_title="Talent AI - LLM Talent Acquisition",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =====================================================
# CUSTOM CSS
# =====================================================

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Plus Jakarta Sans', sans-serif;
    font-size: 14px !important;
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

.main-title {
    background: linear-gradient(135deg, #6366f1, #a855f7);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    font-weight: 800;
    font-size: 2.0rem;
    margin-bottom: 0.5rem;
}

.subtitle {
    color: #94a3b8;
    font-size: 0.95rem;
    margin-bottom: 2rem;
}

.score-badge {
    background: linear-gradient(135deg, #3b82f6, #1d4ed8);
    color: white;
    padding: 4px 10px;
    border-radius: 9999px;
    font-size: 0.85rem;
    font-weight: 600;
}

.chat-bubble {
    padding: 12px 16px;
    border-radius: 12px;
    margin-bottom: 10px;
    line-height: 1.5;
}

.chat-interviewer {
    background-color: rgba(99, 102, 241, 0.1);
    border: 1px solid rgba(99, 102, 241, 0.2);
    border-top-left-radius: 2px;
}

.chat-candidate {
    background-color: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-top-right-radius: 2px;
}

.sidebar-step {
    padding: 6px 0;
}

.sidebar-step-done {
    color: #22c55e;
}

.sidebar-step-active {
    color: #6366f1;
    font-weight: 700;
}

.sidebar-step-pending {
    color: #64748b;
}
</style>
""", unsafe_allow_html=True)

# =====================================================
# TEXT-TO-SPEECH (Human-like Voice)
# =====================================================

def trigger_tts(text):
    """Read text aloud using Web Speech API with human-like voice"""
    if text:
        clean_text = text.replace('"', '\\"').replace("'", "\\'").replace('\n', ' ')
        js_code = f"""
        <script>
            if ('speechSynthesis' in window) {{
                window.speechSynthesis.cancel();
                var utterance = new SpeechSynthesisUtterance("{clean_text}");
                utterance.rate = 0.9;
                utterance.pitch = 1.0;
                utterance.volume = 1.0;
                // Try to use a female voice if available
                var voices = window.speechSynthesis.getVoices();
                var femaleVoice = voices.find(v => v.name.includes('Google UK') || v.name.includes('Samantha'));
                if (femaleVoice) {{
                    utterance.voice = femaleVoice;
                }}
                window.speechSynthesis.speak(utterance);
            }}
        </script>
        """
        components.html(js_code, height=0)

# =====================================================
# SPEECH-TO-TEXT (Sarvam + Google Fallback)
# =====================================================

def sarvam_speech_to_text(audio_bytes: bytes) -> str:
    """Convert speech to text using Sarvam API (Hindi/Bengali support)"""
    try:
        api_key = st.secrets.get("SARVAM_API_KEY", "")
        if not api_key:
            return google_speech_to_text(audio_bytes)
        
        if len(audio_bytes) < 1000:
            return ""
        
        headers = {"api-subscription-key": api_key}
        files = {"file": ("audio.wav", audio_bytes, "audio/wav")}
        data = {"language_code": "auto", "model": "saarika-v2", "with_diarization": "false"}
        
        response = requests.post(
            "https://api.sarvam.ai/speech-to-text",
            headers=headers, files=files, data=data, timeout=30
        )
        
        if response.status_code == 200:
            transcript = response.json().get("transcript", "")
            return transcript.strip() if transcript else ""
        else:
            return google_speech_to_text(audio_bytes)
            
    except Exception:
        return google_speech_to_text(audio_bytes)

def google_speech_to_text(audio_bytes: bytes) -> str:
    """Fallback: Google Speech Recognition"""
    try:
        import speech_recognition as sr
        recognizer = sr.Recognizer()
        with sr.AudioFile(io.BytesIO(audio_bytes)) as source:
            audio_data = recognizer.record(source)
            return recognizer.recognize_google(audio_data)
    except:
        return ""

def compress_wav(wav_bytes):
    """Compress WAV audio for storage"""
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
    except:
        return wav_bytes

# =====================================================
# INITIALIZE SESSION STATE
# =====================================================

if "step" not in st.session_state:
    st.session_state.step = "UPLOAD"
if "candidate_id" not in st.session_state:
    st.session_state.candidate_id = None
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
    st.session_state.selected_model = None
if "candidate_answer" not in st.session_state:
    st.session_state.candidate_answer = ""
if "last_spoken_question" not in st.session_state:
    st.session_state.last_spoken_question = ""
if "voice_enabled" not in st.session_state:
    st.session_state.voice_enabled = True
if "current_audio_b64" not in st.session_state:
    st.session_state.current_audio_b64 = None
if "skip_count" not in st.session_state:
    st.session_state.skip_count = 0

# =====================================================
# INITIALIZE DATABASE
# =====================================================

@st.cache_resource
def get_db():
    db = TalentDB()
    db.seed_roles()
    return db

db = get_db()

# =====================================================
# SIDEBAR (Redesigned)
# =====================================================

with st.sidebar:
    st.image("https://img.icons8.com/isometric/100/null/artificial-intelligence.png", width=60)
    st.markdown("### 🎯 Talent AI")
    st.markdown("---")
    
    # Model Settings
    st.markdown("#### 🤖 Model")
    available_models = llm_client.get_available_models()
    import config
    default_idx = available_models.index(config.LLM_MODEL) if config.LLM_MODEL in available_models else 0
    selected_model = st.selectbox("LLM Model", options=available_models, index=default_idx)
    st.session_state.selected_model = selected_model
    
    st.markdown("---")
    
    # Voice Settings
    st.markdown("#### 🔊 Voice")
    voice_enabled = st.checkbox(
        "Read Questions Aloud",
        value=st.session_state.voice_enabled
    )
    st.session_state.voice_enabled = voice_enabled
    
    st.markdown("---")
    
    # Progress Steps
    st.markdown("#### 📋 Progress")
    
    steps = [
        ("UPLOAD", "📄 Upload"),
        ("SELECT_ROLE", "🎯 Role"),
        ("INTERVIEW", "💬 Interview"),
        ("REPORT", "📊 Report")
    ]
    
    current_step_idx = next(i for i, (s, _) in enumerate(steps) if s == st.session_state.step)
    
    for i, (s, label) in enumerate(steps):
        if i < current_step_idx:
            st.markdown(f'<div style="color:#22c55e;padding:4px 0;">✅ {label}</div>', unsafe_allow_html=True)
        elif i == current_step_idx:
            st.markdown(f'<div style="color:#6366f1;font-weight:bold;padding:4px 0;">🔵 {label}</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div style="color:#64748b;padding:4px 0;">⚪ {label}</div>', unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Database Status
    try:
        db.client.admin.command('ping')
        st.metric("💾 MongoDB", "✅ Connected")
    except:
        st.metric("💾 MongoDB", "❌ Disconnected")

# =====================================================
# STEP 1: UPLOAD RESUME
# =====================================================

if st.session_state.step == "UPLOAD":
    st.markdown('<div class="main-title">🎯 Talent Acquisition Platform</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">Upload your resume, get role matches, and start your AI interview.</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("📄 Upload Resume")
        uploaded_file = st.file_uploader(
            "PDF or TXT (Max 10MB)",
            type=["pdf", "txt"]
        )
        
        if uploaded_file:
            file_size_mb = len(uploaded_file.getvalue()) / (1024 * 1024)
            if file_size_mb > 10.0:
                st.error("File exceeds 10MB limit.")
            else:
                if st.button("🚀 Process Resume", type="primary"):
                    with st.spinner("Processing resume..."):
                        file_ext = uploaded_file.name.split(".")[-1]
                        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file_ext}") as tmp:
                            tmp.write(uploaded_file.getvalue())
                            tmp_path = tmp.name
                            
                        try:
                            raw_text, parsed_profile = parser.process_resume(
                                tmp_path, file_ext, model_name=st.session_state.selected_model
                            )
                            os.unlink(tmp_path)
                            
                            st.session_state.parsed_profile = parsed_profile
                            
                            all_roles = db.get_all_roles()
                            if not all_roles:
                                st.error("No job roles found in database.")
                            else:
                                with st.spinner("Finding best matches..."):
                                    candidate_skills = parsed_profile.get("skills", [])
                                    recommended = matcher.recommend_roles(candidate_skills, all_roles)
                                    st.session_state.recommended_roles = recommended
                                    
                                    cand_id = db.create_candidate(parsed_profile, raw_text)
                                    st.session_state.candidate_id = cand_id
                                    
                                    st.session_state.step = "SELECT_ROLE"
                                    st.rerun()
                        except Exception as e:
                            st.error(f"Error: {str(e)}")
                            if os.path.exists(tmp_path):
                                os.unlink(tmp_path)
    
    with col2:
        st.markdown("""
        ### 🎯 How it works
        1. **Upload** your resume (PDF/TXT)
        2. **AI extracts** skills & experience
        3. **Top 5 roles** matched
        4. **Voice-enabled** interview
        5. **Instant** evaluation report
        """)

# =====================================================
# STEP 2: SELECT ROLE
# =====================================================

elif st.session_state.step == "SELECT_ROLE":
    st.markdown('<div class="main-title">🎯 Select Job Role</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">Choose the role you want to interview for.</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("📋 Your Profile")
        profile = st.session_state.parsed_profile
        
        st.text_input("Name", value=profile.get("name", ""), disabled=True)
        st.text_input("Email", value=profile.get("email", ""), disabled=True)
        st.text_input("Experience", value=f"{profile.get('years_of_experience', 0)} years", disabled=True)
        
        st.markdown("**Skills:**")
        st.write(", ".join(profile.get("skills", [])[:5]) + ("..." if len(profile.get("skills", [])) > 5 else ""))
        
    with col2:
        st.subheader("🏆 Top 5 Matches")
        
        for idx, rec in enumerate(st.session_state.recommended_roles):
            role_name = rec["job_role"]
            score = rec["match_score"]
            
            with st.container():
                st.markdown(f"""
                <div class="role-card">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <h4 style="margin: 0; color: #818cf8;">{role_name}</h4>
                        <span class="score-badge">{score}% Match</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                if st.button(f"Select {role_name}", key=f"btn_{idx}"):
                    db.update_candidate_role(st.session_state.candidate_id, role_name)
                    st.session_state.selected_role = role_name
                    
                    with st.spinner("Generating first question..."):
                        first_q = interview.generate_next_question(
                            role_name, "", 
                            profile.get("skills", []), 
                            profile.get("projects", []), 
                            [], 
                            model_name=st.session_state.selected_model
                        )
                        st.session_state.current_question = first_q
                        db.add_interview_qa(st.session_state.candidate_id, first_q)
                        st.session_state.interview_qas.append({"question": first_q, "answer": ""})
                        
                    st.session_state.step = "INTERVIEW"
                    st.rerun()

# =====================================================
# STEP 3: INTERVIEW (WITH VOICE + SKIP)
# =====================================================

elif st.session_state.step == "INTERVIEW":
    role_name = st.session_state.selected_role
    role_data = db.get_role_by_name(role_name)
    role_desc = role_data.get("job_description", "") if role_data else ""
    
    st.markdown(f'<div class="main-title">💬 Interview: {role_name}</div>', unsafe_allow_html=True)
    
    q_count = len(st.session_state.interview_qas)
    progress_val = q_count / 5.0
    st.progress(progress_val, text=f"Question {q_count} of 5")
    
    st.markdown("---")
    
    # Show conversation
    for i, qa in enumerate(st.session_state.interview_qas):
        # Question with TTS button
        col_q, col_tts = st.columns([6, 1])
        with col_q:
            st.markdown(f"""
            <div class="chat-bubble chat-interviewer">
                <b>Interviewer</b><br/>{qa['question']}
            </div>
            """, unsafe_allow_html=True)
        with col_tts:
            if st.button("🔊", key=f"tts_{i}"):
                trigger_tts(qa['question'])
        
        # Answer
        if qa.get("answer"):
            if qa.get("answer") == "[SKIPPED]":
                st.markdown(f"""
                <div class="chat-bubble chat-candidate" style="opacity:0.6;">
                    <b>You</b><br/><i>⏭️ Skipped</i>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div class="chat-bubble chat-candidate">
                    <b>You</b><br/>{qa['answer']}
                </div>
                """, unsafe_allow_html=True)
    
    # Auto-speak current question
    if st.session_state.voice_enabled and st.session_state.current_question:
        if st.session_state.current_question != st.session_state.last_spoken_question:
            trigger_tts(st.session_state.current_question)
            st.session_state.last_spoken_question = st.session_state.current_question
    
    # Get current answer
    last_qa = st.session_state.interview_qas[-1]
    
    if not last_qa.get("answer"):
        if "candidate_answer" not in st.session_state:
            st.session_state.candidate_answer = ""
        if "current_audio_b64" not in st.session_state:
            st.session_state.current_audio_b64 = None

        st.markdown("---")
        st.markdown("### 🎤 Your Response")
        st.caption("Speak in Hindi, Bengali, or English. Or type your answer.")
        
        # Voice + Text input
        col_rec, col_skip = st.columns([3, 1])
        
        with col_rec:
            # Voice recording button
            audio = mic_recorder(
                start_prompt="🎙️ Record",
                stop_prompt="⏹️ Stop",
                format="wav",
                key=f"audio_rec_{q_count}"
            )
            
            if audio:
                audio_bytes = audio['bytes']
                compressed_bytes = compress_wav(audio_bytes)
                audio_b64 = base64.b64encode(compressed_bytes).decode('utf-8')
                st.session_state.current_audio_b64 = audio_b64
                
                with st.spinner("Converting speech to text..."):
                    transcription = sarvam_speech_to_text(compressed_bytes)
                    if transcription:
                        st.session_state.candidate_answer = transcription
                        st.success(f"📝 {transcription}")
                        st.rerun()
                    else:
                        st.warning("Could not understand. Please type.")
        
        with col_skip:
            if st.button("⏭️ Skip", use_container_width=True):
                st.session_state.skip_count += 1
                st.session_state.interview_qas[-1]["answer"] = "[SKIPPED]"
                db.update_last_qa_answer(st.session_state.candidate_id, "[SKIPPED]", None)
                
                if q_count < 5:
                    with st.spinner("Next question..."):
                        next_q = interview.generate_next_question(
                            role_name, role_desc,
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
                    st.session_state.step = "REPORT"
                    st.rerun()
        
        # Text input
        user_answer = st.text_area(
            "Your Answer",
            value=st.session_state.candidate_answer,
            height=100,
            placeholder="Type your answer here..."
        )
        
        if st.button("📨 Submit Answer", type="primary"):
            final_answer = user_answer.strip()
            if not final_answer:
                st.warning("Please provide an answer.")
            else:
                st.session_state.interview_qas[-1]["answer"] = final_answer
                db.update_last_qa_answer(st.session_state.candidate_id, final_answer, st.session_state.current_audio_b64)
                
                st.session_state.candidate_answer = ""
                st.session_state.current_audio_b64 = None
                
                if q_count < 5:
                    with st.spinner("Generating next question..."):
                        next_q = interview.generate_next_question(
                            role_name, role_desc,
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
                    st.session_state.step = "REPORT"
                    st.rerun()
    else:
        st.info("Interview completed. Generating report...")

# =====================================================
# STEP 4: REPORT (Short & Crisp)
# =====================================================

elif st.session_state.step == "REPORT":
    st.markdown('<div class="main-title">📊 Interview Report</div>', unsafe_allow_html=True)
    
    # Get evaluation
    with st.spinner("Evaluating your answers..."):
        evaluation = interview.evaluate_candidate(
            st.session_state.parsed_profile.get("name", "Candidate"),
            st.session_state.selected_role,
            st.session_state.interview_qas,
            model_name=st.session_state.selected_model
        )
        db.save_evaluation(st.session_state.candidate_id, evaluation)
    
    # Display results - Short & Crisp
    score = evaluation.get("overall_score", 0)
    rec = evaluation.get("recommendation", "")
    feedback = evaluation.get("feedback", "")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        # Score Circle
        score_color = "🟢" if score >= 70 else "🟡" if score >= 50 else "🔴"
        st.markdown(f"""
        <div style="text-align: center; padding: 20px;">
            <h1 style="font-size: 64px; margin: 0;">{score_color} {score}%</h1>
            <p style="font-size: 18px; color: #94a3b8;">Overall Score</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown(f"### {rec}")
        st.info(feedback)
    
    st.markdown("---")
    
    # Score breakdown (simple)
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**✅ Strengths**")
        for s in evaluation.get("strengths", []):
            st.markdown(f"- {s}")
    with col2:
        st.markdown("**📈 Improvements**")
        for i in evaluation.get("improvements", []):
            st.markdown(f"- {i}")
    
    st.markdown("---")
    
    if st.button("🔄 Start New Assessment", type="primary"):
        for key in ["step", "candidate_id", "parsed_profile", "recommended_roles", 
                    "selected_role", "interview_qas", "current_question", 
                    "candidate_answer", "last_spoken_question", "skip_count"]:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()