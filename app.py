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
            headers = {"User-Agent": "TalentAcquisitionApp/1.0"}
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

/* Custom premium scrollbar */
::-webkit-scrollbar {
    width: 6px;
    height: 6px;
}
::-webkit-scrollbar-track {
    background: rgba(255, 255, 255, 0.02);
}
::-webkit-scrollbar-thumb {
    background: rgba(99, 102, 241, 0.3);
    border-radius: 3px;
}
::-webkit-scrollbar-thumb:hover {
    background: rgba(99, 102, 241, 0.5);
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
    font-size: 2.2rem;
    margin-bottom: 0.5rem;
    text-align: center;
}

.subtitle {
    color: #94a3b8;
    font-size: 0.95rem;
    margin-bottom: 2.5rem;
    text-align: center;
    line-height: 1.5;
}

.score-badge {
    background: linear-gradient(135deg, #3b82f6, #1d4ed8);
    color: white;
    padding: 4px 10px;
    border-radius: 9999px;
    font-size: 0.85rem;
    font-weight: 600;
}

.step-container {
    padding: 12px 18px;
    border-radius: 8px;
    background-color: rgba(255, 255, 255, 0.02);
    margin-bottom: 10px;
    border-left: 4px solid #475569;
    transition: all 0.2s ease;
}

.step-active {
    border-left-color: #6366f1;
    background-color: rgba(99, 102, 241, 0.05);
    box-shadow: 0 4px 12px rgba(99, 102, 241, 0.05);
}

.step-done {
    border-left-color: #22c55e;
    background-color: rgba(34, 197, 94, 0.02);
}

.chat-bubble {
    padding: 14px 18px;
    border-radius: 12px;
    margin-bottom: 12px;
    line-height: 1.6;
    font-size: 0.95rem;
    box-shadow: 0 4px 10px rgba(0, 0, 0, 0.15);
}

.chat-interviewer {
    background-color: rgba(99, 102, 241, 0.1);
    border: 1px solid rgba(99, 102, 241, 0.25);
    border-top-left-radius: 2px;
}

.chat-candidate {
    background-color: rgba(255, 255, 255, 0.04);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-top-right-radius: 2px;
}

/* Custom premium button styles */
.stButton > button {
    background: linear-gradient(135deg, #6366f1, #a855f7) !important;
    color: white !important;
    font-weight: 600 !important;
    border: none !important;
    border-radius: 8px !important;
    padding: 8px 24px !important;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
    box-shadow: 0 4px 12px rgba(99, 102, 241, 0.15) !important;
}

.stButton > button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 6px 20px rgba(99, 102, 241, 0.35) !important;
    border-color: transparent !important;
}

/* Custom input textarea focus state */
textarea {
    background-color: rgba(255, 255, 255, 0.02) !important;
    border: 1px solid rgba(255, 255, 255, 0.1) !important;
    border-radius: 8px !important;
    color: white !important;
    transition: all 0.3s ease !important;
}

textarea:focus {
    border-color: #6366f1 !important;
    box-shadow: 0 0 0 2px rgba(99, 102, 241, 0.2) !important;
}
</style>
""", unsafe_allow_html=True)


def google_speech_to_text(audio_bytes: bytes) -> str:
    """
    Fallback: Google Speech Recognition
    """
    try:
        import speech_recognition as sr
        
        recognizer = sr.Recognizer()
        with sr.AudioFile(io.BytesIO(audio_bytes)) as source:
            audio_data = recognizer.record(source)
            text = recognizer.recognize_google(audio_data)
            return text
    except sr.UnknownValueError:
        st.error("Could not understand audio. Please try again.")
        return ""
    except sr.RequestError as e:
        st.error(f"Speech recognition service error: {e}")
        return ""
    except Exception as e:
        st.error(f"Error transcribing audio: {e}")
        return ""

# =====================================================
# COMPRESS WAV AUDIO (Reduces payload size)
# =====================================================

def compress_wav(wav_bytes):
    try:
        import wave
        import audioop
        
        in_io = io.BytesIO(wav_bytes)
        with wave.open(in_io, 'rb') as wav_in:
            params = wav_in.getparams()
            nchannels, sampwidth, framerate, nframes = params[:4]
            raw_frames = wav_in.readframes(nframes)
            
        # Convert to mono if stereo
        if nchannels > 1:
            raw_frames = audioop.tomono(raw_frames, sampwidth, 1, 1)
            nchannels = 1
            
        # Downsample to 16000 Hz
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

# =====================================================
# CONVERT WAV TO MP3
# =====================================================

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
# TEXT-TO-SPEECH (Voice Reader)
# =====================================================

def trigger_tts(text):
    if text:
        try:
            from gtts import gTTS
            import io
            tts = gTTS(text=text, lang='en', tld='com', slow=False)
            fp = io.BytesIO()
            tts.write_to_fp(fp)
            fp.seek(0)
            audio_bytes = fp.read()
            st.audio(audio_bytes, format="audio/mp3", autoplay=True)
        except Exception as e:
            # Fallback to browser SpeechSynthesis if gtts fails
            print(f"Error in gTTS: {e}")
            clean_text = text.replace('"', '\\"').replace("'", "\\'").replace('\n', ' ')
            js_code = f"""
            <script>
                if ('speechSynthesis' in window) {{
                    window.speechSynthesis.cancel();
                    var utterance = new SpeechSynthesisUtterance("{clean_text}");
                    utterance.rate = 1.0;
                    utterance.pitch = 1.0;
                    window.speechSynthesis.speak(utterance);
                }}
            </script>
            """
            components.html(js_code, height=0)

# =====================================================
# INITIALIZE SESSION STATE
# =====================================================

if "step" not in st.session_state:
    st.session_state.step = "LOGIN"
if "candidate_id" not in st.session_state:
    st.session_state.candidate_id = None
if "candidate_email" not in st.session_state:
    st.session_state.candidate_email = ""
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
    st.session_state.selected_model = "gemma4:e2b"
if "candidate_answer" not in st.session_state:
    st.session_state.candidate_answer = ""
if "last_spoken_question" not in st.session_state:
    st.session_state.last_spoken_question = ""
if "voice_enabled" not in st.session_state:
    st.session_state.voice_enabled = True
if "current_audio_b64" not in st.session_state:
    st.session_state.current_audio_b64 = None
if "feedback_submitted" not in st.session_state:
    st.session_state.feedback_submitted = False

# =====================================================
# INITIALIZE DATABASE
# =====================================================

# Initialize database
@st.cache_resource(show_spinner=False)
def get_db():
    from database import TalentDB
    db = TalentDB()
    db.seed_roles()
    return db

db = get_db()

# =====================================================
# PREMIUM LOGO HEADER
# =====================================================

st.markdown("<div style='text-align: center; margin-top: 10px; margin-bottom: 20px;'><h1 style='font-weight: 800; font-size: 2.4rem; background: linear-gradient(135deg, #6366f1, #a855f7); -webkit-background-clip: text; -webkit-text-fill-color: transparent;'>TALENT AI</h1></div>", unsafe_allow_html=True)


def google_speech_to_text(audio_bytes: bytes) -> str:
    """
    Fallback: Google Speech Recognition
    """
    try:
        import speech_recognition as sr
        
        recognizer = sr.Recognizer()
        with sr.AudioFile(io.BytesIO(audio_bytes)) as source:
            audio_data = recognizer.record(source)
            text = recognizer.recognize_google(audio_data)
            return text
    except sr.UnknownValueError:
        st.error("Could not understand audio. Please try again.")
        return ""
    except sr.RequestError as e:
        st.error(f"Speech recognition service error: {e}")
        return ""
    except Exception as e:
        st.error(f"Error transcribing audio: {e}")
        return ""

# =====================================================
# COMPRESS WAV AUDIO (Reduces payload size)
# =====================================================

def compress_wav(wav_bytes):
    try:
        import wave
        import audioop
        
        in_io = io.BytesIO(wav_bytes)
        with wave.open(in_io, 'rb') as wav_in:
            params = wav_in.getparams()
            nchannels, sampwidth, framerate, nframes = params[:4]
            raw_frames = wav_in.readframes(nframes)
            
        # Convert to mono if stereo
        if nchannels > 1:
            raw_frames = audioop.tomono(raw_frames, sampwidth, 1, 1)
            nchannels = 1
            
        # Downsample to 16000 Hz
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

# =====================================================
# CONVERT WAV TO MP3
# =====================================================

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
# TEXT-TO-SPEECH (Voice Reader)
# =====================================================

def trigger_tts(text):
    if text:
        try:
            from gtts import gTTS
            import io
            tts = gTTS(text=text, lang='en', tld='com', slow=False)
            fp = io.BytesIO()
            tts.write_to_fp(fp)
            fp.seek(0)
            audio_bytes = fp.read()
            st.audio(audio_bytes, format="audio/mp3", autoplay=True)
        except Exception as e:
            # Fallback to browser SpeechSynthesis if gtts fails
            print(f"Error in gTTS: {e}")
            clean_text = text.replace('"', '\\"').replace("'", "\\'").replace('\n', ' ')
            js_code = f"""
            <script>
                if ('speechSynthesis' in window) {{
                    window.speechSynthesis.cancel();
                    var utterance = new SpeechSynthesisUtterance("{clean_text}");
                    utterance.rate = 1.0;
                    utterance.pitch = 1.0;
                    window.speechSynthesis.speak(utterance);
                }}
            </script>
            """
            components.html(js_code, height=0)

# =====================================================
# INITIALIZE SESSION STATE
# =====================================================

if "step" not in st.session_state:
    st.session_state.step = "LOGIN"
if "candidate_id" not in st.session_state:
    st.session_state.candidate_id = None
if "candidate_email" not in st.session_state:
    st.session_state.candidate_email = ""
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
    st.session_state.selected_model = "gemma4:e2b"
if "candidate_answer" not in st.session_state:
    st.session_state.candidate_answer = ""
if "last_spoken_question" not in st.session_state:
    st.session_state.last_spoken_question = ""
if "voice_enabled" not in st.session_state:
    st.session_state.voice_enabled = True
if "current_audio_b64" not in st.session_state:
    st.session_state.current_audio_b64 = None

# =====================================================
# INITIALIZE DATABASE
# =====================================================

# Initialize database
@st.cache_resource(show_spinner=False)
def get_db():
    from database import TalentDB
    db = TalentDB()
    db.seed_roles()
    return db

db = get_db()



# =====================================================
# NAVIGATION CONTROLS
# =====================================================

def show_navigation_bar(back_step=None, next_step=None):
    if st.session_state.step in ["UPLOAD", "PARSING", "SELECT_ROLE"]:
        c1, c2, c3 = st.columns([1, 1, 1])
        with c1:
            if back_step:
                if st.button("⬅️ Go Back", use_container_width=True):
                    st.session_state.step = back_step
                    st.rerun()
        with c2:
            if next_step:
                is_disabled = False
                if st.session_state.step == "UPLOAD" and not st.session_state.parsed_profile:
                    is_disabled = True
                if st.button("➡️ Next Page", use_container_width=True, disabled=is_disabled):
                    st.session_state.step = next_step
                    st.rerun()
        with c3:
            if st.button("🚪 Logout", use_container_width=True):
                # Reset session state
                for k in list(st.session_state.keys()):
                    del st.session_state[k]
                st.session_state.step = "LOGIN"
                st.rerun()

# =====================================================
# STEP 0: LOGIN & STATE RECOVERY
# =====================================================

if st.session_state.step == "LOGIN":
    st.markdown('<div class="main-title">Candidate Authentication</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">Enter your email to log in or register. If your interview was disconnected, logging in will resume exactly where you left off.</div>', unsafe_allow_html=True)
    
    email_input = st.text_input("Enter Email Address", placeholder="e.g. candidate@example.com").strip()
    
    c_login, c_new = st.columns(2)
    with c_login:
        if st.button("🔑 Login / Resume Interview", type="primary", use_container_width=True):
            if not email_input:
                st.warning("Please enter your email address to log in.")
            else:
                with st.spinner("Checking your application status..."):
                    existing_cand = db.get_candidate_by_email(email_input)
                    if existing_cand:
                        # Restore state
                        st.session_state.candidate_id = str(existing_cand["_id"])
                        st.session_state.candidate_email = email_input
                        p_info = existing_cand.get("personal_info", {})
                        st.session_state.parsed_profile = {
                            "name": p_info.get("name", "Unknown"),
                            "email": p_info.get("email", ""),
                            "phone": p_info.get("phone", ""),
                            "current_location": p_info.get("current_location", ""),
                            "education": existing_cand.get("education", []),
                            "projects": existing_cand.get("projects", []),
                            "skills": existing_cand.get("extracted_skills", []),
                            "years_of_experience": existing_cand.get("years_of_experience", 0.0)
                        }
                        st.session_state.selected_role = existing_cand.get("selected_role")
                        st.session_state.interview_qas = existing_cand.get("qas", [])
                        
                        status = existing_cand.get("interview_status", "PENDING")
                        
                        if status == "COMPLETED":
                            st.session_state.step = "REPORT"
                            st.success("Welcome back! Your interview is already completed. Accessing your final completion report.")
                            st.rerun()
                        elif status == "IN_PROGRESS" or (status == "PENDING" and existing_cand.get("selected_role")):
                            st.session_state.step = "INTERVIEW"
                            # Restore current question
                            qas = existing_cand.get("qas", [])
                            if qas:
                                last_qa = qas[-1]
                                if not last_qa.get("answer"):
                                    st.session_state.current_question = last_qa["question"]
                                else:
                                    # Generate next question
                                    with st.spinner("Formulating next question..."):
                                        role_data = db.get_role_by_name(st.session_state.selected_role)
                                        role_desc = role_data.get("job_description", "") if role_data else ""
                                        next_q = interview.generate_next_question(
                                            st.session_state.selected_role,
                                            role_desc,
                                            st.session_state.parsed_profile.get("skills", []),
                                            st.session_state.parsed_profile.get("projects", []),
                                            st.session_state.interview_qas,
                                            model_name=st.session_state.selected_model
                                        )
                                        db.add_interview_qa(st.session_state.candidate_id, next_q)
                                        st.session_state.interview_qas.append({"question": next_q, "answer": ""})
                                        st.session_state.current_question = next_q
                            else:
                                # No questions generated yet
                                with st.spinner("Preparing your interview..."):
                                    role_data = db.get_role_by_name(st.session_state.selected_role)
                                    role_desc = role_data.get("job_description", "") if role_data else ""
                                    first_q = interview.generate_next_question(
                                        st.session_state.selected_role,
                                        role_desc,
                                        st.session_state.parsed_profile.get("skills", []),
                                        st.session_state.parsed_profile.get("projects", []),
                                        [],
                                        model_name=st.session_state.selected_model
                                    )
                                    st.session_state.current_question = first_q
                                    db.add_interview_qa(st.session_state.candidate_id, first_q)
                                    st.session_state.interview_qas.append({"question": first_q, "answer": ""})
                            
                            st.success("Welcome back! Resuming your interview exactly where you left off.")
                            st.rerun()
                        else:
                            # Status PENDING but no role selected
                            st.session_state.step = "SELECT_ROLE"
                            # Compute recommendations
                            all_roles = db.get_all_roles()
                            if all_roles:
                                import matcher
                                model = matcher.load_bert_model()
                                if model is not None:
                                    cand_skills_str = ", ".join(st.session_state.parsed_profile.get("skills", []))
                                    cand_projs_str = ", ".join([p.get("project_name", "") for p in st.session_state.parsed_profile.get("projects", [])])
                                    cand_text = f"Skills: {cand_skills_str}\nProjects: {cand_projs_str}\nExperience: {st.session_state.parsed_profile.get('years_of_experience', 0.0)} years"
                                    c_emb = model.encode(cand_text).tolist()
                                    ranks = []
                                    for idx, r in enumerate(all_roles):
                                        import numpy as np
                                        from numpy.linalg import norm
                                        emb_r = r.get("embedding")
                                        if emb_r and c_emb:
                                            score = float(np.dot(emb_r, c_emb)/(norm(emb_r)*norm(c_emb)))
                                            match_pct = round(score * 100.0, 1)
                                        else:
                                            match_pct = 50.0
                                        ranks.append({
                                            "job_role": r.get("job_role"),
                                            "match_score": match_pct,
                                            "job_description": r.get("job_description"),
                                            "skills": r.get("skills")
                                        })
                                    st.session_state.recommended_roles = sorted(ranks, key=lambda x: x["match_score"], reverse=True)[:5]
                            st.success("Welcome back! Redirecting you to role selection.")
                            st.rerun()
                    else:
                        st.info("Email address not found. Click 'Register / New Application' to upload your CV and register.")

    with c_new:
        if st.button("➕ Register / New Application", use_container_width=True):
            if not email_input:
                st.warning("Please enter your email address to register.")
            else:
                st.session_state.candidate_email = email_input
                st.session_state.step = "UPLOAD"
                st.rerun()

# =====================================================
# STEP 1: UPLOAD RESUME
# =====================================================

elif st.session_state.step == "UPLOAD":
    st.markdown('<div class="main-title">Talent Acquisition Platform</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">Upload your resume to begin a dynamic interview.</div>', unsafe_allow_html=True)
    
    st.subheader("Upload Candidate Resume")
    uploaded_file = st.file_uploader(
        "Supported formats: PDF, TXT (Max size 10MB)",
        type=["pdf", "txt"],
        help="Your resume will be processed using secure parsers."
    )
    
    if uploaded_file is not None:
        file_size_mb = len(uploaded_file.getvalue()) / (1024 * 1024)
        if file_size_mb > 10.0:
            st.error("File exceeds the 10MB size limit. Please upload a smaller file.")
        else:
            if st.button("Process & Parse Resume", type="primary", use_container_width=True):
                with st.spinner("Reading resume contents and extracting skills..."):
                    file_ext = uploaded_file.name.split(".")[-1]
                    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file_ext}") as tmp:
                        tmp.write(uploaded_file.getvalue())
                        tmp_path = tmp.name
                        
                    try:
                        all_roles = db.get_all_roles()
                        if not all_roles:
                            st.error("No job roles found in database. Seed job_role.json first.")
                            os.unlink(tmp_path)
                        else:
                            # Extract text, parse details & match jobs via Hybrid Vector Reranking
                            with st.spinner("Extracting candidate profile and calculating job role recommendations..."):
                                geo_address = get_geolocation_location(None)
                                raw_text, resume_embedding, parsed_profile, recommended = parser.process_resume_hybrid_rerank(
                                    tmp_path, 
                                    file_ext, 
                                    all_roles,
                                    model_name=st.session_state.selected_model,
                                    current_location=geo_address
                                )
                              
                            # Clean temp file
                            os.unlink(tmp_path)
                            
                            # Ensure email matches login email if parsed email is empty
                            if not parsed_profile.get("email") and st.session_state.get("candidate_email"):
                                parsed_profile["email"] = st.session_state.candidate_email
                            
                            st.session_state.parsed_profile = parsed_profile
                            st.session_state.recommended_roles = recommended
                            st.session_state.raw_resume_text = raw_text
                            st.session_state.resume_embedding = resume_embedding
                            
                            # Create candidate entry in MongoDB
                            cand_id = db.create_candidate(parsed_profile, raw_text, resume_embedding=resume_embedding)
                            st.session_state.candidate_id = cand_id
                            
                            # Transition to resume parsing (editable) page
                            st.session_state.step = "PARSING"
                            st.success("Resume processed successfully! Check your parsed details below.")
                            st.rerun()
                    except Exception as e:
                        st.error(f"Error processing resume: {str(e)}")
                        if os.path.exists(tmp_path):
                            os.unlink(tmp_path)
    
    show_navigation_bar(back_step="LOGIN", next_step="PARSING")

# =====================================================
# STEP 2: EDITABLE PARSING EDITOR
# =====================================================

elif st.session_state.step == "PARSING":
    st.markdown('<div class="main-title">Resume Parsing Details</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">Review and edit your profile details extracted by the AI below. Make sure they are accurate before proceeding.</div>', unsafe_allow_html=True)
    
    profile = st.session_state.parsed_profile
    if not profile:
        st.warning("No parsed profile found. Please upload a resume first.")
    else:
        with st.form("edit_profile_form"):
            st.subheader("Edit Parsed Information")
            
            # Basic fields
            col_n, col_e = st.columns(2)
            with col_n:
                name_val = st.text_input("Full Name", value=profile.get("name", ""))
            with col_e:
                email_val = st.text_input("Email Address", value=profile.get("email", ""))
                
            col_p, col_l = st.columns(2)
            with col_p:
                phone_val = st.text_input("Phone Number", value=profile.get("phone", ""))
            with col_l:
                loc_val = st.text_input("Location (City, Country)", value=profile.get("current_location", ""))
                
            exp_val = st.number_input("Years of Experience", min_value=0.0, max_value=50.0, value=float(profile.get("years_of_experience") or 0.0), step=0.5)
            
            # Lists as serialized strings
            edu_items = profile.get("education", [])
            if isinstance(edu_items, list):
                edu_str = "\n".join([f"{e.get('degree', '')} at {e.get('institution', '')} ({e.get('year', '')})" if isinstance(e, dict) else str(e) for e in edu_items])
            else:
                edu_str = str(edu_items)
            edu_val = st.text_area("Educational Background (one entry per line)", value=edu_str, placeholder="e.g. B.S. Computer Science at NYU (2020)")
            
            proj_items = profile.get("projects", [])
            if isinstance(proj_items, list):
                proj_str = "\n".join([f"{p.get('project_name', '')}: {p.get('description', '')}" if isinstance(p, dict) else str(p) for p in proj_items])
            else:
                proj_str = str(proj_items)
            proj_val = st.text_area("Work Experience / Projects (one project per line in format 'Project Name: Description')", value=proj_str, placeholder="e.g. E-Commerce App: Built scalable web store using React")
            
            skills_items = profile.get("skills", [])
            if isinstance(skills_items, list):
                skills_str = ", ".join(skills_items)
            else:
                skills_str = str(skills_items)
            skills_val = st.text_area("Skillset (comma-separated)", value=skills_str, placeholder="e.g. Python, SQL, Project Management")
            
            save_btn = st.form_submit_button("💾 Save Profile & Proceed to Job Matches", use_container_width=True)
            if save_btn:
                # Parse edited strings back to structures
                parsed_edu = []
                for line in edu_val.split("\n"):
                    line = line.strip()
                    if not line:
                        continue
                    if " at " in line:
                        parts = line.split(" at ")
                        degree = parts[0].strip()
                        institution_year = parts[1].strip()
                        if " (" in institution_year:
                            y_parts = institution_year.split(" (")
                            institution = y_parts[0].strip()
                            year = y_parts[1].replace(")", "").strip()
                        else:
                            institution = institution_year
                            year = ""
                        parsed_edu.append({"degree": degree, "institution": institution, "year": year})
                    else:
                        parsed_edu.append({"degree": line, "institution": "", "year": ""})
                        
                parsed_proj = []
                for line in proj_val.split("\n"):
                    line = line.strip()
                    if not line:
                        continue
                    if ":" in line:
                        parts = line.split(":", 1)
                        parsed_proj.append({"project_name": parts[0].strip(), "description": parts[1].strip()})
                    else:
                        parsed_proj.append({"project_name": line, "description": ""})
                        
                parsed_skills = [s.strip() for s in skills_val.split(",") if s.strip()]
                
                # Update MongoDB
                p_info = {
                    "name": name_val,
                    "email": email_val,
                    "phone": phone_val,
                    "current_location": loc_val
                }
                db.update_candidate_parsed_profile(
                    st.session_state.candidate_id,
                    p_info,
                    parsed_edu,
                    parsed_skills,
                    parsed_proj,
                    exp_val
                )
                
                # Update session state
                st.session_state.parsed_profile["name"] = name_val
                st.session_state.parsed_profile["email"] = email_val
                st.session_state.parsed_profile["phone"] = phone_val
                st.session_state.parsed_profile["current_location"] = loc_val
                st.session_state.parsed_profile["education"] = parsed_edu
                st.session_state.parsed_profile["projects"] = parsed_proj
                st.session_state.parsed_profile["skills"] = parsed_skills
                st.session_state.parsed_profile["years_of_experience"] = exp_val
                
                # Re-generate recommendations using updated skills
                all_roles = db.get_all_roles()
                if all_roles:
                    import matcher
                    model = matcher.load_bert_model()
                    if model is not None:
                        # candidate embedding based on edited text
                        cand_skills_str = ", ".join(parsed_skills)
                        cand_projs_str = ", ".join([p.get("project_name", "") for p in parsed_proj])
                        cand_text = f"Skills: {cand_skills_str}\nProjects: {cand_projs_str}\nExperience: {exp_val} years"
                        c_emb = model.encode(cand_text).tolist()
                        
                        ranks = []
                        for idx, r in enumerate(all_roles):
                            import numpy as np
                            from numpy.linalg import norm
                            emb_r = r.get("embedding")
                            if emb_r and c_emb:
                                score = float(np.dot(emb_r, c_emb)/(norm(emb_r)*norm(c_emb)))
                                match_pct = round(score * 100.0, 1)
                            else:
                                match_pct = 50.0
                            
                            ranks.append({
                                "job_role": r.get("job_role"),
                                "match_score": match_pct,
                                "job_description": r.get("job_description"),
                                "skills": r.get("skills")
                            })
                        ranks = sorted(ranks, key=lambda x: x["match_score"], reverse=True)[:5]
                        st.session_state.recommended_roles = ranks
                
                st.session_state.step = "SELECT_ROLE"
                st.success("Profile saved! Redirecting to Job Matches...")
                st.rerun()
    
    show_navigation_bar(back_step="UPLOAD", next_step="SELECT_ROLE")

# =====================================================
# STEP 3: SELECT JOB ROLE
# =====================================================

elif st.session_state.step == "SELECT_ROLE":
    st.markdown('<div class="main-title">Select Job Role</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">Review your parsed profile details and choose which job role to interview for.</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("Parsed Profile Summary")
        profile = st.session_state.parsed_profile
        
        st.text_input("Name", value=profile.get("name", ""), disabled=True)
        st.text_input("Email", value=profile.get("email", ""), disabled=True)
        st.text_input("Phone", value=profile.get("phone", ""), disabled=True)
        st.text_input("Current Location", value=profile.get("current_location", ""), disabled=True)
        st.number_input("Years of Experience", value=float(profile.get("years_of_experience") or 0.0), disabled=True)
        
        st.markdown("**Skills Found:**")
        st.write(", ".join(profile.get("skills", [])) or "None")
        
    with col2:
        st.subheader("Recommended Job Roles (Top 5 Matches)")
        
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
                    <p style="font-size: 0.9rem; margin-top: 10px; color: #cbd5e1;">{desc[:250]}...</p>
                    <div style="font-size: 0.8rem; color: #94a3b8;">
                        <b>Key Skills:</b> {", ".join([s.get("skill_name", "") for s in skills_req])}
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                if st.button(f"Apply & Start Interview - {role_name}", key=f"btn_{idx}", use_container_width=True):
                    db.update_candidate_role(st.session_state.candidate_id, role_name)
                    st.session_state.selected_role = role_name
                    
                    with st.spinner("Generating your first question..."):
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
                        st.session_state.interview_qas.append({"question": first_q, "answer": ""})
                        
                    st.session_state.step = "INTERVIEW"
                    st.rerun()
    
    show_navigation_bar(back_step="PARSING", next_step=None)

# =====================================================
# STEP 4: INTERVIEW (WITH VOICE SUPPORT) - NAVIGATION LOCKED
# =====================================================

elif st.session_state.step == "INTERVIEW":
    role_name = st.session_state.selected_role
    role_data = db.get_role_by_name(role_name)
    role_desc = role_data.get("job_description", "") if role_data else ""
    
    st.markdown(f'<div class="main-title">Interview: {role_name}</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">Answer each question professionally. Navigation is locked during the active interview.</div>', unsafe_allow_html=True)
    
    q_count = len(st.session_state.interview_qas)
    progress_val = q_count / 5.0
    st.progress(progress_val, text=f"Question {q_count} of 5")
    
    # Voice settings control
    voice_enabled = st.checkbox(
        "🔊 Auto-read questions aloud",
        value=st.session_state.voice_enabled,
        help="Automatically read out interview questions."
    )
    st.session_state.voice_enabled = voice_enabled
    
    # Voice info
    st.caption("🎤 Speak in Hindi, Bengali, or English | Click microphone to record")
    
    st.write("### Conversation")
    
    for i, qa in enumerate(st.session_state.interview_qas):
        st.markdown(f"""
        <div class="chat-bubble chat-interviewer">
            <b>Interviewer (AI)</b><br/>{qa['question']}
        </div>
        """, unsafe_allow_html=True)
        
        if qa.get("answer"):
            st.markdown(f"""
            <div class="chat-bubble chat-candidate">
                <b>You</b><br/>{qa['answer']}
            </div>
            """, unsafe_allow_html=True)
    
    # Speak the current question if not already spoken
    if st.session_state.voice_enabled and st.session_state.current_question and st.session_state.current_question != st.session_state.last_spoken_question:
        trigger_tts(st.session_state.current_question)
        st.session_state.last_spoken_question = st.session_state.current_question

    # Define shared QA submission & evaluation handler
    def submit_and_evaluate_answer(final_answer, is_skipped=False):
        st.session_state.interview_qas[-1]["answer"] = final_answer
        db.update_last_qa_answer(st.session_state.candidate_id, final_answer, st.session_state.current_audio_b64)
        
        if is_skipped:
            tech_score = 0.0
            soft_score = 0.0
            feedback = "Question was skipped by candidate."
            extra_eval = {
                "technical_sub_scores": {
                    "accuracy_correctness": 0.0,
                    "completeness_depth": 0.0
                },
                "soft_skills_sub_scores": {
                    "structure_organization": 0.0,
                    "clarity_articulation": 0.0
                }
            }
            # Update local state
            st.session_state.interview_qas[-1]["technical_score"] = tech_score
            st.session_state.interview_qas[-1]["soft_skills_score"] = soft_score
            st.session_state.interview_qas[-1]["feedback"] = feedback
            st.session_state.interview_qas[-1]["extra_eval"] = extra_eval
            # Save to DB
            db.update_last_qa_evaluation(
                st.session_state.candidate_id,
                tech_score,
                soft_score,
                feedback,
                extra_eval
            )
        else:
            # EVALUATE SINGLE QA IMMEDIATELY
            with st.spinner("Evaluating your response..."):
                tech_score, soft_score, feedback, extra_eval = interview.evaluate_single_qa(
                    role_name,
                    st.session_state.current_question,
                    final_answer,
                    model_name=st.session_state.selected_model
                )
                # Update local state
                st.session_state.interview_qas[-1]["technical_score"] = tech_score
                st.session_state.interview_qas[-1]["soft_skills_score"] = soft_score
                st.session_state.interview_qas[-1]["feedback"] = feedback
                st.session_state.interview_qas[-1]["extra_eval"] = extra_eval
                # Save to DB
                db.update_last_qa_evaluation(
                    st.session_state.candidate_id,
                    tech_score,
                    soft_score,
                    feedback,
                    extra_eval
                )
        
        st.session_state.candidate_answer = ""
        st.session_state.current_audio_b64 = None
        if "last_processed_audio_bytes" in st.session_state:
            del st.session_state["last_processed_audio_bytes"]
        
        if q_count < 5:
            with st.spinner("Formulating next question..."):
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
            with st.spinner("AI compiling final scorecard and summary (may take a moment)..."):
                cand = db.get_candidate(st.session_state.candidate_id)
                evaluation = interview.evaluate_candidate(
                    st.session_state.parsed_profile.get("name", "Candidate"),
                    st.session_state.selected_role,
                    cand.get("qas", []),
                    model_name=st.session_state.selected_model
                )
                db.save_evaluation(st.session_state.candidate_id, evaluation)
            st.session_state.step = "REPORT"
            st.rerun()

    # Get current answer
    last_qa = st.session_state.interview_qas[-1]
    
    if not last_qa.get("answer"):
        if "candidate_answer" not in st.session_state:
            st.session_state.candidate_answer = ""
        if "current_audio_b64" not in st.session_state:
            st.session_state.current_audio_b64 = None

        st.write("🎙️ **Voice Input:**")
        col_rec, col_speak, col_clear = st.columns([2, 2, 1])
        
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
                    
                    # Convert WAV to MP3
                    mp3_bytes = wav_to_mp3(compressed_bytes)
                    audio_b64 = base64.b64encode(mp3_bytes).decode('utf-8')
                    st.session_state.current_audio_b64 = audio_b64
                    
                    # Transcribe using Google STT
                    with st.spinner("🔄 Transcribing your voice..."):
                        transcription = google_speech_to_text(compressed_bytes)
                        
                        if transcription:
                            st.session_state.candidate_answer = transcription
                            st.success(f"📝 Transcribed: {transcription}")
                            st.rerun()
                        else:
                            st.warning("Could not transcribe audio. Please type your answer.")
                            
        with col_speak:
            if st.button("🔊 Replay Question", use_container_width=True):
                trigger_tts(st.session_state.current_question)
                
        with col_clear:
            if st.button("🗑️ Clear", use_container_width=True):
                st.session_state.candidate_answer = ""
                st.session_state.current_audio_b64 = None
                if "last_processed_audio_bytes" in st.session_state:
                    del st.session_state["last_processed_audio_bytes"]
                st.rerun()

        # Text input
        user_answer = st.text_area(
            "Your Answer:", 
            value=st.session_state.candidate_answer, 
            height=150, 
            placeholder="Type your response here or click 'Start Recording' above to speak..."
        )
        
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            submitted = st.button("Submit Answer", type="primary", use_container_width=True)
        with col_btn2:
            skipped = st.button("⏭️ Skip Question", use_container_width=True)
            
        if submitted:
            final_answer = user_answer.strip()
            if not final_answer:
                st.warning("Please provide a response before submitting.")
            else:
                submit_and_evaluate_answer(final_answer, is_skipped=False)
                
        if skipped:
            submit_and_evaluate_answer("Candidate skipped this question.", is_skipped=True)
    else:
        st.info("Interview conversation completed. Generating final scorecard...")

# =====================================================
# STEP 5: THANK YOU PAGE (REPORT)
# =====================================================

elif st.session_state.step == "REPORT":
    st.markdown("""
    <div style="text-align: center; padding: 50px 20px; background: rgba(30, 41, 59, 0.45); backdrop-filter: blur(8px); border-radius: 12px; border: 1px solid rgba(255, 255, 255, 0.08); max-width: 800px; margin: 40px auto;">
        <h1 style="color: #22c55e; font-size: 2.8rem; margin-bottom: 20px; font-weight: 800;">&#127881; Thank You!</h1>
        <h3 style="color: #cbd5e1; font-weight: 500; margin-bottom: 25px;">Your interview has been completed and submitted successfully.</h3>
        <p style="color: #94a3b8; font-size: 1.05rem; line-height: 1.6; margin-bottom: 35px;">
            We have safely recorded your profile and interview transcript in our database. 
            Our recruitment team will review your assessment shortly and get in touch with you regarding the next steps in our hiring process.
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    st.write("---")
    st.subheader("💬 Share Your Experience")
    
    if st.session_state.get("feedback_submitted"):
        st.success("🎉 Thank you! Your feedback has been recorded successfully.")
    else:
        with st.form("feedback_form"):
            rating = st.radio(
                "Rate your overall interview experience (1 = Poor, 10 = Excellent):",
                options=list(range(1, 11)),
                index=9, # Default to 10
                horizontal=True
            )
            
            additional_comments = st.text_area(
                "Additional Feedback / Suggestions (Optional):",
                placeholder="Share your thoughts on the AI interviewer, audio quality, voice recording, etc..."
            )
            
            submit_feedback = st.form_submit_button("Submit Feedback", use_container_width=True)
            
            if submit_feedback:
                db.save_candidate_feedback(
                    candidate_id=st.session_state.candidate_id,
                    email=st.session_state.candidate_email,
                    role=st.session_state.selected_role,
                    rating=rating,
                    comments=additional_comments
                )
                st.session_state.feedback_submitted = True
                st.rerun()
                
    st.write("")
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        if st.button("Logout / Exit Application", type="primary", use_container_width=True):
            # Reset session states
            for k in list(st.session_state.keys()):
                del st.session_state[k]
            st.session_state.step = "LOGIN"
            st.rerun()
