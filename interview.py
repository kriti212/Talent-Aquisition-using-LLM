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

def evaluate_candidate(candidate_name, job_role, qas_history, model_name=None):
    """
    Reviews the candidate transcript and generates a graded evaluation scoring card.
    """
    system_prompt = (
        "You are an expert technical interviewer and talent assessor. Your job is to review the "
        "provided interview transcript and generate a structured grading scorecard.\n\n"
        "You MUST return ONLY a valid JSON object. Do not include markdown block wrapping (```json), "
        "notes, or explanations. Conform strictly to this schema:\n"
        "{\n"
        "  \"technical_score\": 85.50 (float, 0.00 to 100.00 representing overall technical competence),\n"
        "  \"soft_skills_score\": 90.00 (float, 0.00 to 100.00 representing communication clarity and style),\n"
        "  \"final_score\": 87.75 (float, 0.00 to 100.00 representing overall fit),\n"
        "  \"detailed_feedback\": [\n"
        "    {\n"
        "      \"question_number\": 1,\n"
        "      \"question\": \"The question asked\",\n"
        "      \"answer\": \"The candidate's response\",\n"
        "      \"score\": 80.00 (float, 0.00 to 100.00),\n"
        "      \"feedback\": \"Constructive feedback for this specific response\"\n"
        "    }\n"
        "  ],\n"
        "  \"technical_summary\": \"Detailed overview of technical strengths, core gaps, and tools mastered.\",\n"
        "  \"soft_skill_summary\": \"Assessment of structure, vocabulary, confidence, and empathy.\",\n"
        "  \"recommendation\": \"Strong Hire / Hire / No Hire\"\n"
        "}\n\n"
        "Analyze the depth, correctness, and relevance of each answer carefully. Be objective and fair."
    )
    
    # Format the transcript text
    transcript_lines = []
    for i, qa in enumerate(qas_history):
        q = qa.get("question", "")
        a = qa.get("answer", "")
        transcript_lines.append(f"Q{i+1}: {q}\nA{i+1}: {a}")
        
    transcript_text = "\n\n".join(transcript_lines)
    
    user_prompt = (
        f"Candidate Name: {candidate_name}\n"
        f"Target Role: {job_role}\n\n"
        f"Interview Transcript:\n{transcript_text}"
    )
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]
    
    try:
        response_content = llm_client.query_llm(messages, temperature=0.1, json_mode=True, model_name=model_name)
        
        # Clean markdown characters if they slip in
        response_content = response_content.strip()
        if response_content.startswith("```json"):
            response_content = response_content[7:]
        if response_content.endswith("```"):
            response_content = response_content[:-3]
        response_content = response_content.strip()
        
        evaluation = json.loads(response_content)
        return evaluation
    except Exception as e:
        print(f"Error evaluating candidate transcript: {str(e)}")
        # Construct fallback scorecard
        return {
            "technical_score": 0.0,
            "soft_skills_score": 0.0,
            "final_score": 0.0,
            "detailed_feedback": [
                {
                    "question_number": i + 1,
                    "question": qa.get("question", ""),
                    "answer": qa.get("answer", ""),
                    "score": 0.0,
                    "feedback": "Evaluation failed due to system/network issues."
                } for i, qa in enumerate(qas_history)
            ],
            "technical_summary": "Failed to generate summary automatically.",
            "soft_skill_summary": "Failed to generate summary automatically.",
            "recommendation": "Manual Transcript Review Required"
        }
