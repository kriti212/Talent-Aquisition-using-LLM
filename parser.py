import pdfplumber
import json
import re
import llm_client
import instructor
from openai import OpenAI
from pydantic import BaseModel, Field
from typing import List, Optional
import config

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

class EducationEntry(BaseModel):
    degree: str = Field(default="", description="Degree title (e.g., Bachelor of Science in Mathematics)")
    institution: str = Field(default="", description="University or School name")
    year: Optional[int] = Field(default=None, description="Graduation/completion year as an integer")

class CandidateProfile(BaseModel):
    name: str = Field(default="Unknown", description="Full Name of the candidate")
    email: str = Field(default="", description="Email address")
    phone: str = Field(default="", description="Phone number")
    skills: List[str] = Field(default_factory=list, description="List of technical and soft skills extracted from the resume")
    projects: List[str] = Field(default_factory=list, description="List of projects mentioned in the resume")
    education: List[EducationEntry] = Field(default_factory=list, description="List of education details")
    years_of_experience: float = Field(default=0.0, description="Total years of experience as a float")
    current_location: str = Field(default="", description="Current city, state/country")

def parse_resume_text_with_llm(resume_text, model_name=None, current_location=None):
    """
    Sends the extracted resume text to Ollama and requests a structured JSON profile back using instructor and pydantic.
    """
    try:
        # Construct OpenAI compatible endpoint for Ollama
        base_url = config.API_URL.replace("/api/chat", "/v1")
        client = instructor.from_openai(
            OpenAI(
                base_url=base_url,
                api_key="ollama"
            ),
            mode=instructor.Mode.JSON
        )
        
        user_content = f"Resume Text:\n{resume_text}"
        if current_location:
            user_content = f"Candidate Current Location (via Geolocation/IP): {current_location}\n\n" + user_content
            
        profile = client.chat.completions.create(
            model=model_name or config.LLM_MODEL,
            response_model=CandidateProfile,
            messages=[
                {
                    "role": "system", 
                    "content": (
                        "You are an expert resume parsing assistant. Analyze the provided resume text and extract "
                        "the key details in a structured format conforming to the schema. "
                        "If a 'current_location' is provided via Geolocation context, use it to fill the candidate's current_location. "
                        "For the 'education' year field, extract ONLY the completion/graduation year as an integer. "
                        "If a range is given, use the final year of that range."
                    )
                },
                {"role": "user", "content": user_content}
            ],
            temperature=0.0
        )
        
        # Convert Pydantic model to dictionary
        if hasattr(profile, "model_dump"):
            parsed_json = profile.model_dump()
        else:
            parsed_json = profile.dict()
            
        if "education" in parsed_json:
            post_process_education_years(parsed_json["education"], resume_text)
            
        return parsed_json
    except Exception as e:
        print(f"Error parsing resume with instructor/pydantic: {str(e)}")
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

def process_resume_hybrid_rerank(file_path, file_type, all_roles, model_name=None, current_location=None):
    """
    1. Extracts text from the file path.
    2. Generates candidate resume embedding.
    3. Parses the resume features using instructor and pydantic.
    4. Performs MongoDB Atlas Vector Search to retrieve the top 5 matching job roles.
    Returns (raw_text, resume_embedding, parsed_profile, recommendations)
    """
    import matcher
    from database import TalentDB
    
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
            
    # 3. Extract profile details using instructor and pydantic
    print("Extracting candidate profile features using instructor and pydantic...")
    parsed_profile = parse_resume_text_with_llm(raw_text, model_name=model_name, current_location=current_location)
    
    # 4. Perform MongoDB Atlas Vector Search
    recommendations = []
    vector_matches = []
    if resume_embedding is not None:
        try:
            print("Querying MongoDB Atlas Vector Search for job matches...")
            db = TalentDB()
            # Call vector search roles
            vector_matches = db.vector_search_roles(resume_embedding, limit=5)
            print(f"MongoDB Atlas Vector Search returned {len(vector_matches)} matches.")
        except Exception as e:
            print(f"MongoDB Atlas Vector Search failed/not configured: {str(e)}. Falling back to local search.")
            vector_matches = []
            
    # Fallback to local BERT/overlap search if Atlas search returned nothing or failed
    if not vector_matches:
        print("Using local semantic similarity search fallback...")
        local_matches = matcher.vector_search_jobs(raw_text, all_roles)
        # Convert local matches format
        vector_matches = local_matches[:5]
        
    # Format matches into the standard recommendation schema
    for match in vector_matches:
        role_doc = match.get("role_document", {})
        recommendations.append({
            "job_role": match.get("job_role", role_doc.get("job_role", "")),
            "match_score": match.get("vector_score", 50.0),
            "reason": f"Semantic compatibility match of {match.get('vector_score', 50.0)}% computed via vector search.",
            "job_description": role_doc.get("job_description", ""),
            "skills": role_doc.get("skills", [])
        })
        
    # Sort recommendations by match score descending to keep best matches first
    recommendations = sorted(recommendations, key=lambda x: x.get("match_score", 0.0), reverse=True)[:5]
    
    return raw_text, resume_embedding, parsed_profile, recommendations

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
