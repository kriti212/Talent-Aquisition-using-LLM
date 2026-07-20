import streamlit as st
import base64
from database import TalentDB

# =====================================================
# PAGE CONFIGURATION
# =====================================================
st.set_page_config(
    page_title="Talent AI - Interview Transcript",
    page_icon="🎤",
    layout="wide"
)

# Custom Styling
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Plus Jakarta Sans', sans-serif;
    font-size: 14px !important;
}

.main-title {
    background: linear-gradient(135deg, #6366f1, #a855f7);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    font-weight: 800;
    font-size: 2.2rem;
    margin-bottom: 0.5rem;
}

.subtitle {
    color: #94a3b8;
    font-size: 0.95rem;
    margin-bottom: 2rem;
}

.transcript-block {
    background: rgba(30, 41, 59, 0.35);
    border: 1px solid rgba(255, 255, 255, 0.05);
    border-radius: 12px;
    padding: 20px;
    margin-bottom: 15px;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
}

.chat-badge {
    display: inline-block;
    padding: 3px 8px;
    border-radius: 4px;
    font-size: 0.75rem;
    font-weight: 600;
    margin-bottom: 8px;
}

.badge-interviewer {
    background-color: rgba(99, 102, 241, 0.15);
    color: #818cf8;
    border: 1px solid rgba(99, 102, 241, 0.3);
}

.badge-candidate {
    background-color: rgba(255, 255, 255, 0.08);
    color: #cbd5e1;
    border: 1px solid rgba(255, 255, 255, 0.12);
}
</style>
""", unsafe_allow_html=True)

# Database
@st.cache_resource(show_spinner=False)
def get_db():
    return TalentDB()

db = get_db()

# Active Candidate Banner
if st.session_state.get("active_candidate_id"):
    cand = db.get_candidate(st.session_state.active_candidate_id)
    if cand:
        name = cand.get("personal_info", {}).get("name", "Unknown")
        role = cand.get("selected_role", "None")
        st.info(f"👤 **Active Selected Candidate:** {name} | **Applied Role:** {role}")

# Active candidate check
if not st.session_state.get("active_candidate_id"):
    st.warning("⚠️ No active candidate selected. Please go to **Pipeline Overview** page first to select a candidate.")
else:
    cand_id = st.session_state.active_candidate_id
    candidate = db.get_candidate(cand_id)
    
    if not candidate:
        st.error("Candidate record not found in MongoDB.")
    else:
        p_info = candidate.get("personal_info", {})
        name = p_info.get("name", "Unknown")
        role = candidate.get("selected_role") or "None"
        qas = candidate.get("qas", [])
        
        st.markdown(f'<div class="main-title">Interview Transcript & Audio: {name}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="subtitle">Search transcript keywords and review audio voice recordings for candidate <b>{name}</b>.</div>', unsafe_allow_html=True)

        if not qas:
            st.info("No interview conversation records available for this candidate.")
        else:
            # 1. Search Box
            search_word = st.text_input("🔍 Filter Transcript Content", placeholder="Type keywords (e.g. database, project, experience)...")
            
            st.write("### 🎤 Transcript Inspector")
            
            match_count = 0
            for idx, qa in enumerate(qas):
                q_text = qa.get("question", "")
                a_text = qa.get("answer", "")
                
                # Filtering logic
                w = search_word.lower().strip()
                if w and w not in q_text.lower() and w not in a_text.lower():
                    continue
                
                match_count += 1
                
                with st.container():
                    st.markdown(f'<div class="transcript-block">', unsafe_allow_html=True)
                    st.write(f"**Question {idx+1}**")
                    st.markdown('<span class="chat-badge badge-interviewer">AI Interviewer</span>', unsafe_allow_html=True)
                    st.write(q_text)
                    st.markdown("---")
                    st.markdown('<span class="chat-badge badge-candidate">Candidate Response</span>', unsafe_allow_html=True)
                    st.write(f"*\"{a_text or 'No response provided.'}\"*")
                    
                    # 2. Audio Playback if exists
                    audio_b64 = qa.get("audio_b64")
                    if audio_b64:
                        st.write("")
                        try:
                            audio_bytes = base64.b64decode(audio_b64)
                            st.audio(audio_bytes, format="audio/mp3")
                        except Exception as audio_err:
                            st.error(f"Error loading voice playback: {audio_err}")
                            
                    st.markdown('</div>', unsafe_allow_html=True)

            if search_word and match_count == 0:
                st.warning("No conversation exchanges matched your search word.")
