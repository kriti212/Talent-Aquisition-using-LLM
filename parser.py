import pdfplumber
import json
import re
import llm_client

def post_process_education_years(education_list, raw_text):
    """
    Post-processes the parsed education list to ensure that if a date range
    exists in the raw text, the graduation year is set to the end year of the range.
    """
    lines = [line.strip() for line in raw_text.split('\n') if line.strip()]
    
    for edu in education_list:
        inst = edu.get("institution", "")
        deg = edu.get("degree", "")
        year = edu.get("year")
        
        # Collect all candidate indices where either inst or deg matches
        candidate_indices = []
        for idx, line in enumerate(lines):
            match_inst = inst and inst.lower() in line.lower()
            match_deg = deg and deg.lower() in line.lower()
            if match_inst or match_deg:
                candidate_indices.append(idx)
                
        # Check adjacent lines of each index for a year range
        for idx in candidate_indices:
            search_lines = lines[idx : min(idx + 4, len(lines))]
            combined_search_text = " ".join(search_lines)
            
            # Find range YYYY - YYYY
            range_matches = re.findall(r'\b(20\d{2})\s*(?:-|–|—|to)\s*(20\d{2})\b', combined_search_text)
            if range_matches:
                start_yr, end_yr = range_matches[0]
                edu["year"] = int(end_yr)
                print(f"[Post-process] Overrode year for '{deg}' at '{inst}' from {year} to {end_yr}")
                break

def extract_text_column_aware(page):
    """
    Extracts text from a page, detecting if it has a two-column layout
    and extracting column-by-column to avoid horizontal merging.
    """
    try:
        width = page.width
        words = page.extract_words()
        if not words:
            return page.extract_text() or ""
            
        best_x = None
        min_crossings = float('inf')
        
        # Test candidate split points (between 20% and 80% of page width)
        for pct in range(20, 81, 2):
            x = (pct / 100.0) * width
            crossings = 0
            for w in words:
                # Add a padding to avoid splitting words that cross
                if w['x0'] - 2 < x < w['x1'] + 2:
                    crossings += 1
            
            if crossings < min_crossings:
                min_crossings = crossings
                best_x = x
                
        # If crossings are very low (gutter exists), split page
        if best_x is not None and min_crossings <= 3:
            left_bbox = (0, 0, best_x, page.height)
            right_bbox = (best_x, 0, width, page.height)
            
            left_page = page.within_bbox(left_bbox)
            right_page = page.within_bbox(right_bbox)
            
            left_text = left_page.extract_text() or ""
            right_text = right_page.extract_text() or ""
            
            if left_text.strip() and right_text.strip():
                return left_text + "\n\n" + right_text
            
    except Exception as e:
        print(f"Error in column-aware extraction: {str(e)}")
        
    return page.extract_text() or ""

def extract_text_from_pdf(pdf_file_path):
    """
    Extracts plain text from a PDF file using pdfplumber with column-aware layout support.
    """
    text = ""
    try:
        with pdfplumber.open(pdf_file_path) as pdf:
            for page in pdf.pages:
                page_text = extract_text_column_aware(page)
                if page_text:
                    text += page_text + "\n"
    except Exception as e:
        print(f"Error reading PDF with pdfplumber: {str(e)}")
        raise e
    return text.strip()

