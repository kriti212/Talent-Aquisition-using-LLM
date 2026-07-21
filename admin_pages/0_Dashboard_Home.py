import streamlit as st
import pandas as pd
from database import TalentDB

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
</style>
""", unsafe_allow_html=True)

# =====================================================
# INITIALIZE DATABASE CONNECTION
# =====================================================
@st.cache_resource(show_spinner=False)
def get_db():
    return TalentDB()

db = get_db()

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
    
    try:
        db.client.admin.command('ping')
        db_status = "💚 Connected"
    except Exception:
        db_status = "❤️ Disconnected"
    st.metric("MongoDB Status", db_status)

# Fetch Data
try:
    candidates_list = list(db.candidates_col.find({}))
except Exception as e:
    st.error(f"Error fetching data from database: {e}")
    candidates_list = []

# Main Title
st.markdown('<div class="main-title">Recruiter Admin Space</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Welcome to the AI Talent Dashboard. Monitor hiring statistics and pipeline distribution. Use the sidebar pages to search candidates and review scores.</div>', unsafe_allow_html=True)

if not candidates_list:
    st.info("ℹ️ No candidate applications found in the database. Complete an application flow on the candidate app to populate this dashboard.")
else:
    # Calculations
    total_candidates = len(candidates_list)
    completed_interviews = sum(1 for c in candidates_list if c.get("interview_status") == "COMPLETED")
    
    evaluations = [c.get("evaluation") for c in candidates_list if c.get("evaluation") and c.get("interview_status") == "COMPLETED"]
    
    avg_final = sum(float(e.get("final_score", 0.0)) for e in evaluations) / len(evaluations) if evaluations else 0.0
    avg_tech = sum(float(e.get("technical_score", 0.0)) for e in evaluations) / len(evaluations) if evaluations else 0.0
    avg_soft = sum(float(e.get("soft_skills_score", 0.0)) for e in evaluations) / len(evaluations) if evaluations else 0.0
    
    # Render Metrics
    col_m1, col_m2, col_m3, col_m4, col_m5 = st.columns(5)
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
            <div class="metric-label">Completed</div>
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
    with col_m5:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Avg Soft Score</div>
            <div class="metric-value">{avg_soft:.1f}%</div>
        </div>
        """, unsafe_allow_html=True)
        
    st.markdown("---")
    
    # Multi-column charts / tables
    col_chart1, col_chart2 = st.columns(2)
    
    with col_chart1:
        st.write("### 💼 Applicants by Target Job Role")
        roles = [c.get("selected_role") for c in candidates_list if c.get("selected_role")]
        if roles:
            df_roles = pd.DataFrame(roles, columns=["Job Role"])
            role_counts = df_roles["Job Role"].value_counts().reset_index()
            role_counts.columns = ["Job Role", "Count"]
            st.dataframe(role_counts, hide_index=True, use_container_width=True)
            # Add simple bar chart
            st.bar_chart(role_counts.set_index("Job Role"), height=200)
        else:
            st.info("No job roles selected yet.")
            
    with col_chart2:
        st.write("### 📌 Applicants by Review Status")
        statuses = [c.get("recruiter_status", "Applied") for c in candidates_list]
        df_status = pd.DataFrame(statuses, columns=["Status"])
        status_counts = df_status["Status"].value_counts().reset_index()
        status_counts.columns = ["Status", "Count"]
        st.dataframe(status_counts, hide_index=True, use_container_width=True)
        # Add simple bar chart
        st.bar_chart(status_counts.set_index("Status"), height=200)

    st.markdown("---")
    st.write("### 🧭 Sidebar Navigation Guide")
    st.markdown("""
    - **Candidate Directory**: Search applicants by name/skills, filter by roles/statuses, and select a candidate for evaluation.
    - **Interview Scoring**: View overall match scorecard, progress bars for sub-metrics (Accuracy, Depth, STAR flow, Clarity), read CoT reasons, listen to audio answers, edit recruiter notes, and download dynamic ReportLab PDF reports.
    - **Resume Details**: Examine structured education, projects, skills, and inspect the raw text extracted from the candidate's uploaded resume.
    """)
