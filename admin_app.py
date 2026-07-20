import streamlit as st

# =====================================================
# PROGRAMMATIC MULTIPAGE ROUTING
# =====================================================
pg = st.navigation([
    st.Page("admin_pages/0_Pipeline_Overview.py", title="Pipeline Overview", icon="📊", default=True),
    st.Page("admin_pages/1_Candidate_Evaluation.py", title="Candidate Evaluation", icon="🎯"),
    st.Page("admin_pages/2_Transcript_Inspector.py", title="Transcript & Audio", icon="🎤"),
    st.Page("admin_pages/3_Resume_Viewer.py", title="Resume Details", icon="📄"),
    st.Page("admin_pages/4_Shortlisting_Panel.py", title="Shortlisting & Action", icon="⚡"),
    st.Page("admin_pages/5_Role_Configuration.py", title="Job Role Settings", icon="⚙️")
])

pg.run()