def extract_text_from_txt(txt_file_path):
    """
    Extracts plain text from a text file.
    """
    try:
        with open(txt_file_path, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read().strip()
    except Exception as e:
        print(f"Error reading TXT file: {str(e)}")
        raise e

def parse_resume_text_with_llm(resume_text, model_name=None):
    """
    Sends the extracted resume text to Ollama and requests a structured JSON profile back.
    """
    system_prompt = (
        "You are an expert resume parsing assistant. Analyze the provided resume text and extract "
        "the key details in a clean, structured JSON format. You MUST return ONLY a valid JSON object. "
        "Do not include any introductions, explanations, markdown wrapping (such as ```json), or notes. "
        "Conform strictly to the following JSON schema:\n\n"
        "{\n"
        "  \"name\": \"Full Name (string, default to 'Unknown')\",\n"
        "  \"email\": \"Email address (string, default to '')\",\n"
        "  \"phone\": \"Phone number (string, default to '')\",\n"
        "  \"skills\": [\"Skill 1\", \"Skill 2\", ...],\n"
        "  \"projects\": [\"Project 1\", \"Project 2\", ...],\n"
        "  \"education\": [\n"
        "    {\n"
        "      \"degree\": \"Degree title (e.g. Master of Science in Data Science or Bachelor of Science in Mathematics)\",\n"
        "      \"institution\": \"University or School name\",\n"
        "      \"year\": 2022\n"
        "    }\n"
        "  ],\n"
        "  \"years_of_experience\": 3.5,\n"
        "  \"current_location\": \"City, State/Country\"\n"
        "}\n\n"
        "For 'education' entries, you MUST extract all degrees and courses. For the 'year' field, extract ONLY the completion/graduation year as an integer (e.g. extract 2027 from a range like '2025 - 2027', and 2024 from '2021 - 2024'). NEVER use the starting year of a range as the graduation year. If some fields like education year cannot be parsed, set them to null. "
        "Ensure years_of_experience is represented as a float."
    )
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Resume Text:\n{resume_text}"}
    ]
    
    try:
        # Force JSON mode
        response_content = llm_client.query_llm(messages, temperature=0.0, json_mode=True, model_name=model_name)
        
        # Clean response if LLM added markdown formatting
        response_content = response_content.strip()
        if response_content.startswith("```json"):
            response_content = response_content[7:]
        if response_content.endswith("```"):
            response_content = response_content[:-3]
        response_content = response_content.strip()
        
        parsed_json = json.loads(response_content)
        if "education" in parsed_json:
            post_process_education_years(parsed_json["education"], resume_text)
        return parsed_json
    except Exception as e:
        print(f"Error parsing resume with LLM: {str(e)}")
        # Fallback to a structured empty response so the app doesn't crash
        return {
            "name": "Unknown Candidate",
            "email": "",
            "phone": "",
            "skills": [],
            "projects": [],
            "education": [],
            "years_of_experience": 0.0,
            "current_location": ""
        }

