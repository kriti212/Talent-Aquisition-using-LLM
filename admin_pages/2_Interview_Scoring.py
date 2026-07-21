import streamlit as st
import base64
from bson import ObjectId
from database import TalentDB
import generate_pdf

# =====================================================
# PAGE CONFIGURATION
# =====================================================
st.set_page_config(
    page_title="Talent AI - Interview Scoring",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
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

.score-badge {
    background: linear-gradient(135deg, #6366f1, #a855f7);
    color: white;
    padding: 3px 10px;
    border-radius: 9999px;
    font-size: 0.8rem;
    font-weight: 600;
}

.transcript-block {
    background-color: rgba(255, 255, 255, 0.02);
    border: 1px solid rgba(255, 255, 255, 0.05);
    border-radius: 8px;
    padding: 15px;
    margin-bottom: 12px;
}
</style>
""", unsafe_allow_html=True)

# Database
@st.cache_resource(show_spinner=False)
def get_db():
    return TalentDB()

db = get_db()

with st.sidebar:
    st.markdown("## Navigation Panel")
    st.write("Current Page: Interview Scoring")
    st.markdown("---")
    try:
        db.client.admin.command('ping')
        db_status = "💚 Connected"
    except Exception:
        db_status = "❤️ Disconnected"
    st.metric("MongoDB Status", db_status)

# Active candidate check
if not st.session_state.get("active_candidate_id"):
    st.warning("⚠️ No active candidate selected. Please go to **1 Candidate Directory** first to choose a candidate.")
else:
    # Retrieve Candidate
    cand_id = st.session_state.active_candidate_id
    candidate = db.get_candidate(cand_id)
    
    if not candidate:
        st.error("Candidate record not found in MongoDB.")
    else:
        p_info = candidate.get("personal_info", {})
        name = p_info.get("name", "Unknown")
        role = candidate.get("selected_role") or "Not selected"
        eval_report = candidate.get("evaluation", {})
        prefs = candidate.get("preferences", {})
        rec_status = candidate.get("recruiter_status", "Applied")
        rec_notes = candidate.get("recruiter_notes", "")
        
        st.markdown(f'<div class="main-title">Evaluation: {name}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="subtitle">Detailed technical scorecard, sub-metrics, audio playbacks, and PDF report download.</div>', unsafe_allow_html=True)
        
        col_left, col_right = st.columns([1, 1])
        
        # ---------------------------------------------
        # LEFT COLUMN: METRICS & DECISION FORM
        # ---------------------------------------------
        with col_left:
            st.write("### 📊 AI Scorecard Summary")
            if not eval_report:
                st.warning("⚠️ This candidate has not completed the interview evaluation yet.")
            else:
                st.markdown(f"""
                <div style="padding: 15px; background-color: rgba(255,255,255,0.03); border-radius: 8px; margin-bottom:15px; border: 1px solid rgba(255,255,255,0.08);">
                    <div style="display:flex; justify-content:space-between; margin-bottom:8px;">
                        <span><b>Overall Match Rating:</b></span>
                        <span class="score-badge">{eval_report.get('final_score', 0.0)}%</span>
                    </div>
                    <div style="display:flex; justify-content:space-between; margin-bottom:8px;">
                        <span>Technical Competency Score:</span>
                        <b>{eval_report.get('technical_score', 0.0)}%</b>
                    </div>
                    <div style="display:flex; justify-content:space-between; margin-bottom:8px;">
                        <span>Communication & Soft Skills Score:</span>
                        <b>{eval_report.get('soft_skills_score', 0.0)}%</b>
                    </div>
                    <div style="display:flex; justify-content:space-between; margin-bottom:8px;">
                        <span>System Recommendation:</span>
                        <b style="color: #4ade80;">{eval_report.get('recommendation', 'N/A')}</b>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                st.markdown("**Technical Skills Summary:**")
                st.write(eval_report.get("technical_summary", "No details provided."))
                st.markdown("**Communication Summary:**")
                st.write(eval_report.get("soft_skill_summary", "No details provided."))
                st.markdown("---")
            
            # Recruiter form
            st.write("📝 **HR Recruitment Assessment & Status Update**")
            with st.form("recruiter_notes_form"):
                updated_status = st.selectbox(
                    "HR Status Selection",
                    options=["Applied", "Under Review", "Shortlisted", "Rejected"],
                    index=["Applied", "Under Review", "Shortlisted", "Rejected"].index(rec_status) if rec_status in ["Applied", "Under Review", "Shortlisted", "Rejected"] else 0
                )
                updated_notes = st.text_area(
                    "Internal HR Screening Notes",
                    value=rec_notes,
                    placeholder="Write observations about the candidate here..."
                )
                submitted = st.form_submit_button("Save Notes & Status Updates", type="primary")
                if submitted:
                    db.update_recruiter_status(cand_id, updated_status, updated_notes)
                    st.success("Candidate review status and notes saved successfully!")
                    st.rerun()
            
            # PDF download button
            if eval_report:
                st.markdown("### 📄 Export PDF Assessment Report")
                try:
                    # Dynamically generate PDF bytes using ReportLab
                    pdf_bytes = generate_pdf.generate_candidate_pdf(candidate)
                    st.download_button(
                        label="📥 Download Candidate Assessment Report (PDF)",
                        data=pdf_bytes,
                        file_name=f"Candidate_Report_{name.replace(' ', '_')}.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )
                except Exception as pdf_err:
                    st.error(f"Error compiling PDF report: {pdf_err}")

        # ---------------------------------------------
        # RIGHT COLUMN: INTERVIEW TRANSCRIPT & AUDIO
        # ---------------------------------------------
        with col_right:
            st.write("### 🎤 Interview Questions & Audio Responses")
            qas = candidate.get("qas", [])
            
            if not qas:
                st.info("No Q&A history available for this candidate.")
            else:
                for idx, qa in enumerate(qas):
                    st.markdown(f'<div class="transcript-block">', unsafe_allow_html=True)
                    st.write(f"❓ **Question {idx+1}:** {qa.get('question')}")
                    st.write(f"💬 **Candidate Answer:** *\"{qa.get('answer') or 'No answer provided.'}\"*")
                    
                    # Render Audio Player if audio exists
                    audio_b64 = qa.get("audio_b64")
                    if audio_b64:
                        try:
                            audio_bytes = base64.b64decode(audio_b64)
                            st.audio(audio_bytes, format="audio/mp3")
                        except Exception as audio_err:
                            st.error(f"Error loading voice playback: {audio_err}")
                            
                    # Detailed Question scoring
                    tech_score = qa.get("technical_score")
                    soft_score = qa.get("soft_skills_score")
                    feedback_txt = qa.get("feedback")
                    extra_eval = qa.get("extra_eval")
                    
                    if tech_score is not None or soft_score is not None:
                        st.markdown(
                            f"📊 **Technical Score:** `{tech_score or 0.0}%` | "
                            f"💬 **Soft Skills Score:** `{soft_score or 0.0}%`"
                        )
                        
                        if extra_eval and isinstance(extra_eval, dict):
                            st.markdown('<div style="padding: 10px; background-color: rgba(255,255,255,0.02); border-radius: 6px; margin: 10px 0; border: 1px solid rgba(255,255,255,0.05);">', unsafe_allow_html=True)
                            c_tech_col, c_soft_col = st.columns(2)
                            
                            with c_tech_col:
                                st.markdown("⚙️ **Technical Sub-scores**")
                                tech_sub = extra_eval.get("technical_sub_scores") or {}
                                accuracy = tech_sub.get("accuracy_correctness", 0.0)
                                depth = tech_sub.get("completeness_depth", 0.0)
                                
                                st.write(f"Accuracy & Correctness: **{accuracy}%**")
                                st.progress(min(max(accuracy / 100.0, 0.0), 1.0))
                                
                                st.write(f"Completeness & Depth: **{depth}%**")
                                st.progress(min(max(depth / 100.0, 0.0), 1.0))
                                
                                tech_r = extra_eval.get("technical_evaluation_reasoning", "")
                                if tech_r:
                                    st.markdown(f"📝 *CoT Reasoning:* {tech_r}")
                                    
                            with c_soft_col:
                                st.markdown("🗣️ **Soft Skills Sub-scores**")
                                soft_sub = extra_eval.get("soft_skills_sub_scores") or {}
                                structure = soft_sub.get("structure_organization", 0.0)
                                clarity = soft_sub.get("clarity_articulation", 0.0)
                                
                                st.write(f"Structure & Organization: **{structure}%**")
                                st.progress(min(max(structure / 100.0, 0.0), 1.0))
                                
                                st.write(f"Clarity & Articulation: **{clarity}%**")
                                st.progress(min(max(clarity / 100.0, 0.0), 1.0))
                                
                                soft_r = extra_eval.get("soft_skills_evaluation_reasoning", "")
                                if soft_r:
                                    st.markdown(f"📝 *CoT Reasoning:* {soft_r}")
                            st.markdown('</div>', unsafe_allow_html=True)
                            
                        st.markdown(f"🎯 **AI Feedback:** {feedback_txt or 'No feedback provided.'}")
                    st.markdown('</div>', unsafe_allow_html=True)
