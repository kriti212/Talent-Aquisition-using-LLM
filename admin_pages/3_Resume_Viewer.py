import streamlit as st
from database import TalentDB

# =====================================================
# PAGE CONFIGURATION
# =====================================================
st.set_page_config(
    page_title="Talent AI - Resume Details",
    page_icon="📄",
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

.contact-card {
    background: rgba(30, 41, 59, 0.45);
    backdrop-filter: blur(8px);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 12px;
    padding: 24px;
    margin-bottom: 20px;
}

.match-badge-success {
    background-color: rgba(34, 197, 94, 0.15);
    color: #4ade80;
    border: 1px solid rgba(34, 197, 94, 0.3);
    padding: 4px 12px;
    border-radius: 9999px;
    font-weight: 600;
    font-size: 0.85rem;
}

.match-badge-warning {
    background-color: rgba(234, 179, 8, 0.15);
    color: #facc15;
    border: 1px solid rgba(234, 179, 8, 0.3);
    padding: 4px 12px;
    border-radius: 9999px;
    font-weight: 600;
    font-size: 0.85rem;
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
        role_name = candidate.get("selected_role") or "None"
        raw_text = candidate.get("resume_text", "No raw text available.")
        
        st.markdown(f'<div class="main-title">Resume & Profile Details: {name}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="subtitle">AI-extracted resume profile details, location/experience match indicators, and raw resume text.</div>', unsafe_allow_html=True)

        col_l, col_r = st.columns([1, 1])

        # Left Column: Extracted Contact & Profile Card
        with col_l:
            st.write("### 📇 Extracted Profile Overview")
            
            with st.container():
                st.markdown(f"""
                <div class="contact-card">
                    <h4 style="margin-top:0; color:#818cf8;">Personal & Contact Info</h4>
                    <table style="width:100%; border-collapse:collapse; font-size:0.9rem;">
                        <tr><td style="padding:6px 0; color:#94a3b8; width:35%;"><b>Full Name:</b></td><td style="color:white;">{name}</td></tr>
                        <tr><td style="padding:6px 0; color:#94a3b8;"><b>Email Address:</b></td><td style="color:white;">{p_info.get('email', 'N/A')}</td></tr>
                        <tr><td style="padding:6px 0; color:#94a3b8;"><b>Phone Number:</b></td><td style="color:white;">{p_info.get('phone', 'N/A')}</td></tr>
                        <tr><td style="padding:6px 0; color:#94a3b8;"><b>Current Location:</b></td><td style="color:white;">{p_info.get('current_location', 'N/A')}</td></tr>
                        <tr><td style="padding:6px 0; color:#94a3b8;"><b>Total Experience:</b></td><td style="color:white;">{candidate.get('years_of_experience', 0.0)} Years</td></tr>
                    </table>
                </div>
                """, unsafe_allow_html=True)
            
            # Education
            st.write("### 🎓 Extracted Education")
            edu_list = candidate.get("education", [])
            if not edu_list:
                st.write("No education details extracted.")
            else:
                for edu in edu_list:
                    st.write(f"• **{edu.get('degree', 'Degree')}** - {edu.get('institution', 'Institution')} (Grad: {edu.get('year', 'N/A')})")

            # Projects
            st.write("### 💻 Key Projects")
            proj_list = candidate.get("projects", [])
            if not proj_list:
                st.write("No projects extracted.")
            else:
                for proj in proj_list:
                    st.write(f"• **{proj.get('project_name', 'Project')}**: {proj.get('description', '')}")

            # Extracted Skills
            st.write("### ⚙️ Skills List")
            skills = candidate.get("extracted_skills", [])
            if not skills:
                st.write("No skills extracted.")
            else:
                st.write(", ".join(skills))

        # Right Column: Location/Experience Match & Raw Resume Text
        with col_r:
            st.write("### 🎯 Location & Experience Match Badges")
            
            # Calculate Match Badges
            role_data = db.get_role_by_name(role_name)
            
            # 1. Experience Check
            # Default required experience threshold to 2 years if not defined in role
            req_exp = 2.0
            cand_exp = float(candidate.get("years_of_experience") or 0.0)
            if cand_exp >= req_exp:
                exp_badge_html = f'<span class="match-badge-success">✅ Meets Experience Requirement ({cand_exp} / {req_exp} yrs)</span>'
            else:
                exp_badge_html = f'<span class="match-badge-warning">⚠️ Below Preferred Experience ({cand_exp} / {req_exp} yrs)</span>'
                
            # 2. Location Check
            cand_loc = p_info.get("current_location", "").lower().strip()
            # If target role is defined, we can compare. Let's show a success match by default or warning if empty
            if cand_loc:
                loc_badge_html = '<span class="match-badge-success">✅ Location Extracted Successfully</span>'
            else:
                loc_badge_html = '<span class="match-badge-warning">⚠️ Location Missing or Not Found</span>'
                
            st.markdown(f"""
            <div style="padding: 15px; background: rgba(255,255,255,0.02); border-radius: 8px; border: 1px solid rgba(255,255,255,0.05); margin-bottom: 25px;">
                <div style="margin-bottom:12px;">
                    <b>Experience Status:</b> &nbsp; {exp_badge_html}
                </div>
                <div>
                    <b>Location Status:</b> &nbsp; &nbsp; &nbsp; &nbsp; {loc_badge_html}
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            st.write("### 📄 Raw Resume Text")
            st.text_area(
                "Resume content extracted from original document:",
                value=raw_text,
                height=350,
                disabled=True
            )
            
            # Export raw text download button
            st.download_button(
                label="📥 Download Parsed Resume Content (TXT)",
                data=raw_text,
                file_name=f"{name.replace(' ', '_')}_Resume_Content.txt",
                mime="text/plain",
                use_container_width=True
            )
