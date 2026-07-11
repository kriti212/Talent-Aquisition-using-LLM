import streamlit as st
from database import TalentDB

# =====================================================
# PAGE CONFIGURATION
# =====================================================
st.set_page_config(
    page_title="Talent AI - Candidates Directory",
    page_icon="👤",
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
</style>
""", unsafe_allow_html=True)

# Database
@st.cache_resource(show_spinner=False)
def get_db():
    return TalentDB()

db = get_db()

# Session state active candidate key init
if "active_candidate_id" not in st.session_state:
    st.session_state.active_candidate_id = None

# Sidebar Database Connection status
with st.sidebar:
    st.markdown("## Navigation Panel")
    st.write("Current Page: Candidates Directory")
    st.markdown("---")
    try:
        db.client.admin.command('ping')
        db_status = "💚 Connected"
    except Exception:
        db_status = "❤️ Disconnected"
    st.metric("MongoDB Status", db_status)

# Fetch candidates
try:
    candidates_list = list(db.candidates_col.find({}))
except Exception as e:
    st.error(f"Error fetching data: {e}")
    candidates_list = []

st.markdown('<div class="main-title">Candidates Directory</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Search, filter, and select a candidate. The details and scorecard are shown on the subsequent pages.</div>', unsafe_allow_html=True)

if not candidates_list:
    st.info("No candidates registered in database yet.")
else:
    # Selected candidate banner
    if st.session_state.active_candidate_id:
        curr_cand = next((c for c in candidates_list if str(c["_id"]) == st.session_state.active_candidate_id), None)
        if curr_cand:
            name = curr_cand.get("personal_info", {}).get("name", "Unknown")
            st.success(f"🎯 **Currently Selected:** **{name}** | You can view this candidate's details in pages **2 Interview Scoring** and **3 Resume Viewer**.")
            
    # Filters
    st.subheader("Filter Applicants")
    col_f1, col_f2, col_f3 = st.columns([2, 1, 1])
    
    with col_f1:
        search_query = st.text_input("🔍 Search by Name or Skill", placeholder="e.g. Rahul, Python, MongoDB...")
    with col_f2:
        roles_list = list(set([c.get("selected_role") for c in candidates_list if c.get("selected_role")]))
        selected_role_filter = st.selectbox("Job Role Filter", ["All Roles"] + roles_list)
    with col_f3:
        status_filter = st.selectbox("Recruiter Review Status", ["All Statuses", "Applied", "Under Review", "Shortlisted", "Rejected"])

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
            query = search_query.lower()
            matches_search = (query in cand_name) or any(query in s for s in cand_skills)
            
        matches_role = True
        if selected_role_filter != "All Roles":
            matches_role = (cand_role == selected_role_filter)
            
        matches_status = True
        if status_filter != "All Statuses":
            matches_status = (cand_rec_status == status_filter)
            
        if matches_search and matches_role and matches_status:
            filtered_candidates.append(cand)

    st.write(f"Showing {len(filtered_candidates)} applicants matching criteria.")
    st.markdown("---")
    
    # Candidate Grid / Table Layout
    if not filtered_candidates:
        st.warning("No candidates found matching the filters.")
    else:
        # Create visual cards
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
            
            # Check highlight if currently selected
            card_border_style = "border-color: #6366f1; background: rgba(99, 102, 241, 0.05);" if st.session_state.active_candidate_id == cand_id_str else ""
            
            with st.container():
                st.markdown(f"""
                <div class="candidate-card" style="{card_border_style}">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                        <h4 style="margin: 0; color: #818cf8;">{name}</h4>
                        <span class="score-badge">Match: {score}%</span>
                    </div>
                    <div style="font-size: 0.9rem; color: #cbd5e1; margin-bottom: 8px;">
                        <b>Role:</b> {role} | <b>Experience:</b> {cand.get("years_of_experience", 0.0)} Years
                    </div>
                    <div style="font-size: 0.8rem; color: #94a3b8; margin-bottom: 8px;">
                        <b>Skills:</b> {', '.join(skills[:8])}{'...' if len(skills) > 8 else ''}
                    </div>
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div>{status_badge}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                if st.button(f"🔍 Select & View Candidate - {name}", key=f"btn_sel_{cand_id_str}", use_container_width=True):
                    st.session_state.active_candidate_id = cand_id_str
                    st.rerun()