def parse_resume_and_match_jobs_with_llm(resume_text, all_roles, model_name=None):
    """
    Sends the resume text AND all job roles to the LLM.
    Returns (parsed_profile, recommendations).
    """
    # 1. Format job roles for the prompt
    roles_text_list = []
    for r in all_roles:
        role_name = r.get("job_role", "")
        desc = r.get("job_description", "")
        skills_str = ", ".join([f"{s.get('skill_name')} (weight: {s.get('weight')})" for s in r.get("skills", [])])
        roles_text_list.append(f"- Role: {role_name}\n  Description: {desc}\n  Required Skills: {skills_str}")
        
    roles_formatted = "\n\n".join(roles_text_list)
    
    # 2. Construct system prompt
    system_prompt = (
        "You are an expert recruitment assistant. Analyze the candidate's resume text and match "
        "their skills/experience against the list of available job roles.\n\n"
        "Your task is to:\n"
        "1. Extract candidate profile details (Name, Email, Phone, Skills, Projects, Education, Experience, Location).\n"
        "   Strict Extraction Guidelines to ensure consistency and correctness:\n"
        "   - Extract fields strictly from the provided resume text. Do not hallucinate or guess details.\n"
        "   - For 'education': You MUST extract all degrees and courses mentioned in the resume (e.g. both Master's and Bachelor's degrees). For each entry, provide:\n"
        "     * 'degree': Extract the exact degree/course title (e.g. 'Master of Science' or 'Bachelor of Science'). If a major or specialization (like 'Mathematics' or 'Data Science') is mentioned adjacent or associated with the degree, format it as 'Degree Name in Major' (e.g., 'Master of Science in Data Science' or 'Bachelor of Science in Mathematics'). Do not cross-associate majors or confuse columns in multi-column layouts.\n"
        "     * 'institution': Extract the university/school name (e.g. 'Chennai Mathematical Institute' or 'St. Xavier’s College').\n"
        "     * 'year': Extract ONLY the graduation/completion year as an integer. If a range is given (e.g., '2025 - 2027' or '2021 - 2024'), the year MUST be the upper/end year of the range (e.g. 2027 for '2025 - 2027', 2024 for '2021 - 2024'). NEVER extract the starting year of a range (like 2025 or 2021) as the graduation year. If the course is ongoing or has a future end year, still return that end year as the expected graduation year. If no year can be determined, return null.\n"
        "   - For 'years_of_experience': Extract or calculate the total experience in years as a float. If not specified, default to 0.0.\n"
        "2. Evaluate the candidate against all provided job roles. Recommend the top 5 matched job roles "
        "by calculating a semantic compatibility match score (percentage float from 0.00 to 100.00) for each, "
        "taking into account job descriptions, required skills, and skill weights. You MUST select the "
        "recommended job roles STRICTLY from the provided list of Available Job Roles. Do not fabricate, "
        "invent, or modify any job role names. Every recommended job role's name must exactly match one "
        "of the job roles provided in the 'Available Job Roles' list.\n\n"
        "You MUST return ONLY a valid JSON object. Do not include introductory text, notes, or markdown formatting (like ```json).\n"
        "Conform strictly to the following JSON schema:\n"
        "{\n"
        "  \"profile\": {\n"
        "    \"name\": \"Full Name (or 'Unknown')\",\n"
        "    \"email\": \"Email address (or empty string)\",\n"
        "    \"phone\": \"Phone number (or empty string)\",\n"
        "    \"skills\": [\"Skill 1\", \"Skill 2\", ...],\n"
        "    \"projects\": [\"Project 1\", \"Project 2\", ...],\n"
        "    \"education\": [\n"
        "      {\n"
        "        \"degree\": \"Degree title\",\n"
        "        \"institution\": \"University/School name\",\n"
        "        \"year\": 2022 (int or null)\n"
        "      }\n"
        "    ],\n"
        "    \"years_of_experience\": 3.5 (float),\n"
        "    \"current_location\": \"City, State/Country (or empty string)\"\n"
        "  },\n"
        "  \"recommendations\": [\n"
        "    {\n"
        "      \"job_role\": \"Job Role Name\",\n"
        "      \"match_score\": 85.50 (float representing match percentage),\n"
        "      \"reason\": \"Brief explanation of why this candidate is a good match based on their skills\"\n"
        "    }\n"
        "  ]\n"
        "}"
    )
    
    user_content = (
        f"Available Job Roles:\n"
        f"{roles_formatted}\n\n"
        f"Candidate Resume Text:\n"
        f"{resume_text}"
    )
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content}
    ]
    
    fallback_profile = {
        "name": "Unknown Candidate",
        "email": "",
        "phone": "",
        "skills": [],
        "projects": [],
        "education": [],
        "years_of_experience": 0.0,
        "current_location": ""
    }
    fallback_recs = []
    
    try:
        # Force JSON mode
        response_content = llm_client.query_llm(messages, temperature=0.0, json_mode=True, model_name=model_name)
        
        # Clean response if LLM added markdown formatting
        response_content = response_content.strip()
        if response_content.startswith("```json"):
            response_content = response_content[7:]
        if response_content.endswith("```"):
            response_content = response_content[:-3]
        response_content = response_content.strip()
        
        parsed_json = json.loads(response_content)
        profile = parsed_json.get("profile", fallback_profile)
        if "education" in profile:
            post_process_education_years(profile["education"], resume_text)
        recommendations = parsed_json.get("recommendations", fallback_recs)
        
        # Decorate recommendations with description and skills from original job role documents
        decorated_recs = []
        role_map = {r.get("job_role").lower().strip(): r for r in all_roles}
        for rec in recommendations:
            r_name = rec.get("job_role", "")
            db_role = role_map.get(r_name.lower().strip())
            if db_role:
                rec["job_role"] = db_role.get("job_role")
                rec["job_description"] = db_role.get("job_description", "")
                rec["skills"] = db_role.get("skills", [])
                decorated_recs.append(rec)
            else:
                print(f"Skipping LLM recommended role '{r_name}' because it does not exist in the database.")
                
        # Ensure top 5 sorted recommendations
        decorated_recs = sorted(decorated_recs, key=lambda x: x.get("match_score", 0.0), reverse=True)[:5]
        
        return profile, decorated_recs
    except Exception as e:
        print(f"Error in combined LLM parsing/matching: {str(e)}")
        return fallback_profile, fallback_recs

