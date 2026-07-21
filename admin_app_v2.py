import streamlit as st
import pandas as pd
import base64
import io
from bson import ObjectId
from database import TalentDB

# =====================================================
# PAGE CONFIGURATION & CUSTOM CSS
# =====================================================

st.set_page_config(
    page_title="Talent AI - HR Admin Portal",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap');

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
    margin-bottom: 1.5rem;
}

.metric-card {
    background: rgba(30, 41, 59, 0.45);
    backdrop-filter: blur(8px);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 12px;
    padding: 18px;
    margin-bottom: 15px;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
}

.metric-label {
    color: #94a3b8;
    font-size: 0.8rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}

.metric-value {
    color: #ffffff;
    font-size: 1.7rem;
    font-weight: 800;
    margin-top: 5px;
}

.candidate-card {
    background: rgba(30, 41, 59, 0.25);
    border: 1px solid rgba(255, 255, 255, 0.06);
    border-radius: 10px;
    padding: 15px;
    margin-bottom: 12px;
    transition: all 0.2s ease-in-out;
}

.candidate-card:hover {
    border-color: rgba(99, 102, 241, 0.4);
    background: rgba(30, 41, 59, 0.45);
}

.score-badge {
    background: linear-gradient(135deg, #6366f1, #a855f7);
    color: white;
    padding: 3px 10px;
    border-radius: 9999px;
    font-size: 0.8rem;
    font-weight: 700;
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
    border: 1px solid rgba(255, 255, 255, 0.06);
    border-radius: 8px;
    padding: 12px 15px;
    margin-bottom: 10px;
}
</style>
""", unsafe_allow_html=True)

# =====================================================
# DATABASE CONNECTION
# =====================================================

@st.cache_resource(show_spinner=False)
def get_db():
    return TalentDB()

db = get_db()

try:
    candidates_list = list(db.candidates_col.find({}))
except Exception as e:
    st.error(f"Error fetching candidates from database: {e}")
    candidates_list = []

if "active_candidate_id" not in st.session_state:
    st.session_state.active_candidate_id = None

# =====================================================
# SIDEBAR
# =====================================================

with st.sidebar:
    st.markdown("""
    <div style="text-align: left; margin-bottom: 10px;">
        <svg width="50" height="50" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <defs>
                <linearGradient id="iconGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                    <stop offset="0%" stop-color="#6366f1" />
                    <stop offset="100%" stop-color="#a855f7" />
                </linearGradient>
            </defs>
            <rect width="24" height="24" rx="5" fill="url(#iconGrad)"/>
            <path d="M7 9C7 8.44772 7.44772 8 8 8H16C16.5523 8 17 8.44772 17 9V15C17 15.5523 16.5523 16 16 16H8C7.44772 16 7 15.5523 7 15V9Z" stroke="white" stroke-width="1.5" stroke-linejoin="round"/>
        </svg>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("## Talent AI Admin")
    st.caption("HR & Recruiter Portal v2")
    st.markdown("---")
    st.markdown("[👤 Open Candidate Portal](http://localhost:8501)", unsafe_allow_html=True)
    st.markdown("---")
    
    try:
        db.client.admin.command('ping')
        db_status = "💚 Connected"
    except Exception:
        db_status = "❤️ Disconnected"
    st.metric("MongoDB Status", db_status)

# =====================================================
# MAIN HEADER & TOP METRICS
# =====================================================

st.markdown('<div class="main-title">HR Admin Analytics & Evaluation Portal</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Crisp dashboard view for evaluating candidate technical scorecards, AI feedback, and recruiter decisions.</div>', unsafe_allow_html=True)

if not candidates_list:
    st.info("ℹ️ No candidate applications found in MongoDB. Complete an interview on the candidate app to populate this portal.")
else:
    total_candidates = len(candidates_list)
    completed_interviews = sum(1 for c in candidates_list if c.get("interview_status") == "COMPLETED")
    
    evaluations = [
        c.get("evaluation") for c in candidates_list 
        if c.get("evaluation") and c.get("interview_status") == "COMPLETED"
    ]
    
    avg_final = sum(float(c.get("final_score") or c.get("evaluation", {}).get("final_score", 0.0)) for c in candidates_list if c.get("evaluation")) / len(evaluations) if evaluations else 0.0
    avg_tech = sum(float(c.get("technical_score") or c.get("evaluation", {}).get("technical_score", 0.0)) for c in candidates_list if c.get("evaluation")) / len(evaluations) if evaluations else 0.0
    avg_soft = sum(float(c.get("soft_skills_score") or c.get("evaluation", {}).get("soft_skills_score", 0.0)) for c in candidates_list if c.get("evaluation")) / len(evaluations) if evaluations else 0.0
    
    col_m1, col_m2, col_m3, col_m4, col_m5 = st.columns(5)
    with col_m1:
        st.markdown(f'<div class="metric-card"><div class="metric-label">Total Applicants</div><div class="metric-value">{total_candidates}</div></div>', unsafe_allow_html=True)
    with col_m2:
        st.markdown(f'<div class="metric-card"><div class="metric-label">Completed Interviews</div><div class="metric-value">{completed_interviews}</div></div>', unsafe_allow_html=True)
    with col_m3:
        st.markdown(f'<div class="metric-card"><div class="metric-label">Avg Tech Score</div><div class="metric-value" style="color: #818cf8;">{avg_tech:.1f}%</div></div>', unsafe_allow_html=True)
    with col_m4:
        st.markdown(f'<div class="metric-card"><div class="metric-label">Avg Soft Score</div><div class="metric-value" style="color: #38bdf8;">{avg_soft:.1f}%</div></div>', unsafe_allow_html=True)
    with col_m5:
        st.markdown(f'<div class="metric-card"><div class="metric-label">Avg Final Score</div><div class="metric-value" style="color: #4ade80;">{avg_final:.1f}%</div></div>', unsafe_allow_html=True)
        
    st.markdown("---")

    # =====================================================
    # EXPANDABLE HR ANALYTICS & LEADERBOARD
    # =====================================================
    with st.expander("📊 Recruitment Analytics & Score Leaderboard", expanded=True):
        roles_data = [c.get("selected_role") for c in candidates_list if c.get("selected_role")]
        recs = [c.get("evaluation", {}).get("recommendation", "Pending") for c in candidates_list if c.get("interview_status") == "COMPLETED"]
        
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            st.write("📈 **Applications by Role**")
            if roles_data:
                st.bar_chart(pd.Series(roles_data).value_counts())
            else:
                st.info("No applications yet.")
                
        with col_c2:
            st.write("🎯 **Hiring Recommendation Breakdown**")
            if recs:
                st.bar_chart(pd.Series(recs).value_counts())
            else:
                st.info("No completed evaluations yet.")

        # Candidate Score Leaderboard
        if evaluations:
            st.write("🏆 **Candidate Leaderboard (Saved Scores in MongoDB)**")
            leaderboard_data = []
            for c in candidates_list:
                if c.get("interview_status") == "COMPLETED":
                    p_info = c.get("personal_info", {})
                    eval_data = c.get("evaluation", {})
                    leaderboard_data.append({
                        "Candidate Name": p_info.get("name", "Unknown"),
                        "Job Role": c.get("selected_role", "N/A"),
                        "Final Score (%)": float(c.get("final_score") or eval_data.get("final_score", 0.0)),
                        "Tech Score (%)": float(c.get("technical_score") or eval_data.get("technical_score", 0.0)),
                        "Soft Score (%)": float(c.get("soft_skills_score") or eval_data.get("soft_skills_score", 0.0)),
                        "Recommendation": eval_data.get("recommendation", "N/A"),
                        "Recruiter Status": c.get("recruiter_status", "Applied")
                    })
            if leaderboard_data:
                df_lb = pd.DataFrame(leaderboard_data).sort_values(by="Final Score (%)", ascending=False)
                st.dataframe(df_lb, use_container_width=True)

    # =====================================================
    # SEARCH & FILTERS
    # =====================================================
    st.subheader("Filter & Sort Applicants")
    col_f1, col_f2, col_f3, col_f4 = st.columns([2, 1, 1, 1])
    
    with col_f1:
        search_query = st.text_input("🔍 Search Candidate or Skill", placeholder="e.g. Rahul, Python, Financial...")
    with col_f2:
        roles_list = list(set([c.get("selected_role") for c in candidates_list if c.get("selected_role")]))
        selected_role_filter = st.selectbox("Role Filter", ["All Roles"] + roles_list)
    with col_f3:
        status_filter = st.selectbox("Status Filter", ["All Statuses", "Applied", "Under Review", "Shortlisted", "Rejected"])
    with col_f4:
        sort_order = st.selectbox("Sort By", ["Score (High to Low)", "Experience (High to Low)", "Name (A-Z)"])

    # Filtering logic
    filtered_candidates = []
    for cand in candidates_list:
        p_info = cand.get("personal_info", {})
        cand_name = p_info.get("name", "").lower()
        cand_skills = [s.lower() for s in cand.get("extracted_skills", [])]
        cand_role = cand.get("selected_role", "")
        cand_rec_status = cand.get("recruiter_status", "Applied")
        
        matches_search = True
        if search_query:
            q = search_query.lower()
            matches_search = (q in cand_name) or any(q in s for s in cand_skills)
            
        matches_role = (selected_role_filter == "All Roles") or (cand_role == selected_role_filter)
        matches_status = (status_filter == "All Statuses") or (cand_rec_status == status_filter)
            
        if matches_search and matches_role and matches_status:
            filtered_candidates.append(cand)

    # Sorting
    if sort_order == "Score (High to Low)":
        filtered_candidates.sort(key=lambda x: float(x.get("final_score") or x.get("evaluation", {}).get("final_score", 0.0)), reverse=True)
    elif sort_order == "Experience (High to Low)":
        filtered_candidates.sort(key=lambda x: float(x.get("years_of_experience", 0.0)), reverse=True)
    elif sort_order == "Name (A-Z)":
        filtered_candidates.sort(key=lambda x: x.get("personal_info", {}).get("name", "zzzzz").lower())

    st.write(f"Showing {len(filtered_candidates)} applicants.")

    # Two column layout
    col_list, col_details = st.columns([1, 1])

    # -------------------------------------------------
    # CANDIDATE LIST COLUMN
    # -------------------------------------------------
    with col_list:
        st.write("### Applicants Directory")
        if not filtered_candidates:
            st.warning("No candidate records found matching filters.")
        else:
            for cand in filtered_candidates:
                cand_id_str = str(cand["_id"])
                p_info = cand.get("personal_info", {})
                name = p_info.get("name", "Unknown")
                role = cand.get("selected_role") or "Not selected"
                skills = cand.get("extracted_skills", [])
                score = float(cand.get("final_score") or cand.get("evaluation", {}).get("final_score", 0.0))
                status = cand.get("recruiter_status", "Applied")
                
                if status == "Shortlisted":
                    status_badge = f'<span class="status-badge-shortlisted">{status}</span>'
                elif status == "Rejected":
                    status_badge = f'<span class="status-badge-rejected">{status}</span>'
                elif status == "Under Review":
                    status_badge = f'<span class="status-badge-review">{status}</span>'
                else:
                    status_badge = f'<span class="status-badge-applied">Applied</span>'
                
                st.markdown(f"""
                <div class="candidate-card">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                        <h4 style="margin: 0; color: #818cf8;">{name}</h4>
                        <span class="score-badge">{score:.1f}% Score</span>
                    </div>
                    <div style="font-size: 0.85rem; color: #cbd5e1; margin-bottom: 6px;">
                        <b>Role:</b> {role} | <b>Exp:</b> {cand.get("years_of_experience", 0.0)} Yrs
                    </div>
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div>{status_badge}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                if st.button(f"🔍 View Evaluation Card - {name}", key=f"btn_view_{cand_id_str}", use_container_width=True):
                    st.session_state.active_candidate_id = cand_id_str
                    st.rerun()

    # -------------------------------------------------
    # CANDIDATE EVALUATION DETAILS PANEL
    # -------------------------------------------------
    with col_details:
        st.write("### Detailed Evaluation & Decision Panel")
        if not st.session_state.active_candidate_id:
            st.info("👈 Select an applicant on the left directory to display their technical scorecard and feedback.")
        else:
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
                rec_status = active_cand.get("recruiter_status", "Applied")
                rec_notes = active_cand.get("recruiter_notes", "")
                
                st.markdown(f"## {name}")
                st.caption(f"Email: `{email}` | Phone: `{phone}` | Location: `{loc}`")
                st.write(f"💼 **Role**: **{role}** | ⏳ **Experience**: {active_cand.get('years_of_experience', 0.0)} Years")
                
                # Report export
                report_io = io.StringIO()
                report_io.write(f"=== CANDIDATE AI SCORECARD: {name} ===\n")
                report_io.write(f"Role: {role} | Exp: {active_cand.get('years_of_experience', 0.0)} Yrs\n")
                report_io.write(f"Final Score: {active_cand.get('final_score', 0.0)}%\n")
                report_io.write(f"Recommendation: {eval_report.get('recommendation', 'N/A')}\n\n")
                report_io.write(f"Technical Summary:\n{eval_report.get('technical_summary', 'N/A')}\n\n")
                report_text = report_io.getvalue()
                
                st.download_button(
                    label="📥 Export Candidate Scorecard (TXT)",
                    data=report_text,
                    file_name=f"Scorecard_{name.replace(' ', '_')}.txt",
                    mime="text/plain",
                    use_container_width=True
                )
                
                # Recruiter Decision Form
                st.markdown("---")
                st.write("📝 **Recruiter Decision & Assessment Notes**")
                
                with st.form("recruiter_review_form"):
                    updated_status = st.selectbox(
                        "Update Candidate Status",
                        options=["Applied", "Under Review", "Shortlisted", "Rejected"],
                        index=["Applied", "Under Review", "Shortlisted", "Rejected"].index(rec_status) if rec_status in ["Applied", "Under Review", "Shortlisted", "Rejected"] else 0
                    )
                    
                    updated_notes = st.text_area(
                        "Internal Recruiter Notes",
                        value=rec_notes,
                        placeholder="Add screening notes, interview observations, or next step details..."
                    )
                    
                    if st.form_submit_button("Save Recruiter Decision", type="primary"):
                        db.update_recruiter_status(st.session_state.active_candidate_id, updated_status, updated_notes)
                        st.success(f"Updated status for {name} to {updated_status}!")
                        st.rerun()

                # CRISP SCORECARD CONTAINER
                st.markdown("---")
                st.write("🤖 **AI Technical Scorecard Summary**")
                if not eval_report:
                    st.warning("⚠️ Interview evaluation pending for this applicant.")
                else:
                    st.markdown(f"""
                    <div style="padding: 12px; background-color: rgba(255,255,255,0.03); border-radius: 8px; margin-bottom: 12px;">
                        <div style="display:flex; justify-content:space-between; margin-bottom:5px;">
                            <span>Technical Score:</span>
                            <b style="color: #818cf8;">{eval_report.get('technical_score', 0.0)}%</b>
                        </div>
                        <div style="display:flex; justify-content:space-between; margin-bottom:5px;">
                            <span>Soft Skills Score:</span>
                            <b style="color: #38bdf8;">{eval_report.get('soft_skills_score', 0.0)}%</b>
                        </div>
                        <div style="display:flex; justify-content:space-between; margin-bottom:5px;">
                            <span>Overall Final Score:</span>
                            <b style="color: #4ade80;">{eval_report.get('final_score', 0.0)}%</b>
                        </div>
                        <div style="display:flex; justify-content:space-between;">
                            <span>Recommendation:</span>
                            <b style="color: #facc15;">{eval_report.get('recommendation', 'N/A')}</b>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    st.markdown("**Technical Domain Summary:**")
                    st.write(eval_report.get("technical_summary", "No details available."))
                    st.markdown("**Communication Summary:**")
                    st.write(eval_report.get("soft_skill_summary", "No details available."))

                # CRISP COLLAPSIBLE DETAILED TRANSCRIPT & AI FEEDBACK EXPANDER
                with st.expander("💬 View Detailed Q&A Feedback & Voice Playback", expanded=False):
                    qas = active_cand.get("qas", [])
                    detailed_fb = eval_report.get("detailed_feedback", [])
                    
                    if not qas:
                        st.info("No Q&A transcript recorded.")
                    else:
                        for idx, qa in enumerate(qas):
                            st.markdown(f'<div class="transcript-block">', unsafe_allow_html=True)
                            st.write(f"❓ **Q{idx+1}:** {qa.get('question')}")
                            
                            ans = qa.get('answer') or 'No answer provided.'
                            if ans == "Skipped":
                                st.write("💬 **Answer:** ⏩ *Skipped by Candidate*")
                            else:
                                st.write(f"💬 **Answer:** *\"{ans}\"*")
                            
                            # Audio playback
                            audio_b64 = qa.get("audio_b64")
                            if audio_b64:
                                try:
                                    st.audio(base64.b64decode(audio_b64), format="audio/mp3")
                                except Exception as err:
                                    st.error(f"Error loading voice playback: {err}")
                            
                            # Matching AI detailed feedback item
                            matching_item = next((item for item in detailed_fb if item.get("question_number") == idx + 1), None)
                            if matching_item:
                                st.markdown(f"📊 **Tech Score:** `{matching_item.get('technical_score', 0.0)}%` | **Soft Skills:** `{matching_item.get('soft_skills_score', 0.0)}%`")
                                st.markdown(f"🎯 **AI Feedback:** {matching_item.get('feedback', 'No feedback.')}")
                            st.markdown('</div>', unsafe_allow_html=True)

                # RAW RESUME PARSED TEXT EXPANDER
                with st.expander("📄 Raw Parsed Resume Text", expanded=False):
                    st.text_area("Extracted Resume Content", value=active_cand.get("resume_text", "No text recorded."), height=250, disabled=True)
