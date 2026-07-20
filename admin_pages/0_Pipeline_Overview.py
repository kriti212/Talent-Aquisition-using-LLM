import streamlit as st
import pandas as pd
from database import TalentDB

# =====================================================
# PAGE CONFIGURATION
# =====================================================
st.set_page_config(
    page_title="Talent AI - Pipeline Overview",
    page_icon="📊",
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

.metric-card {
    background: rgba(30, 41, 59, 0.45);
    backdrop-filter: blur(8px);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 12px;
    padding: 20px;
    margin-bottom: 15px;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
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
</style>
""", unsafe_allow_html=True)

# Initialize Database
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

# Title
st.markdown('<div class="main-title">High-Level Pipeline Overview</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Monitor hiring statistics, filter candidate profiles, and select applicants for inspection.</div>', unsafe_allow_html=True)

# Fetch candidates
try:
    candidates = list(db.candidates_col.find({}))
except Exception as e:
    st.error(f"Error connecting to MongoDB: {e}")
    candidates = []

if not candidates:
    st.info("ℹ️ No candidates found in the database. Complete interview assessments to populate stats.")
else:
    # Calculations
    total_candidates = len(candidates)
    completed_interviews = sum(1 for c in candidates if c.get("interview_status") == "COMPLETED")
    
    evaluations = [c.get("evaluation") for c in candidates if c.get("evaluation") and c.get("interview_status") == "COMPLETED"]
    avg_score = sum(float(e.get("final_score", 0.0)) for e in evaluations) / len(evaluations) if evaluations else 0.0
    
    top_performers = sum(1 for e in evaluations if float(e.get("final_score", 0.0)) >= 80.0)
    pending_reviews = sum(1 for c in candidates if c.get("recruiter_status", "Applied") in ["Applied", "Under Review"])

    # 1. Metric Summaries
    col_m1, col_m2, col_m3, col_m4 = st.columns(4)
    with col_m1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Total Interviewed</div>
            <div class="metric-value">{completed_interviews}</div>
        </div>
        """, unsafe_allow_html=True)
    with col_m2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Average Match Score</div>
            <div class="metric-value">{avg_score:.1f}%</div>
        </div>
        """, unsafe_allow_html=True)
    with col_m3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Top Performers (>=80%)</div>
            <div class="metric-value">{top_performers}</div>
        </div>
        """, unsafe_allow_html=True)
    with col_m4:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Pending HR Review</div>
            <div class="metric-value">{pending_reviews}</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # 2. Filter & Search Bar
    st.write("### 🔍 Search & Filtering Controls")
    
    col_f1, col_f2, col_f3, col_f4 = st.columns(4)
    with col_f1:
        search_query = st.text_input("Search Name / Skills", placeholder="e.g. Jane Doe, Python")
    with col_f2:
        role_options = ["All Roles"] + sorted(list(set(c.get("selected_role") for c in candidates if c.get("selected_role"))))
        selected_role = st.selectbox("Filter Target Job Role", options=role_options)
    with col_f3:
        score_threshold = st.slider("Min Overall Match Score", min_value=0.0, max_value=100.0, value=0.0)
    with col_f4:
        status_options = ["All Statuses", "Applied", "Under Review", "Shortlisted", "Rejected"]
        selected_status = st.selectbox("Filter HR Status", options=status_options)

    # Filtering Logic
    filtered_cands = []
    for cand in candidates:
        # Search query matching
        p_info = cand.get("personal_info", {})
        name_val = p_info.get("name", "").lower()
        email_val = p_info.get("email", "").lower()
        skills_val = " ".join(cand.get("extracted_skills", [])).lower()
        
        q = search_query.lower().strip()
        if q and not (q in name_val or q in email_val or q in skills_val):
            continue
            
        # Role matching
        c_role = cand.get("selected_role")
        if selected_role != "All Roles" and c_role != selected_role:
            continue
            
        # Score matching
        eval_data = cand.get("evaluation") or {}
        score = float(eval_data.get("final_score") or 0.0)
        if score < score_threshold:
            continue
            
        # Status matching
        c_status = cand.get("recruiter_status", "Applied")
        if selected_status != "All Statuses" and c_status != selected_status:
            continue
            
        filtered_cands.append(cand)

    # 3. Candidates Directory Listing Table
    st.write(f"### 📋 Candidates Listing ({len(filtered_cands)} matched)")
    if not filtered_cands:
        st.info("No candidates match your search and filter criteria.")
    else:
        table_rows = []
        for c in filtered_cands:
            eval_data = c.get("evaluation") or {}
            table_rows.append({
                "ID": str(c["_id"]),
                "Name": c.get("personal_info", {}).get("name", "Unknown"),
                "Applied Role": c.get("selected_role") or "None",
                "Status": c.get("recruiter_status", "Applied"),
                "Match Score": f"{eval_data.get('final_score', 0.0)}%",
                "Tech Score": f"{eval_data.get('technical_score', 0.0)}%",
                "Soft Score": f"{eval_data.get('soft_skills_score', 0.0)}%",
                "Recommendation": eval_data.get("recommendation", "N/A")
            })
            
        df_display = pd.DataFrame(table_rows)
        st.dataframe(df_display, use_container_width=True, hide_index=True)

        st.markdown("---")
        # Selection area
        st.write("### ⚡ Activate Candidate Screening Context")
        candidate_map = {f"{r['Name']} ({r['Applied Role']})": r["ID"] for r in table_rows}
        selected_cand_label = st.selectbox("Choose Candidate to Inspect Across Pages", options=list(candidate_map.keys()))
        
        if st.button("Set Selected Candidate", type="primary", use_container_width=True):
            cand_id = candidate_map[selected_cand_label]
            st.session_state.active_candidate_id = cand_id
            st.success(f"Successfully activated context for {selected_cand_label}! Use the navigation sidebar to view their scorecard, transcripts, and resume details.")
            st.rerun()
