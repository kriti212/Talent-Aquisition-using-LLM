import numpy as np
import config

# Global variable to cache the BERT model
_bert_model = None
_using_fallback = False

def load_bert_model():
    """
    Loads the sentence-transformers BERT model.
    Falls back gracefully if the package is not installed.
    """
    global _bert_model, _using_fallback
    if _bert_model is not None:
        return _bert_model
        
    try:
        from sentence_transformers import SentenceTransformer
        # Use a very lightweight, fast-loading sentence-BERT model
        _bert_model = SentenceTransformer('all-MiniLM-L6-v2')
        print("Successfully loaded BERT (SentenceTransformer) model.")
        _using_fallback = False
    except ImportError:
        print("sentence-transformers package not installed. Falling back to TF-IDF / Token Overlap matching.")
        _using_fallback = True
    except Exception as e:
        print(f"Error loading BERT model: {str(e)}. Falling back.")
        _using_fallback = True
        
    return _bert_model

def get_cosine_similarity(vec1, vec2):
    """Computes cosine similarity between two 1D numpy arrays."""
    dot_product = np.dot(vec1, vec2)
    norm_a = np.linalg.norm(vec1)
    norm_b = np.linalg.norm(vec2)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(dot_product / (norm_a * norm_b))

def match_skills_jaccard_fallback(candidate_skills, job_skills):
    """
    Fallback Jaccard/Overlap matcher if no ML packages are installed.
    Computes weighted score based on exact/substring matches.
    """
    if not candidate_skills or not job_skills:
        return 0.0
        
    total_weight = 0.0
    matched_weight = 0.0
    
    # Normalize candidate skills for comparison
    cand_skills_lower = [c.lower().strip() for c in candidate_skills]
    
    for r_skill in job_skills:
        skill_name = r_skill.get("skill_name", "")
        weight = r_skill.get("weight", 50.0) # default weight
        total_weight += weight
        
        skill_name_lower = skill_name.lower().strip()
        
        # Check if the skill matches any candidate skill (exact or substring)
        best_match_score = 0.0
        for cand in cand_skills_lower:
            if cand == skill_name_lower:
                best_match_score = 1.0
                break
            elif cand in skill_name_lower or skill_name_lower in cand:
                # Substring overlap heuristic
                best_match_score = max(best_match_score, 0.5)
                
        matched_weight += (best_match_score * weight)
        
    if total_weight == 0:
        return 0.0
    return (matched_weight / total_weight) * 100.0

def match_skills_bert(candidate_skills, job_skills):
    """
    BERT-based semantic matcher.
    Computes cosine similarity between candidate skills and job skills,
    then combines them using job skill weights.
    """
    model = load_bert_model()
    if model is None or _using_fallback:
        # Fall back to token overlap if BERT failed to load
        return match_skills_jaccard_fallback(candidate_skills, job_skills)
        
    if not candidate_skills or not job_skills:
        return 0.0
        
    try:
        # Extract skills and weights
        req_skills = [js.get("skill_name", "") for js in job_skills]
        weights = [js.get("weight", 50.0) for js in job_skills]
        
        # Encode skills
        # Candidate skills
        cand_embeddings = model.encode(candidate_skills, show_progress_bar=False)
        # Required job skills
        req_embeddings = model.encode(req_skills, show_progress_bar=False)
        
        total_weight = sum(weights)
        weighted_score = 0.0
        
        # Calculate best semantic match for each required skill
        for i, req_emb in enumerate(req_embeddings):
            # Compute cosine similarity with all candidate skills
            similarities = []
            for cand_emb in cand_embeddings:
                sim = get_cosine_similarity(req_emb, cand_emb)
                similarities.append(sim)
            
            # Find the best matching candidate skill
            best_sim = max(similarities) if similarities else 0.0
            
            # Clip negative similarities to 0
            best_sim = max(0.0, best_sim)
            
            # Apply weight
            weighted_score += (best_sim * weights[i])
            
        if total_weight == 0:
            return 0.0
            
        # Convert to percentage (0 to 100)
        final_score = (weighted_score / total_weight) * 100.0
        return round(final_score, 2)
        
    except Exception as e:
        print(f"Error in BERT matching: {str(e)}. Falling back.")
        return match_skills_jaccard_fallback(candidate_skills, job_skills)

