import streamlit as st
import pandas as pd
from database import TalentDB
import generate_pdf

# =====================================================
# PAGE CONFIGURATION
# =====================================================
st.set_page_config(
    page_title="Talent AI - Shortlisting Panel",
    page_icon="⚡",
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

.action-card {
    background: rgba(30, 41, 59, 0.45);
    backdrop-filter: blur(8px);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 12px;
    padding: 24px;
    margin-bottom: 20px;
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
        rec_status = candidate.get("recruiter_status", "Applied")
        rec_notes = candidate.get("recruiter_notes", "")
        
        st.markdown(f'<div class="main-title">Shortlisting & Actions: {name}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="subtitle">Assign candidate screening statuses, write manual evaluation feedback notes, and export assessment files.</div>', unsafe_allow_html=True)

        col_l, col_r = st.columns([1, 1])

        # Left Column: One-Click Decisions & Recruiter Notes
        with col_l:
            st.write("### ⚡ Screening Decision & Notes")
            
            with st.container():
                st.markdown(f"""
                <div class="action-card">
                    <h4 style="margin-top:0; color:#818cf8;">Recruiter Screening Updates</h4>
                    <p style="font-size:0.9rem; color:#94a3b8; margin-bottom: 20px;">
                        Current Candidate Status: <b style="color:white;">{rec_status}</b>
                    </p>
                </div>
                """, unsafe_allow_html=True)
            
            # One click action buttons
            st.write("#### 🎯 Assign Recruitment Status")
            col_b1, col_b2, col_b3 = st.columns(3)
            with col_b1:
                if st.button("👍 Shortlist for Round 2", use_container_width=True, type="primary"):
                    db.update_recruiter_status(cand_id, "Shortlisted", rec_notes)
                    st.success("Candidate status updated to 'Shortlisted'!")
                    st.rerun()
            with col_b2:
                if st.button("⏸️ Keep on Hold", use_container_width=True):
                    db.update_recruiter_status(cand_id, "Under Review", rec_notes)
                    st.success("Candidate status updated to 'Under Review' (On Hold)!")
                    st.rerun()
            with col_b3:
                if st.button("👎 Reject Applicant", use_container_width=True):
                    db.update_recruiter_status(cand_id, "Rejected", rec_notes)
                    st.success("Candidate status updated to 'Rejected'!")
                    st.rerun()
            
            st.markdown("---")
            
            # Recruiter notes edit form
            st.write("#### 📝 Edit Recruiter Evaluation Notes")
            with st.form("notes_form"):
                new_notes = st.text_area(
                    "Manual screening observations & observations:",
                    value=rec_notes,
                    placeholder="Write detailed screening observations here...",
                    height=200
                )
                if st.form_submit_button("Save Notes Only"):
                    db.update_recruiter_status(cand_id, rec_status, new_notes)
                    st.success("Manual screening notes updated successfully!")
                    st.rerun()

        # Right Column: Export Center
        with col_r:
            st.write("### 📥 Document Export Center")
            
            # PDF download
            st.markdown("#### 📄 Candidate Assessment Report (PDF)")
            st.write("Generate a formatted ReportLab PDF containing contact information, semantic job role recommendations, and full transcript metrics.")
            try:
                pdf_bytes = generate_pdf.generate_candidate_pdf(candidate)
                st.download_button(
                    label="📥 Download Candidate Assessment PDF",
                    data=pdf_bytes,
                    file_name=f"Candidate_Report_{name.replace(' ', '_')}.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
            except Exception as pdf_err:
                st.error(f"Error generating PDF report: {pdf_err}")
                
            st.markdown("---")
            
            # CSV download (Active Candidate)
            st.markdown("#### 📊 Candidate Assessment Data (CSV)")
            st.write("Export a clean spreadsheet of this candidate's metrics, selected role, and HR screening status.")
            
            eval_report = candidate.get("evaluation") or {}
            cand_data = [{
                "Name": name,
                "Email": p_info.get("email", ""),
                "Phone": p_info.get("phone", ""),
                "Selected Role": role_name,
                "Match Score (%)": eval_report.get("final_score", 0.0),
                "Technical Score (%)": eval_report.get("technical_score", 0.0),
                "Soft Skills Score (%)": eval_report.get("soft_skills_score", 0.0),
                "Recommendation": eval_report.get("recommendation", "N/A"),
                "HR Status": rec_status,
                "HR Screening Notes": rec_notes
            }]
            
            df_cand = pd.DataFrame(cand_data)
            csv_bytes = df_cand.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Download Candidate Assessment CSV",
                data=csv_bytes,
                file_name=f"Candidate_Data_{name.replace(' ', '_')}.csv",
                mime="text/csv",
                use_container_width=True
            )
            
            st.markdown("---")
            
            # Bulk export all candidates
            st.markdown("#### 📂 Export All Candidate Records")
            st.write("Download a unified CSV containing screening data for all applicant profiles currently logged in MongoDB.")
            
            try:
                all_cands = list(db.candidates_col.find({}))
                bulk_rows = []
                for c in all_cands:
                    ev = c.get("evaluation") or {}
                    bulk_rows.append({
                        "Name": c.get("personal_info", {}).get("name", "Unknown"),
                        "Email": c.get("personal_info", {}).get("email", ""),
                        "Phone": c.get("personal_info", {}).get("phone", ""),
                        "Selected Role": c.get("selected_role") or "None",
                        "Match Score (%)": ev.get("final_score", 0.0),
                        "Technical Score (%)": ev.get("technical_score", 0.0),
                        "Soft Skills Score (%)": ev.get("soft_skills_score", 0.0),
                        "Recommendation": ev.get("recommendation", "N/A"),
                        "HR Status": c.get("recruiter_status", "Applied"),
                        "HR Screening Notes": c.get("recruiter_notes", "")
                    })
                df_bulk = pd.DataFrame(bulk_rows)
                bulk_csv_bytes = df_bulk.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Download Master Pipeline CSV (All Candidates)",
                    data=bulk_csv_bytes,
                    file_name="Master_Pipeline_Candidates.csv",
                    mime="text/csv",
                    use_container_width=True
                )
            except Exception as bulk_err:
                st.error(f"Error compiling master pipeline: {bulk_err}")
