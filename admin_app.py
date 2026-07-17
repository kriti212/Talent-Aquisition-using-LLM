import streamlit as st

# =====================================================
# PROGRAMMATIC MULTIPAGE ROUTING
# =====================================================
pg = st.navigation([
    st.Page("admin_pages/0_Dashboard_Home.py", title="Home Dashboard", icon="🏠", default=True),
    st.Page("admin_pages/1_Candidate_Directory.py", title="Candidate Directory", icon="📇"),
    st.Page("admin_pages/2_Interview_Scoring.py", title="Interview Scoring", icon="🎯"),
    st.Page("admin_pages/3_Resume_Viewer.py", title="Resume Details", icon="📄")
])

pg.run()
