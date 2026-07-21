import json
import llm_client

def generate_next_question(job_role, job_description, candidate_skills, candidate_projects, qas_history, model_name=None):
    """
    Formulates the next interview question based on job role details, candidate skills, candidate projects,
    and previous chat history. Ensures a conversational, highly relevant, anti-hallucination flow.
    """
    TOTAL_QUESTIONS = 5
    matched_role = job_role
    skills = ', '.join(candidate_skills) if candidate_skills else 'Not specified'
    projects = ', '.join(candidate_projects) if candidate_projects else 'Not specified'
    
    system_prompt = f"""
    You are an expert technical interviewer conducting a live screening interview.
    Target Job Role: {matched_role}
    Job Description: {job_description}
    Candidate Claimed Skills: {skills}
    Candidate Claimed Projects: {projects}

    STRICT ANTI-HALLUCINATION & RELEVANCE RULES:
    1. Ask exactly {TOTAL_QUESTIONS} questions overall, one question at a time.
    2. NEVER hallucinate non-existent software, libraries, companies, or technologies.
    3. Ground your question strictly in real-world engineering and practical responsibilities of the role: {matched_role}.
    4. COMPATIBILITY RULE:
       - If the candidate's skills/projects overlap with {matched_role}, ask a focused question linking their actual skills/projects to the requirements of {matched_role}.
       - If the candidate's skills/projects DO NOT match {matched_role}, IGNORE the mismatched resume details completely and ask standard, practical core questions required for {matched_role}.
    5. Keep the question concise, clear, and direct (maximum 2 sentences).
    6. Do NOT write any introduction, greetings, explanations, or meta-comments (e.g. 'Question 2:'). Output ONLY the raw question text.
    """
    
    messages = [{"role": "system", "content": system_prompt}]
    
    # Rebuild conversation history
    for qa in qas_history:
        messages.append({"role": "assistant", "content": qa["question"]})
        if qa.get("answer"):
            messages.append({"role": "user", "content": qa["answer"]})
            
    # Ask first question or follow-up
    if not qas_history:
        messages.append({"role": "user", "content": f"Begin the interview for the role of {matched_role}. Ask your first question."})
    else:
        messages.append({"role": "user", "content": "Ask the next relevant, concise technical question based on our interview flow."})
        
    try:
        question = llm_client.query_llm(messages, temperature=0.5, model_name=model_name)
        return question.strip()
    except Exception as e:
        print(f"Error generating interview question: {str(e)}")
        q_idx = len(qas_history)
        
        # Skill-based fallbacks
        if candidate_skills:
            skill = candidate_skills[q_idx % len(candidate_skills)]
            skills_fallbacks = [
                f"Can you describe a challenging project where you utilized {skill} and how you solved technical hurdles?",
                f"In your experience working with {skill}, what are the key performance optimizations or best practices you follow?",
                f"How would you explain the core architecture of {skill} to a team member?",
                f"What design choices or tradeoffs did you make while using {skill} on a recent project?",
                f"How does {skill} compare to alternative tools you have used in past projects?"
            ]
            return skills_fallbacks[q_idx % len(skills_fallbacks)]
            
        # General fallbacks
        general_fallbacks = [
            f"Could you describe a technical project you worked on recently as a {job_role} and explain your specific role?",
            "How do you approach debugging a complex technical issue under tight deadlines?",
            "Can you share an experience where you had to learn a new framework quickly to deliver a feature?",
            "How do you ensure high code quality standards while working in a fast-paced team environment?",
            "What technical skills or architecture concepts are you aiming to master in the next 1-2 years?"
        ]
        return general_fallbacks[q_idx % len(general_fallbacks)]

