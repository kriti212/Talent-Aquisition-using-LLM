import streamlit as st
from database import TalentDB

# =====================================================
# PAGE CONFIGURATION
# =====================================================
st.set_page_config(
    page_title="Talent AI - Role Configuration",
    page_icon="⚙️",
    layout="wide"
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

.config-card {
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

# Title
st.markdown('<div class="main-title">Job Role & Skill Weight Configuration</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Modify standard job role requirements, customize required skills, and adjust weights in real-time.</div>', unsafe_allow_html=True)

# Tab architecture
tab_edit, tab_add = st.tabs(["✏️ Edit Required Role Weights", "➕ Add New Job Role"])

# Fetch roles list
try:
    all_roles = db.get_all_roles()
except Exception as e:
    st.error(f"Error fetching job roles: {e}")
    all_roles = []

# Tab 1: Edit Roles
with tab_edit:
    if not all_roles:
        st.info("No job roles found in database.")
    else:
        role_names = [r["job_role"] for r in all_roles]
        selected_role_name = st.selectbox("Select Target Position to Modify", options=role_names)
        
        # Load role detail
        role_doc = next(r for r in all_roles if r["job_role"] == selected_role_name)
        skills = role_doc.get("skills", [])
        
        st.write("### ⚙️ Edit Skill Requirement Weights")
        st.write("Adjust the relative weights for each required skill below. Higher weights place more priority on matching candidate experience details during parsing.")
        
        updated_skills = []
        # Create input rows for each skill
        for idx, skill in enumerate(skills):
            s_name = skill.get("skill_name", "Skill")
            s_weight = float(skill.get("weight") or 50.0)
            
            c1, c2 = st.columns([3, 1])
            with c1:
                new_name = st.text_input(f"Skill Name {idx+1}", value=s_name, key=f"sname_{selected_role_name}_{idx}")
            with c2:
                new_weight = st.number_input(f"Skill Weight % {idx+1}", min_value=0.0, max_value=100.0, value=s_weight, key=f"sweight_{selected_role_name}_{idx}")
            
            updated_skills.append({
                "skill_name": new_name,
                "weight": new_weight
            })
            
        st.markdown("---")
        
        # Save modifications
        if st.button("💾 Save Skill Weight Modifications", type="primary", use_container_width=True):
            with st.spinner("Recomputing semantic text and updating database records..."):
                try:
                    import matcher
                    
                    # 1. Update text representation
                    skills_str = ", ".join([s.get("skill_name", "") for s in updated_skills])
                    desc_text = role_doc.get("job_description", "")
                    role_text = f"Job Role: {selected_role_name}\nDescription: {desc_text}\nSkills: {skills_str}"
                    
                    # 2. Re-generate embedding
                    model = matcher.load_bert_model()
                    new_emb = []
                    if model is not None:
                        new_emb = model.encode(role_text).tolist()
                        
                    # 3. Update MongoDB
                    db.roles_col.update_one(
                        {"_id": role_doc["_id"]},
                        {"$set": {
                            "skills": updated_skills,
                            "embedding": new_emb
                        }}
                    )
                    st.success(f"Successfully saved and updated BERT embeddings for '{selected_role_name}'!")
                    st.rerun()
                except Exception as save_err:
                    st.error(f"Error saving role updates: {save_err}")

# Tab 2: Add New Role
with tab_add:
    st.write("### ➕ Create a New Job Position Profile")
    st.write("Adding a new role automatically triggers the BERT semantic model to calculate vector embeddings, enabling immediate matching against candidate resumes.")
    
    with st.form("add_role_form"):
        new_role_name = st.text_input("Job Position Title", placeholder="e.g. Senior Frontend Engineer")
        new_role_desc = st.text_area("Job Profile Description", placeholder="Write brief details about responsibilities, tools, and requirements...")
        
        st.write("#### Add Required Skills (Minimum 3)")
        skills_inputs = []
        for idx in range(5):
            c_s1, c_s2 = st.columns([3, 1])
            with c_s1:
                sk_name = st.text_input(f"Skill Name {idx+1}", placeholder=f"e.g. ReactJS" if idx == 0 else "")
            with c_s2:
                sk_weight = st.number_input(f"Skill Weight % {idx+1}", min_value=0.0, max_value=100.0, value=50.0)
            
            if sk_name.strip():
                skills_inputs.append({
                    "skill_name": sk_name.strip(),
                    "weight": sk_weight
                })
                
        create_btn = st.form_submit_button("➕ Create Job Position & Compute Embeddings", type="primary")
        
        if create_btn:
            if not new_role_name.strip() or not new_role_desc.strip():
                st.warning("Please provide a title and job description.")
            elif len(skills_inputs) < 1:
                st.warning("Please provide at least 1 required skill.")
            else:
                with st.spinner("Generating BERT vector embeddings and creating role record..."):
                    try:
                        import matcher
                        
                        # Calculate text representation
                        skills_str = ", ".join([s.get("skill_name", "") for s in skills_inputs])
                        role_text = f"Job Role: {new_role_name}\nDescription: {new_role_desc}\nSkills: {skills_str}"
                        
                        # Generate embedding
                        model = matcher.load_bert_model()
                        emb = []
                        if model is not None:
                            emb = model.encode(role_text).tolist()
                            
                        # Insert doc
                        new_role_doc = {
                            "job_role": new_role_name.strip(),
                            "job_description": new_role_desc.strip(),
                            "skills": skills_inputs,
                            "embedding": emb
                        }
                        
                        db.roles_col.insert_one(new_role_doc)
                        st.success(f"Job Role '{new_role_name}' successfully added to database with vector index! Candidates can now apply and match for this position.")
                        st.rerun()
                    except Exception as add_err:
                        st.error(f"Error creating job role: {add_err}")
