import streamlit as st
import pandas as pd
import base64
import io
from bson import ObjectId
from database import TalentDB

# =====================================================
# PAGE CONFIGURATION
# =====================================================

st.set_page_config(
    page_title="Talent AI - Recruiter Portal",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =====================================================
# CUSTOM CSS FOR STUNNING DESIGN
# =====================================================

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

.metric-card {
    background: rgba(30, 41, 59, 0.45);
    backdrop-filter: blur(8px);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 12px;
    padding: 20px;
    margin-bottom: 15px;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
}

.metric-label {
    color: #94a3b8;
    font-size: 0.85rem;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}

.metric-value {
    color: #ffffff;
    font-size: 1.8rem;
    font-weight: 700;
    margin-top: 5px;
}

.candidate-card {
    background: rgba(30, 41, 59, 0.25);
    border: 1px solid rgba(255, 255, 255, 0.05);
    border-radius: 8px;
    padding: 15px;
    margin-bottom: 10px;
    transition: all 0.2s ease-in-out;
}

.candidate-card:hover {
    border-color: rgba(99, 102, 241, 0.4);
    background: rgba(30, 41, 59, 0.4);
}

.score-badge {
    background: linear-gradient(135deg, #6366f1, #a855f7);
    color: white;
    padding: 3px 10px;
    border-radius: 9999px;
    font-size: 0.8rem;
    font-weight: 600;
}

.status-badge-applied {
    background-color: rgba(59, 130, 246, 0.15);
    color: #60a5fa;
    border: 1px solid rgba(59, 130, 246, 0.3);
    padding: 2px 8px;
    border-radius: 9999px;
    font-size: 0.75rem;
    font-weight: 600;
}

.status-badge-shortlisted {
    background-color: rgba(34, 197, 94, 0.15);
    color: #4ade80;
    border: 1px solid rgba(34, 197, 94, 0.3);
    padding: 2px 8px;
    border-radius: 9999px;
    font-size: 0.75rem;
    font-weight: 600;
}

.status-badge-rejected {
    background-color: rgba(239, 68, 68, 0.15);
    color: #f87171;
    border: 1px solid rgba(239, 68, 68, 0.3);
    padding: 2px 8px;
    border-radius: 9999px;
    font-size: 0.75rem;
    font-weight: 600;
}

.status-badge-review {
    background-color: rgba(234, 179, 8, 0.15);
    color: #facc15;
    border: 1px solid rgba(234, 179, 8, 0.3);
    padding: 2px 8px;
    border-radius: 9999px;
    font-size: 0.75rem;
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

# =====================================================
# INITIALIZE DATABASE CONNECTION
# =====================================================

@st.cache_resource(show_spinner=False)
def get_db():
    return TalentDB()

db = get_db()

# =====================================================
# FETCH DATA
# =====================================================

try:
    candidates_list = list(db.candidates_col.find({}))
except Exception as e:
    st.error(f"Error fetching data from database: {e}")
    candidates_list = []

# Initialize session state for selected candidate
if "active_candidate_id" not in st.session_state:
    st.session_state.active_candidate_id = None

# Sidebar branding & DB status
with st.sidebar:
    st.markdown("""
    <div style="text-align: left; margin-bottom: 10px;">
        <svg width="55" height="55" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <defs>
                <linearGradient id="iconGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                    <stop offset="0%" stop-color="#6366f1" />
                    <stop offset="100%" stop-color="#a855f7" />
                </linearGradient>
            </defs>
            <rect width="24" height="24" rx="5" fill="url(#iconGrad)"/>
            <path d="M7 9C7 8.44772 7.44772 8 8 8H16C16.5523 8 17 8.44772 17 9V15C17 15.5523 16.5523 16 16 16H8C7.44772 16 7 15.5523 7 15V9Z" stroke="white" stroke-width="1.5" stroke-linejoin="round"/>
            <path d="M12 8V6" stroke="white" stroke-width="1.5" stroke-linecap="round"/>
            <circle cx="12" cy="5" r="1" fill="white"/>
            <circle cx="10" cy="11" r="1" fill="white"/>
            <circle cx="14" cy="11" r="1" fill="white"/>
            <path d="M10 13.5H14" stroke="white" stroke-width="1" stroke-linecap="round"/>
            <rect x="5.5" y="10.5" width="1.5" height="3" rx="0.5" fill="white"/>
            <rect x="17" y="10.5" width="1.5" height="3" rx="0.5" fill="white"/>
        </svg>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("## AI Talent Acquisition")
    st.caption("Recruiter Admin Space")
    st.markdown("---")
    
    # Back to Candidate App Link
    st.markdown("### ↩️ Navigation")
    st.markdown("[👤 Open Candidate App (Port 8501)](http://localhost:8501)", unsafe_allow_html=True)
    st.markdown("---")
    
    try:
        db.client.admin.command('ping')
        db_status = "💚 Connected"
    except Exception:
        db_status = "❤️ Disconnected"
    st.metric("MongoDB Status", db_status)

# Main Title
st.markdown('<div class="main-title">Recruiter Admin Dashboard</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Review parsed skills, candidate evaluations, expected preferences, and listen to voice transcriptions.</div>', unsafe_allow_html=True)

if not candidates_list:
    st.info("ℹ️ No candidate applications found in the database. Complete an application flow on the candidate app to populate this dashboard.")
else:
    # =====================================================
    # METRICS OVERVIEW CARD ROWS
    # =====================================================
    total_candidates = len(candidates_list)
    completed_interviews = sum(1 for c in candidates_list if c.get("interview_status") == "COMPLETED")
    
    # Calculate average scores
    evaluations = [c.get("evaluation") for c in candidates_list if c.get("evaluation") and c.get("interview_status") == "COMPLETED"]
    
    avg_final = sum(float(e.get("final_score", 0.0)) for e in evaluations) / len(evaluations) if evaluations else 0.0
    avg_tech = sum(float(e.get("technical_score", 0.0)) for e in evaluations) / len(evaluations) if evaluations else 0.0
    avg_soft = sum(float(e.get("soft_skills_score", 0.0)) for e in evaluations) / len(evaluations) if evaluations else 0.0
    
    col_m1, col_m2, col_m3, col_m4 = st.columns(4)
    with col_m1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Total Applicants</div>
            <div class="metric-value">{total_candidates}</div>
        </div>
        """, unsafe_allow_html=True)
    with col_m2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Completed Interviews</div>
            <div class="metric-value">{completed_interviews}</div>
        </div>
        """, unsafe_allow_html=True)
    with col_m3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Avg Match Score</div>
            <div class="metric-value">{avg_final:.1f}%</div>
        </div>
        """, unsafe_allow_html=True)
    with col_m4:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Avg Tech Score</div>
            <div class="metric-value">{avg_tech:.1f}%</div>
        </div>
        """, unsafe_allow_html=True)
        
    st.markdown("---")

    # =====================================================
    # SEARCH & FILTERS
    # =====================================================
    st.subheader("Filter Candidates")
    col_f1, col_f2, col_f3 = st.columns([2, 1, 1])
    
    with col_f1:
        search_query = st.text_input("🔍 Search by Name or Skill", placeholder="e.g. Rahul, Python, MongoDB...")
    with col_f2:
        roles_list = list(set([c.get("selected_role") for c in candidates_list if c.get("selected_role")]))
        selected_role_filter = st.selectbox("Job Role Filter", ["All Roles"] + roles_list)
    with col_f3:
        status_filter = st.selectbox("Recruiter Review Status", ["All Statuses", "Applied", "Under Review", "Shortlisted", "Rejected"])

    # Filter candidate list in memory
    filtered_candidates = []
    for cand in candidates_list:
        p_info = cand.get("personal_info", {})
        cand_name = p_info.get("name", "").lower()
        cand_skills = [s.lower() for s in cand.get("extracted_skills", [])]
        cand_role = cand.get("selected_role", "")
        cand_rec_status = cand.get("recruiter_status", "Applied")
        
        # Search criteria
        matches_search = True
        if search_query:
            query = search_query.lower()
            matches_search = (query in cand_name) or any(query in s for s in cand_skills)
            
        # Role criteria
        matches_role = True
        if selected_role_filter != "All Roles":
            matches_role = (cand_role == selected_role_filter)
            
        # Status criteria
        matches_status = True
        if status_filter != "All Statuses":
            matches_status = (cand_rec_status == status_filter)
            
        if matches_search and matches_role and matches_status:
            filtered_candidates.append(cand)

    # Reranked candidates
    st.write(f"Showing {len(filtered_candidates)} applicants matching criteria.")

    # Two column layout: candidate list table and selected details panel
    col_list, col_details = st.columns([1, 1])

    # =====================================================
    # COLUMN 1: CANDIDATE DIRECTORY LIST
    # =====================================================
    with col_list:
        st.write("### Candidates Directory")
        if not filtered_candidates:
            st.warning("No candidates found matching the filters.")
        else:
            for cand in filtered_candidates:
                cand_id_str = str(cand["_id"])
                p_info = cand.get("personal_info", {})
                name = p_info.get("name", "Unknown")
                role = cand.get("selected_role") or "Not selected"
                skills = cand.get("extracted_skills", [])
                score = cand.get("evaluation", {}).get("final_score", 0.0)
                status = cand.get("recruiter_status", "Applied")
                
                # Badge formatting
                if status == "Shortlisted":
                    status_badge = f'<span class="status-badge-shortlisted">{status}</span>'
                elif status == "Rejected":
                    status_badge = f'<span class="status-badge-rejected">{status}</span>'
                elif status == "Under Review":
                    status_badge = f'<span class="status-badge-review">{status}</span>'
                else:
                    status_badge = f'<span class="status-badge-applied">Applied</span>'
                
                # Card rendering
                with st.container():
                    st.markdown(f"""
                    <div class="candidate-card">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                            <h4 style="margin: 0; color: #818cf8;">{name}</h4>
                            <span class="score-badge">Match: {score}%</span>
                        </div>
                        <div style="font-size: 0.9rem; color: #cbd5e1; margin-bottom: 8px;">
                            <b>Role:</b> {role} | <b>Experience:</b> {cand.get("years_of_experience", 0.0)} Years
                        </div>
                        <div style="font-size: 0.8rem; color: #94a3b8; margin-bottom: 8px;">
                            <b>Skills:</b> {', '.join(skills[:5])}{'...' if len(skills) > 5 else ''}
                        </div>
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <div>{status_badge}</div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    if st.button(f"🔍 View Full Evaluation - {name}", key=f"btn_view_{cand_id_str}", use_container_width=True):
                        st.session_state.active_candidate_id = cand_id_str
                        st.rerun()

    # =====================================================
    # COLUMN 2: APPLICANT DETAILS DRAWER / PANEL
    # =====================================================
    with col_details:
        st.write("### Detailed Evaluation & Actions")
        if not st.session_state.active_candidate_id:
            st.info("💡 Select a candidate on the left to display their technical scorecard, audio recordings, and recruiter assessment tools.")
        else:
            # Find candidate in list
            active_cand = next((c for c in candidates_list if str(c["_id"]) == st.session_state.active_candidate_id), None)
            if not active_cand:
                st.error("Selected candidate not found.")
            else:
                p_info = active_cand.get("personal_info", {})
                name = p_info.get("name", "Unknown")
                email = p_info.get("email", "")
                phone = p_info.get("phone", "")
                loc = p_info.get("current_location", "")
                role = active_cand.get("selected_role") or "Not selected"
                eval_report = active_cand.get("evaluation", {})
                prefs = active_cand.get("preferences", {})
                rec_status = active_cand.get("recruiter_status", "Applied")
                rec_notes = active_cand.get("recruiter_notes", "")
                
                st.markdown(f"## Candidate: {name}")
                st.caption(f"ID: {st.session_state.active_candidate_id}")
                
                # Contact info
                st.write(f"✉️ **Email**: `{email}` | 📞 **Phone**: `{phone}` | 📍 **Location**: `{loc}`")
                st.write(f"💼 **Applied For**: **{role}** | ⏳ **Experience**: {active_cand.get('years_of_experience', 0.0)} Years")
                
                # ---------------------------------------------
                # RECRUITER DECISION & NOTE PAD
                # ---------------------------------------------
                st.markdown("---")
                st.write("📝 **Recruiter Assessment & Action Panel**")
                
                with st.form("recruiter_review_form"):
                    updated_status = st.selectbox(
                        "Change Candidate Status",
                        options=["Applied", "Under Review", "Shortlisted", "Rejected"],
                        index=["Applied", "Under Review", "Shortlisted", "Rejected"].index(rec_status) if rec_status in ["Applied", "Under Review", "Shortlisted", "Rejected"] else 0
                    )
                    
                    updated_notes = st.text_area(
                        "Internal Recruiter Notes / Feedback",
                        value=rec_notes,
                        placeholder="Write interview observations, assessment feedback, or screening details here..."
                    )
                    
                    submitted = st.form_submit_button("Save Recruiter Review", type="primary")
                    if submitted:
                        db.update_recruiter_status(st.session_state.active_candidate_id, updated_status, updated_notes)
                        st.success(f"Review updated successfully for {name}!")
                        st.rerun()

                # ---------------------------------------------
                # EXPANDER: AI SCORE CARD
                # ---------------------------------------------
                with st.expander("🤖 AI Scorecard & Fit Analysis", expanded=True):
                    if not eval_report:
                        st.warning("⚠️ Candidate has not completed the technical interview evaluation yet.")
                    else:
                        st.markdown(f"""
                        <div style="padding: 10px; background-color: rgba(255,255,255,0.03); border-radius: 8px; margin-bottom:15px;">
                            <div style="display:flex; justify-content:space-between; margin-bottom:5px;">
                                <span><b>Overall Match Rating:</b></span>
                                <span class="score-badge">{eval_report.get('final_score', 0.0)}%</span>
                            </div>
                            <div style="display:flex; justify-content:space-between; margin-bottom:5px;">
                                <span>Technical Competency Score:</span>
                                <b>{eval_report.get('technical_score', 0.0)}%</b>
                            </div>
                            <div style="display:flex; justify-content:space-between; margin-bottom:5px;">
                                <span>Communication & Soft Skills Score:</span>
                                <b>{eval_report.get('soft_skills_score', 0.0)}%</b>
                            </div>
                            <div style="display:flex; justify-content:space-between; margin-bottom:5px;">
                                <span>System Recommendation:</span>
                                <b style="color: #4ade80;">{eval_report.get('recommendation', 'N/A')}</b>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        st.markdown("**Technical Skills Evaluation Summary:**")
                        st.write(eval_report.get("technical_summary", "No details provided."))
                        st.markdown("**Communication Summary:**")
                        st.write(eval_report.get("soft_skill_summary", "No details provided."))

                # ---------------------------------------------
                # EXPANDER: DECLARED JOB PREFERENCES
                # ---------------------------------------------
                with st.expander("💸 Declared Job Preferences", expanded=False):
                    if not prefs:
                        st.info("No preferences submitted by the candidate yet.")
                    else:
                        st.write(f"💵 **Expected Compensation**: {prefs.get('salary_expectation', 'N/A')}")
                        st.write(f"🏢 **Workplace Preference**: {prefs.get('wfh_preference', 'N/A')}")
                        st.write(f"🗺️ **Willing to Relocate?**: {prefs.get('relocation_ok', 'N/A')}")
                        st.write(f"📍 **Declared Current Location**: {prefs.get('current_location', 'N/A')}")

                # ---------------------------------------------
                # EXPANDER: INTERVIEW TRANSCRIPT & AUDIO PLAYBACK
                # ---------------------------------------------
                with st.expander("🎤 Technical Interview Q&As & Voice Playback", expanded=True):
                    qas = active_cand.get("qas", [])
                    if not qas:
                        st.info("No Q&A history available for this candidate.")
                    else:
                        for idx, qa in enumerate(qas):
                            st.markdown(f'<div class="transcript-block">', unsafe_allow_html=True)
                            st.write(f"❓ **Question {idx+1}:** {qa.get('question')}")
                            st.write(f"💬 **Candidate Answer:** *\"{qa.get('answer') or 'No answer provided.'}\"*")
                            
                            # RENDER Candidate Audio Player if base64 MP3 exists
                            audio_b64 = qa.get("audio_b64")
                            if audio_b64:
                                try:
                                    audio_bytes = base64.b64decode(audio_b64)
                                    st.audio(audio_bytes, format="audio/mp3")
                                except Exception as audio_err:
                                    st.error(f"Error loading voice playback: {audio_err}")
                            
                            # Question rating details
                            if qa.get("score") is not None:
                                st.markdown(f"📊 **Score:** `{qa.get('score')}%` | 🎯 **AI Feedback:** {qa.get('feedback')}")
                            st.markdown('</div>', unsafe_allow_html=True)

                # ---------------------------------------------
                # EXPANDER: RAW RESUME TEXT
                # ---------------------------------------------
                with st.expander("📄 Raw Resume Parse Text", expanded=False):
                    st.text_area("Parsed Text Content", value=active_cand.get("resume_text", "No text parsed."), height=400, disabled=True)
