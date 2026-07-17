import streamlit as st
from database import TalentDB

# =====================================================
# PAGE CONFIGURATION
# =====================================================
st.set_page_config(
    page_title="Talent AI - Resume Details",
    page_icon="📄",
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
</style>
""", unsafe_allow_html=True)

# Database
@st.cache_resource(show_spinner=False)
def get_db():
    return TalentDB()

db = get_db()

with st.sidebar:
    st.markdown("## Navigation Panel")
    st.write("Current Page: Resume & Profile")
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
    cand_id = st.session_state.active_candidate_id
    candidate = db.get_candidate(cand_id)
    
    if not candidate:
        st.error("Candidate record not found in MongoDB.")
    else:
        p_info = candidate.get("personal_info", {})
        name = p_info.get("name", "Unknown")
        role = candidate.get("selected_role") or "Not selected"
        prefs = candidate.get("preferences", {})
        
        st.markdown(f'<div class="main-title">Profile: {name}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="subtitle">Detailed parsed skills, education history, projects, preferences, and raw resume text.</div>', unsafe_allow_html=True)
        
        col_left, col_right = st.columns(2)
        
        with col_left:
            st.subheader("Candidate Information")
            st.text_input("Name", value=name, disabled=True)
            st.text_input("Email", value=p_info.get("email", ""), disabled=True)
            st.text_input("Phone", value=p_info.get("phone", ""), disabled=True)
            st.text_input("Location", value=p_info.get("current_location", ""), disabled=True)
            st.number_input("Years of Experience", value=float(candidate.get("years_of_experience") or 0.0), disabled=True)
            
            st.markdown("**Extracted Skills:**")
            skills = candidate.get("extracted_skills", [])
            st.write(", ".join(skills) if skills else "None")
            
            st.markdown("---")
            st.subheader("Job Preferences")
            if not prefs:
                st.info("No preferences submitted by the candidate yet.")
            else:
                st.write(f"💵 **Expected Compensation**: {prefs.get('salary_expectation', 'N/A')}")
                st.write(f"🏢 **Workplace Preference**: {prefs.get('wfh_preference', 'N/A')}")
                st.write(f"🗺️ **Willing to Relocate?**: {prefs.get('relocation_ok', 'N/A')}")
                st.write(f"📍 **Declared Location**: {prefs.get('current_location', 'N/A')}")
                
        with col_right:
            st.subheader("Structured Resume Content")
            
            # Education
            st.markdown("🎓 **Education History:**")
            education = candidate.get("education", [])
            if not education:
                st.write("No education details structured.")
            else:
                for edu in education:
                    st.write(f"- {edu}")
                    
            # Projects
            st.markdown("💻 **Projects:**")
            projects = candidate.get("projects", [])
            if not projects:
                st.write("No projects details structured.")
            else:
                for proj in projects:
                    st.write(f"- {proj}")
                    
            st.markdown("---")
            # Raw Resume Text Expander
            with st.expander("📄 Raw Parsed Resume Text", expanded=False):
                st.text_area("Parsed Text Content", value=candidate.get("resume_text", "No text parsed."), height=400, disabled=True)