def process_resume_and_match(file_path, file_type, all_roles, model_name=None):
    """
    Extracts text from the file path and queries the LLM for unified parsing & matching.
    Returns (raw_text, parsed_profile, recommendations)
    """
    if file_type.lower() == "pdf":
        raw_text = extract_text_from_pdf(file_path)
    elif file_type.lower() == "txt":
        raw_text = extract_text_from_txt(file_path)
    else:
        raise ValueError(f"Unsupported file type: {file_type}")
        
    profile, recommendations = parse_resume_and_match_jobs_with_llm(raw_text, all_roles, model_name=model_name)
    return raw_text, profile, recommendations

def process_resume_hybrid_rerank(file_path, file_type, all_roles, model_name=None):
    """
    1. Extracts text from the file path.
    2. Generates candidate resume embedding.
    3. Performs vector search against MongoDB job roles to filter top 10 matches.
    4. Queries the LLM to rerank those top 10 matches and return the final top 5 matches,
       along with candidate details.
    Returns (raw_text, resume_embedding, parsed_profile, recommendations)
    """
    import matcher
    
    # 1. Extract raw text
    if file_type.lower() == "pdf":
        raw_text = extract_text_from_pdf(file_path)
    elif file_type.lower() == "txt":
        raw_text = extract_text_from_txt(file_path)
    else:
        raise ValueError(f"Unsupported file type: {file_type}")
        
    # 2. Generate candidate embedding
    model = matcher.load_bert_model()
    resume_embedding = None
    if model is not None:
        try:
            resume_embedding = model.encode(raw_text, show_progress_bar=False).tolist()
        except Exception as e:
            print(f"Error generating candidate resume embedding: {str(e)}")
            
    # 3. Perform vector search to filter top 10
    print("Performing vector similarity filtering on MongoDB job roles...")
    vector_matches = matcher.vector_search_jobs(raw_text, all_roles)
    top_10_results = vector_matches[:10]
    top_10_roles = [r["role_document"] for r in top_10_results]
    print(f"Vector search filtered {len(top_10_roles)} candidate roles.")
    
    # 4. Query the LLM to rerank top 10 into top 5
    profile, recommendations = parse_resume_and_match_jobs_with_llm(raw_text, top_10_roles, model_name=model_name)
    
    # Fill up to 5 recommendations if the LLM output was filtered or returned fewer than 5
    if len(recommendations) < 5 and len(all_roles) > 0:
        recommended_names = {r["job_role"].lower().strip() for r in recommendations}
        
        # Use vector_matches to fill in the remaining slots
        for match in vector_matches:
            if len(recommendations) >= 5:
                break
            role_doc = match["role_document"]
            r_name = role_doc.get("job_role", "")
            if r_name.lower().strip() not in recommended_names:
                recommendations.append({
                    "job_role": r_name,
                    "match_score": match.get("vector_score", 50.0),
                    "reason": "Recommended based on semantic skill compatibility matching.",
                    "job_description": role_doc.get("job_description", ""),
                    "skills": role_doc.get("skills", [])
                })
                recommended_names.add(r_name.lower().strip())
                
        # If still fewer than 5 (e.g. vector search is empty), fill directly from all_roles
        if len(recommendations) < 5:
            for role_doc in all_roles:
                if len(recommendations) >= 5:
                    break
                r_name = role_doc.get("job_role", "")
                if r_name.lower().strip() not in recommended_names:
                    recommendations.append({
                        "job_role": r_name,
                        "match_score": 50.0,
                        "reason": "Alternative role match from job listing.",
                        "job_description": role_doc.get("job_description", ""),
                        "skills": role_doc.get("skills", [])
                    })
                    recommended_names.add(r_name.lower().strip())
                    
    # Sort recommendations by match score descending to keep best matches first
    recommendations = sorted(recommendations, key=lambda x: x.get("match_score", 0.0), reverse=True)[:5]
    
    return raw_text, resume_embedding, profile, recommendations

def process_resume(file_path, file_type, model_name=None):
    """
    Backward-compatible legacy process_resume.
    """
    if file_type.lower() == "pdf":
        raw_text = extract_text_from_pdf(file_path)
    elif file_type.lower() == "txt":
        raw_text = extract_text_from_txt(file_path)
    else:
        raise ValueError(f"Unsupported file type: {file_type}")
        
    parsed_json = parse_resume_text_with_llm(raw_text, model_name=model_name)
    return raw_text, parsed_json
