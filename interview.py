import json
import llm_client

def generate_next_question(job_role, job_description, candidate_skills, candidate_projects, qas_history, model_name=None):
    """
    Formulates the next interview question based on job role details, candidate skills, candidate projects,
    and previous chat history. Ensures a conversational and context-aware flow.
    """
    TOTAL_QUESTIONS = 5
    matched_role = job_role
    skills = ', '.join(candidate_skills) if candidate_skills else 'Not specified'
    projects = ', '.join(candidate_projects) if candidate_projects else 'Not specified'
    
    system_prompt = f"""
            You are a recruiter.
            Candidate Matched Role:
            {matched_role}
            Job Role Description:
            {job_description}
            Candidate Skills:
            {skills}
            Candidate Projects:
            {projects}
            Rules:
            1. Ask exactly {TOTAL_QUESTIONS} questions.
            2. Ask only one question at a time. The next question must be asked only after the candidate answers the current question. If the candidate’s answer is incomplete, unclear, weak, or not satisfactory, ask relevant follow-up questions before moving to the next main question.
            3. Understand the selected job role properly from both a practical and logical perspective. Clearly understand the actual responsibilities of the role and the minimum educational qualification realistically required to perform that job. Based on this understanding, generate appropriate interview questions.
            4. If the job role requires strong theoretical understanding along with practical skills, ask questions that evaluate conceptual clarity, technical understanding, and practical application of important concepts. 
               If the job role mainly requires practical field skills and does not require advanced theoretical education or a degree, focus more on practical troubleshooting, real-world work situations, installation steps, customer handling, and technical tasks commonly performed during the job.
            Example:
            - A househelp does not need to know the chemical formula of detergent, but should know how clothes should be washed properly.
            - A Data Scientist should possess theoretical knowledge, conceptual clarity, educational background, and practical implementation skills.
            5. Analyze the educational qualification of the candidate and adjust the difficulty level accordingly. If a candidate has a strong educational background but has applied for a role that does not require advanced theoretical knowledge, do not ask unnecessarily difficult or highly academic questions unless genuinely relevant to the job role.
            6. Ask all interview questions in simple, clear, and natural English language that is easy for the candidate to understand.
            7. The interview should feel practical, realistic, and relevant to real-world job responsibilities instead of sounding like an academic examination.
            8. Do NOT write any conversational introduction, filler (e.g., 'Okay, here is my next question'), or logs. Output only the direct question text.
            9. COMPATIBILITY RULE: First, analyze the candidate's resume details (skills, projects) against the target Job Role ({matched_role}) and description:
               - If the candidate's skills, projects, or background DO NOT MATCH or have negligible overlap with the target Job Role, you MUST IGNORE the mismatched resume details completely. Ask questions focused SOLELY on the standard core responsibilities, competencies, and duties of the target Job Role ({matched_role}).
               - If there IS a match or overlap between the candidate's resume details and the target Job Role, generate interview questions that are highly compatible with BOTH the candidate's actual resume (assessing their projects and experiences) and the requirements of the Job Role.
            """
    
    messages = [{"role": "system", "content": system_prompt}]
    
    # Rebuild conversation history
    for qa in qas_history:
        messages.append({"role": "assistant", "content": qa["question"]})
        if qa.get("answer"):
            messages.append({"role": "user", "content": qa["answer"]})
            
    # If no history yet, ask the candidate to begin
    if not qas_history:
        messages.append({"role": "user", "content": "Let's start the interview. Ask your first question."})
    else:
        messages.append({"role": "user", "content": "Ask the next relevant follow-up question based on our discussion."})
        
    try:
        question = llm_client.query_llm(messages, temperature=0.7, model_name=model_name)
        return question.strip()
    except Exception as e:
        print(f"Error generating interview question: {str(e)}")
        q_idx = len(qas_history)
        
        # Rotate skill-based fallbacks if candidate has skills
        if candidate_skills:
            skill = candidate_skills[q_idx % len(candidate_skills)]
            skills_fallbacks = [
                f"Can you describe a challenging project where you utilized {skill} and how you overcame any technical hurdles?",
                f"In your experience working with {skill}, what are the key performance optimizations or best practices you follow?",
                f"How would you explain the core concepts of {skill} to a non-technical team member or client?",
                f"What is a design choice or architecture decision you had to make while using {skill} on a recent project?",
                f"How does {skill} compare to alternative tools or libraries you've used in the past?"
            ]
            return skills_fallbacks[q_idx % len(skills_fallbacks)]
            
        # Rotate general role fallbacks if candidate has no specific skills
        general_fallbacks = [
            f"Could you describe a challenging technical project you've worked on recently as a {job_role} and explain your role in it?",
            "How do you typically approach troubleshooting or debugging a complex technical issue under pressure?",
            "Can you share an experience where you had to learn a new framework or technology quickly to deliver a feature?",
            "How do you balance high-quality code standards with tight deadlines in a collaborative team?",
            "What are your primary technical goals for the next 2-3 years, and how does this job role fit into those plans?"
        ]
        return general_fallbacks[q_idx % len(general_fallbacks)]

