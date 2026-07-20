import streamlit as st
import pandas as pd
from database import TalentDB

# =====================================================
# PAGE CONFIGURATION
# =====================================================
st.set_page_config(
    page_title="Talent AI - Candidate Evaluation",
    page_icon="🎯",
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

.card-summary {
    background: linear-gradient(135deg, rgba(99, 102, 241, 0.08), rgba(168, 85, 247, 0.08));
    border-radius: 12px;
    padding: 24px;
    border: 1px solid rgba(99, 102, 241, 0.2);
    box-shadow: 0 4px 15px rgba(99, 102, 241, 0.05);
    margin-bottom: 20px;
}

.big-percentage {
    font-size: 3.5rem;
    font-weight: 800;
    color: #ffffff;
    background: linear-gradient(135deg, #818cf8, #c084fc);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}
</style>
""", unsafe_allow_html=True)

# Database
@st.cache_resource(show_spinner=False)
def get_db():
    return TalentDB()

db = get_db()

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
        eval_report = candidate.get("evaluation", {})
        qas = candidate.get("qas", [])
        
        st.markdown(f'<div class="main-title">Evaluation Scorecard: {name}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="subtitle">AI Match score, sub-metrics split, and weighted skill analysis for target role: <b>{role_name}</b>.</div>', unsafe_allow_html=True)

        if not eval_report:
            st.warning("⚠️ This candidate has not completed their technical interview yet.")
        else:
            col_l, col_r = st.columns([1, 1])
            
            # Left: AI Match Score & Metrics Split
            with col_l:
                st.write("### 🏆 AI Match Score")
                final_score = eval_report.get("final_score", 0.0)
                
                st.markdown(f"""
                <div class="card-summary">
                    <div style="display: flex; align-items: center; justify-content: space-between;">
                        <div>
                            <span style="color: #94a3b8; font-size: 0.9rem; text-transform: uppercase;">Overall Alignment</span>
                            <div class="big-percentage">{final_score}%</div>
                        </div>
                        <div style="text-align: right;">
                            <span style="color: #cbd5e1; font-weight: 500;">Recommendation</span>
                            <div style="font-size: 1.3rem; font-weight: 700; color: #4ade80;">{eval_report.get('recommendation', 'N/A')}</div>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                st.write("### 📊 Technical vs. Soft Skill Split")
                # Collect sub-scores
                accs = []
                deps = []
                structs = []
                clars = []
                
                for qa in qas:
                    extra = qa.get("extra_eval") or {}
                    t_sub = extra.get("technical_sub_scores") or {}
                    s_sub = extra.get("soft_skills_sub_scores") or {}
                    
                    accs.append(float(t_sub.get("accuracy_correctness") or 0.0))
                    deps.append(float(t_sub.get("completeness_depth") or 0.0))
                    structs.append(float(s_sub.get("structure_organization") or 0.0))
                    clars.append(float(s_sub.get("clarity_articulation") or 0.0))
                    
                avg_acc = sum(accs) / len(accs) if accs else 0.0
                avg_dep = sum(deps) / len(deps) if deps else 0.0
                avg_struct = sum(structs) / len(structs) if structs else 0.0
                avg_clar = sum(clars) / len(clars) if clars else 0.0
                
                metrics_data = {
                    "Competency Metric": [
                        "Accuracy & Correctness", 
                        "Completeness & Depth", 
                        "Structure (STAR Flow)", 
                        "Clarity & Articulation"
                    ],
                    "Competency Score (%)": [avg_acc, avg_dep, avg_struct, avg_clar],
                    "Category": ["Technical Competence", "Technical Competence", "Soft Skills", "Soft Skills"]
                }
                
                df_metrics = pd.DataFrame(metrics_data)
                # Plot side-by-side or standard bar chart
                st.bar_chart(df_metrics.set_index("Competency Metric")["Competency Score (%)"], height=260)

            # Right: Weighted Skill Scorecard
            with col_r:
                st.write("### ⚖️ Weighted Skill Scorecard")
                
                # Fetch role weights
                role_info = db.get_role_by_name(role_name)
                
                if not role_info:
                    st.info("No skill weights seeded for this job role.")
                else:
                    required_skills = role_info.get("skills", [])
                    extracted_skills = candidate.get("extracted_skills", [])
                    
                    # Convert to lower case for comparison
                    cand_skills_lower = [s.lower().strip() for s in extracted_skills]
                    
                    rows = []
                    chart_labels = []
                    chart_weights = []
                    chart_candidate = []
                    
                    for req in required_skills:
                        req_name = req.get("skill_name", "Unknown")
                        weight = float(req.get("weight") or 0.0)
                        
                        # Check if matched (fuzzy containment check)
                        is_matched = any(req_name.lower() in s or s in req_name.lower() for s in cand_skills_lower)
                        cand_possession = weight if is_matched else 0.0
                        
                        rows.append({
                            "Skill Name": req_name,
                            "Required Weight (%)": weight,
                            "Candidate Match": "✅ Found in Resume" if is_matched else "❌ Missing in Resume"
                        })
                        
                        chart_labels.append(req_name)
                        chart_weights.append(weight)
                        chart_candidate.append(cand_possession)
                        
                    df_skills = pd.DataFrame(rows)
                    st.dataframe(df_skills, use_container_width=True, hide_index=True)
                    
                    # Plot comparison
                    chart_df = pd.DataFrame({
                        "Skill Name": chart_labels,
                        "Required Weight": chart_weights,
                        "Candidate Match Strength": chart_candidate
                    }).set_index("Skill Name")
                    
                    st.write("#### Required Skill Weight vs Match Comparison")
                    st.bar_chart(chart_df, height=220)