def evaluate_single_qa(job_role, question, answer, model_name=None):
    """
    Evaluates a single question-answer response.
    Returns (technical_score, soft_skills_score, feedback, extra_eval_dict).
    Forces short and crisp feedback.
    """
    if answer.strip() == "[Question Skipped]" or not answer.strip():
        return 0.0, 0.0, "• Question was skipped by the candidate.", {
            "technical_evaluation_reasoning": "Candidate skipped this question.",
            "technical_sub_scores": {"accuracy_correctness": 0.0, "completeness_depth": 0.0},
            "soft_skills_evaluation_reasoning": "Candidate skipped this question.",
            "soft_skills_sub_scores": {"structure_organization": 0.0, "clarity_articulation": 0.0}
        }

    system_prompt = (
        "You are an expert technical interviewer. Evaluate the candidate's answer based on technical accuracy and communication style.\n\n"
        "RULES FOR FEEDBACK:\n"
        "- The feedback MUST be short and crisp (maximum 2 bullet points, under 30 words total).\n"
        "- Do NOT write long paragraphs or repetitive text.\n\n"
        "Conform strictly to this JSON schema:\n"
        "{\n"
        "  \"technical_evaluation_reasoning\": \"Brief analysis of accuracy and depth.\",\n"
        "  \"technical_sub_scores\": {\n"
        "    \"accuracy_correctness\": 85.0,\n"
        "    \"completeness_depth\": 80.0\n"
        "  },\n"
        "  \"soft_skills_evaluation_reasoning\": \"Brief analysis of communication structure.\",\n"
        "  \"soft_skills_sub_scores\": {\n"
        "    \"structure_organization\": 90.0,\n"
        "    \"clarity_articulation\": 80.0\n"
        "  },\n"
        "  \"feedback\": \"• Bullet 1: Key technical strength.\\n• Bullet 2: Concise gap or tip.\"\n"
        "}"
    )
    
    user_prompt = (
        f"Target Role: {job_role}\n"
        f"Question: {question}\n"
        f"Candidate Answer: {answer}"
    )
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]
    
    try:
        response_content = llm_client.query_llm(messages, temperature=0.1, json_mode=True, model_name=model_name)
        response_content = response_content.strip()
        
        first_brace = response_content.find('{')
        last_brace = response_content.rfind('}')
        if first_brace != -1 and last_brace != -1:
            response_content = response_content[first_brace:last_brace+1]
            
        result = json.loads(response_content)
        
        tech_sub = result.get("technical_sub_scores") or {}
        soft_sub = result.get("soft_skills_sub_scores") or {}
        
        accuracy = float(tech_sub.get("accuracy_correctness") or 0.0)
        depth = float(tech_sub.get("completeness_depth") or 0.0)
        structure = float(soft_sub.get("structure_organization") or 0.0)
        clarity = float(soft_sub.get("clarity_articulation") or 0.0)
        
        tech_score = round((accuracy + depth) / 2.0, 2)
        soft_score = round((structure + clarity) / 2.0, 2)
        
        extra_eval = {
            "technical_evaluation_reasoning": result.get("technical_evaluation_reasoning", ""),
            "technical_sub_scores": {"accuracy_correctness": accuracy, "completeness_depth": depth},
            "soft_skills_evaluation_reasoning": result.get("soft_skills_evaluation_reasoning", ""),
            "soft_skills_sub_scores": {"structure_organization": structure, "clarity_articulation": clarity}
        }
        
        feedback_text = result.get("feedback", "• Answer evaluated.")
        if not feedback_text.startswith("•"):
            feedback_text = "• " + feedback_text.replace("\n", "\n• ")
            
        return tech_score, soft_score, feedback_text, extra_eval
    except Exception as e:
        print(f"Error in evaluate_single_qa: {e}")
        return 0.0, 0.0, "• Evaluation pending manual review.", {}