def evaluate_single_qa(job_role, question, answer, model_name=None):
    """
    Evaluates a single question-answer response based on specific rubrics.
    Returns (technical_score, soft_skills_score, feedback, extra_eval_dict).
    """
    system_prompt = (
        "You are an expert interviewer. Evaluate the candidate's answer to the question based on the rubrics below.\n\n"
        "You MUST perform step-by-step chain of thought reasoning for the scores before writing the final scores.\n"
        "You MUST return ONLY a valid JSON object matching the requested schema.\n\n"
        "--- TECHNICAL COMPETENCE RUBRICS ---\n"
        "1. Accuracy & Correctness (0-100):\n"
        "   - 90-100: Flawless accuracy, correct industry terms, directly answers the prompt.\n"
        "   - 70-89: Conceptually sound with minor factual gaps or slight oversimplification.\n"
        "   - 50-69: Vague or partially incorrect, misses key technical concepts.\n"
        "   - 1-49: Completely incorrect, misunderstands core computer science or business concepts.\n"
        "   - 0: Blank, 'I don't know', or completely irrelevant.\n"
        "2. Completeness & Depth (0-100):\n"
        "   - 90-100: Covers edge cases, optimization, performance, or system design trade-offs.\n"
        "   - 70-89: Good detail, addresses core requirements, lacks deep structural/architectural depth.\n"
        "   - 50-69: Extremely brief, shallow explanation, only defines terms without context.\n"
        "   - 1-49: No detail, single word or sentence answer with zero context.\n\n"
        "--- SOFT SKILLS RUBRICS ---\n"
        "1. Structure & Organization (0-100):\n"
        "   - 90-100: Answers using structured frameworks (like STAR method: Situation, Task, Action, Result).\n"
        "   - 70-89: Logical narrative sequence, easy to follow, minor gaps in STAR context.\n"
        "   - 50-69: Unstructured, jumps between points, hard to follow candidate's train of thought.\n"
        "   - 1-49: Unprofessional, chaotic structure, mumbling or highly fragmented response.\n"
        "2. Clarity & Articulation (0-100):\n"
        "   - 90-100: Precise vocabulary, concise, professional tone, zero filler words.\n"
        "   - 70-89: Clear communication, minor vocabulary gaps, occasional fillers (e.g. 'um', 'like').\n"
        "   - 50-69: Hard to follow, heavy filler reliance, grammatically weak or disorganized phrasing.\n"
        "   - 1-49: Mumbled, illegible, or unstructured verbal transcription.\n\n"
        "Conform strictly to this JSON schema:\n"
        "{\n"
        "  \"technical_evaluation_reasoning\": \"Chain-of-thought analysis of correctness, terminology, and gaps.\",\n"
        "  \"technical_sub_scores\": {\n"
        "    \"accuracy_correctness\": 85.0,\n"
        "    \"completeness_depth\": 80.0\n"
        "  },\n"
        "  \"soft_skills_evaluation_reasoning\": \"Chain-of-thought analysis of narrative structure, STAR flow, and phrasing.\",\n"
        "  \"soft_skills_sub_scores\": {\n"
        "    \"structure_organization\": 90.0,\n"
        "    \"clarity_articulation\": 75.0\n"
        "  },\n"
        "  \"feedback\": \"Constructive recommendations to improve candidate answers.\"\n"
        "}"
    )
    
    user_prompt = (
        f"Role: {job_role}\n"
        f"Question: {question}\n"
        f"Answer: {answer}"
    )
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]
    
    try:
        response_content = llm_client.query_llm(messages, temperature=0.1, json_mode=True, model_name=model_name)
        response_content = response_content.strip()
        
        # Locate the JSON block inside the response
        first_brace = response_content.find('{')
        last_brace = response_content.rfind('}')
        if first_brace != -1 and last_brace != -1:
            response_content = response_content[first_brace:last_brace+1]
            
        result = json.loads(response_content)
        
        # Extract sub-scores
        tech_sub = result.get("technical_sub_scores") or {}
        soft_sub = result.get("soft_skills_sub_scores") or {}
        
        accuracy = float(tech_sub.get("accuracy_correctness") or 0.0)
        depth = float(tech_sub.get("completeness_depth") or 0.0)
        structure = float(soft_sub.get("structure_organization") or 0.0)
        clarity = float(soft_sub.get("clarity_articulation") or 0.0)
        
        # Compute final average scores for backward compatibility
        tech_score = round((accuracy + depth) / 2.0, 2)
        soft_score = round((structure + clarity) / 2.0, 2)
        
        extra_eval = {
            "technical_evaluation_reasoning": result.get("technical_evaluation_reasoning", ""),
            "technical_sub_scores": {
                "accuracy_correctness": accuracy,
                "completeness_depth": depth
            },
            "soft_skills_evaluation_reasoning": result.get("soft_skills_evaluation_reasoning", ""),
            "soft_skills_sub_scores": {
                "structure_organization": structure,
                "clarity_articulation": clarity
            }
        }
        
        return tech_score, soft_score, result.get("feedback", "No feedback provided."), extra_eval
    except Exception as e:
        print(f"Error in evaluate_single_qa: {e}")
        return 0.0, 0.0, f"Evaluation failed: {str(e)}", {}

def evaluate_candidate(candidate_name, job_role, qas_history, model_name=None):
    """
    Synthesizes the overall technical and soft skill summaries and calculates final averages.
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
        "You are an expert recruiter. Analyze the interview transcript (including pre-evaluated scores for each question) "
        "and generate a final recruitment summary card. You MUST return ONLY a valid JSON object. "
        "Do not include markdown block wrapping (```json) or notes. Conform strictly to this schema:\n"
        "{\n"
        "  \"technical_summary\": \"Overall technical strengths, gaps, and competencies.\",\n"
        "  \"soft_skill_summary\": \"Overall communication clarity, style, and tone.\",\n"
        "  \"recommendation\": \"Strong Hire / Hire / No Hire\"\n"
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
        
        # Inject computed scores
        result["technical_score"] = round(avg_tech, 2)
        result["soft_skills_score"] = round(avg_soft, 2)
        result["final_score"] = round(avg_final, 2)
        
        # Build detailed feedback array from qas_history to save to final report
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
            "technical_summary": "Failed to compile summary automatically.",
            "soft_skill_summary": "Failed to compile summary automatically.",
            "recommendation": "Manual Transcript Review Required"
        }