def recommend_roles(candidate_skills, all_roles):
    """
    Computes matching scores for all roles and returns the top 5.
    """
    scored_roles = []
    
    for role in all_roles:
        role_name = role.get("job_role", "")
        job_skills = role.get("skills", [])
        description = role.get("job_description", "")
        
        # Match using our BERT-based algorithm
        match_score = match_skills_bert(candidate_skills, job_skills)
        
        scored_roles.append({
            "job_role": role_name,
            "match_score": match_score,
            "skills": job_skills,
            "job_description": description
        })
        
    # Sort roles by match score descending
    scored_roles.sort(key=lambda x: x["match_score"], reverse=True)
    
    # Return top 5
    return scored_roles[:5]

def vector_search_jobs(resume_text, all_roles):
    """
    Performs a local vector similarity search.
    Generates embedding for candidate's resume text,
    compares it to the pre-computed 'embedding' stored in MongoDB for each job role,
    and returns all roles sorted by similarity descending.
    """
    model = load_bert_model()
    if model is None or _using_fallback:
        import re
        print("BERT model is not loaded. Performing token-overlap fallback search.")
        try:
            scored_roles = []
            resume_words = set(re.findall(r'\b\w+\b', resume_text.lower()))
            for role in all_roles:
                role_text = f"{role.get('job_role', '')} {role.get('job_description', '')}"
                role_words = set(re.findall(r'\b\w+\b', role_text.lower()))
                overlap = len(resume_words.intersection(role_words))
                score = (overlap / max(1, len(role_words))) * 100.0
                scored_roles.append({
                    "job_role": role.get("job_role", ""),
                    "vector_score": round(score, 2),
                    "role_document": role
                })
            scored_roles.sort(key=lambda x: x["vector_score"], reverse=True)
            return scored_roles
        except Exception as e:
            print(f"Error during Jaccard fallback search: {str(e)}")
            return []
        
    try:
        # Generate candidate embedding
        cand_embedding = model.encode(resume_text, show_progress_bar=False)
        
        scored_roles = []
        for role in all_roles:
            role_emb = role.get("embedding")
            if role_emb:
                # Calculate cosine similarity
                similarity = get_cosine_similarity(cand_embedding, np.array(role_emb))
                similarity = max(0.0, similarity)
            else:
                similarity = 0.0
                
            scored_roles.append({
                "job_role": role.get("job_role", ""),
                "vector_score": round(similarity * 100.0, 2),
                "role_document": role
            })
            
        # Sort by similarity score descending
        scored_roles.sort(key=lambda x: x["vector_score"], reverse=True)
        return scored_roles
    except Exception as e:
        print(f"Error during local vector search: {str(e)}")
        return []

def compute_resume_embedding(resume_text, model=None):
    """Generates BERT vector embedding list for a given resume text."""
    model_inst = model or load_bert_model()
    if model_inst is not None and not _using_fallback:
        try:
            return model_inst.encode(resume_text, show_progress_bar=False).tolist()
        except Exception as e:
            print(f"Error computing resume embedding: {e}")
    return []

def rank_roles(resume_emb, all_roles):
    """Ranks all roles based on cosine similarity with resume embedding."""
    if not resume_emb:
        # Fallback if no embedding
        return [{"job_role": r.get("job_role", ""), "vector_score": 0.0, "role_document": r} for r in all_roles]
        
    scored_roles = []
    for role in all_roles:
        role_emb = role.get("embedding")
        if role_emb:
            similarity = get_cosine_similarity(np.array(resume_emb), np.array(role_emb))
            similarity = max(0.0, similarity)
        else:
            similarity = 0.0
            
        scored_roles.append({
            "job_role": role.get("job_role", ""),
            "vector_score": round(similarity * 100.0, 2),
            "role_document": role
        })
        
    scored_roles.sort(key=lambda x: x["vector_score"], reverse=True)
    return scored_roles