def evaluate_candidate(candidate_name, job_role, qas_history, model_name=None):
    """
    Synthesizes final technical and soft skill summaries.
    Enforces SHORT AND CRISP bulleted summaries (max 3 bullets each).
    """
    tech_scores = []
    soft_scores = []
    
    transcript_lines = []
    for idx, qa in enumerate(qas_history):
        q = qa.get("question", "")
        a = qa.get("answer", "")
        t_score = float(qa.get("technical_score") or 0.0)
        s_score = float(qa.get("soft_skills_score") or 0.0)
        
        tech_scores.append(t_score)
        soft_scores.append(s_score)
        
        transcript_lines.append(
            f"Q{idx+1}: {q}\n"
            f"A{idx+1}: {a}\n"
            f"[Tech Score: {t_score}, Soft Score: {s_score}]"
        )
        
    transcript_text = "\n\n".join(transcript_lines)
    
    avg_tech = sum(tech_scores) / len(tech_scores) if tech_scores else 0.0
    avg_soft = sum(soft_scores) / len(soft_scores) if soft_scores else 0.0
    avg_final = (avg_tech + avg_soft) / 2.0
    
    system_prompt = (
        "You are an expert recruiter. Analyze the candidate transcript and generate a SHORT & CRISP summary card.\n"
        "STRICT FORMATTING RULES:\n"
        "- technical_summary MUST be a bulleted list of 2-3 short, crisp sentences (max 40 words total).\n"
        "- soft_skill_summary MUST be a bulleted list of 2-3 short, crisp sentences (max 40 words total).\n"
        "- recommendation MUST be one of: 'Strong Hire', 'Hire', 'Consider', 'No Hire'.\n\n"
        "You MUST return ONLY a valid JSON object matching this schema:\n"
        "{\n"
        "  \"technical_summary\": \"• Demonstrated strong knowledge of Python.\\n• Solid understanding of APIs.\\n• Needs minor work on system design.\",\n"
        "  \"soft_skill_summary\": \"• Clear, concise communication.\\n• Structured responses using practical examples.\",\n"
        "  \"recommendation\": \"Hire\"\n"
        "}"
    )
    
    user_prompt = (
        f"Candidate: {candidate_name}\n"
        f"Target Role: {job_role}\n\n"
        f"Transcript & Scores:\n{transcript_text}"
    )
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]
    
    try:
        response_content = llm_client.query_llm(messages, temperature=0.1, json_mode=True, model_name=model_name)
        response_content = response_content.strip()
        if response_content.startswith("```json"):
            response_content = response_content[7:]
        if response_content.endswith("```"):
            response_content = response_content[:-3]
        response_content = response_content.strip()
        
        result = json.loads(response_content)
        
        result["technical_score"] = round(avg_tech, 2)
        result["soft_skills_score"] = round(avg_soft, 2)
        result["final_score"] = round(avg_final, 2)
        
        detailed = []
        for idx, qa in enumerate(qas_history):
            detailed.append({
                "question_number": idx + 1,
                "question": qa.get("question", ""),
                "answer": qa.get("answer", ""),
                "technical_score": float(qa.get("technical_score") or 0.0),
                "soft_skills_score": float(qa.get("soft_skills_score") or 0.0),
                "feedback": qa.get("feedback", ""),
                "extra_eval": qa.get("extra_eval", {})
            })
        result["detailed_feedback"] = detailed
        
        return result
    except Exception as e:
        print(f"Error in overall evaluate_candidate: {e}")
        return {
            "technical_score": round(avg_tech, 2),
            "soft_skills_score": round(avg_soft, 2),
            "final_score": round(avg_final, 2),
            "detailed_feedback": [
                {
                    "question_number": idx + 1,
                    "question": qa.get("question", ""),
                    "answer": qa.get("answer", ""),
                    "technical_score": float(qa.get("technical_score") or 0.0),
                    "soft_skills_score": float(qa.get("soft_skills_score") or 0.0),
                    "feedback": qa.get("feedback", ""),
                    "extra_eval": qa.get("extra_eval", {})
                } for idx, qa in enumerate(qas_history)
            ],
            "technical_summary": "• Completed candidate interview.\n• Evaluated across standard domain skills.",
            "soft_skill_summary": "• Clear articulation during technical Q&A session.",
            "recommendation": "Manual Transcript Review Required"
        }
