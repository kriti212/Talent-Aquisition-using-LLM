import json
import os
import pymongo
from bson import ObjectId
import config

class TalentDB:
    def __init__(self, uri=config.MONGO_URI, db_name=config.DB_NAME):
        self.client = pymongo.MongoClient(uri)
        self.db = self.client[db_name]
        self.roles_col = self.db["job_roles"]
        self.candidates_col = self.db["candidates"]
        
    def seed_roles(self, json_path=config.JOB_ROLE_JSON_PATH):
        """Seeds the job roles from job_role.json if the collection is empty, and adds vector embeddings."""
        try:
            import matcher
            
            # Helper to generate embedding text
            def get_role_text(role):
                role_name = role.get("job_role", "")
                desc = role.get("job_description", "")
                skills_list = role.get("skills", [])
                skills_str = ", ".join([s.get("skill_name", "") for s in skills_list])
                return f"Job Role: {role_name}\nDescription: {desc}\nSkills: {skills_str}"
            
            # Case 1: Collection is empty, seed from scratch
            if self.roles_col.count_documents({}) == 0:
                if not os.path.exists(json_path):
                    print(f"Error: Job role definition file not found at {json_path}")
                    return False
                with open(json_path, 'r', encoding='utf-8') as f:
                    roles = json.load(f)
                
                if roles and isinstance(roles, list):
                    # Compute embeddings before inserting
                    model = matcher.load_bert_model()
                    if model is not None:
                        for role in roles:
                            role_text = get_role_text(role)
                            role["embedding"] = model.encode(role_text).tolist()
                    self.roles_col.insert_many(roles)
                    print(f"Successfully seeded {len(roles)} job roles with vector embeddings into the database.")
                    return True
            else:
                # Case 2: Collection is not empty, check if any roles are missing embeddings
                missing_emb_count = self.roles_col.count_documents({"embedding": {"$exists": False}})
                if missing_emb_count > 0:
                    print(f"Found {missing_emb_count} job roles without vector embeddings. Generating them now...")
                    model = matcher.load_bert_model()
                    if model is not None:
                        for role in self.roles_col.find({"embedding": {"$exists": False}}):
                            role_text = get_role_text(role)
                            embedding = model.encode(role_text).tolist()
                            self.roles_col.update_one(
                                {"_id": role["_id"]},
                                {"$set": {"embedding": embedding}}
                            )
                        print(f"Successfully updated all job roles with vector embeddings.")
                else:
                    print("Job roles collection is already seeded with vector embeddings.")
                return True
        except Exception as e:
            print(f"Error during job roles seeding/embedding: {str(e)}")
            return False
            
    def get_all_roles(self):
        """Returns all job roles as a list of dicts."""
        return list(self.roles_col.find({}))
        
    def get_role_by_name(self, role_name):
        """Returns a job role by its name."""
        return self.roles_col.find_one({"job_role": role_name})
        
    def create_candidate(self, parsed_profile, resume_text, resume_embedding=None):
        """
        Creates a new candidate record with parsed details, raw text, and its vector embedding.
        Returns the inserted candidate's ID as a string.
        """
        candidate_doc = {
            "personal_info": {
                "name": parsed_profile.get("name", "Unknown"),
                "email": parsed_profile.get("email", ""),
                "phone": parsed_profile.get("phone", ""),
                "current_location": parsed_profile.get("current_location", "")
            },
            "education": parsed_profile.get("education", []),
            "extracted_skills": parsed_profile.get("skills", []),
            "projects": parsed_profile.get("projects", []),
            "years_of_experience": float(parsed_profile.get("years_of_experience") or 0.0),
            "resume_text": resume_text,
            "resume_embedding": resume_embedding,
            "selected_role": None,
            "interview_status": "PENDING",
            "qas": [],
            "preferences": {},
            "evaluation": {},
            "created_at": None
        }
        
        # Add timestamp safely
        from datetime import datetime
        candidate_doc["created_at"] = datetime.utcnow()
        
        result = self.candidates_col.insert_one(candidate_doc)
        return str(result.inserted_id)
        
    def update_candidate_role(self, candidate_id, role_name):
        """Updates the selected role for the candidate."""
        self.candidates_col.update_one(
            {"_id": ObjectId(candidate_id)},
            {"$set": {"selected_role": role_name, "interview_status": "IN_PROGRESS"}}
        )
        
    def add_interview_qa(self, candidate_id, question, answer=None, audio_b64=None, score=None, feedback=None):
        """Appends a question-answer pair or updates it."""
        qa_entry = {
            "question": question,
            "answer": answer,
            "audio_b64": audio_b64,
            "score": score,
            "feedback": feedback
        }
        self.candidates_col.update_one(
            {"_id": ObjectId(candidate_id)},
            {"$push": {"qas": qa_entry}}
        )
        
    def update_last_qa_answer(self, candidate_id, answer, audio_b64=None):
        """Updates the answer of the most recent QA entry."""
        candidate = self.candidates_col.find_one({"_id": ObjectId(candidate_id)})
        if not candidate or not candidate.get("qas"):
            return
        
        # Update the answer and audio_b64 fields of the last item in the qas array
        qas = candidate["qas"]
        qas[-1]["answer"] = answer
        if audio_b64 is not None:
            qas[-1]["audio_b64"] = audio_b64
        
        self.candidates_col.update_one(
            {"_id": ObjectId(candidate_id)},
            {"$set": {"qas": qas}}
        )
        
    def update_qa_scores(self, candidate_id, qas_with_scores):
        """Updates the entire qas array with scores and feedback."""
        self.candidates_col.update_one(
            {"_id": ObjectId(candidate_id)},
            {"$set": {"qas": qas_with_scores}}
        )

    def save_preferences(self, candidate_id, preferences):
        """Saves candidate's job preferences."""
        self.candidates_col.update_one(
            {"_id": ObjectId(candidate_id)},
            {"$set": {"preferences": preferences}}
        )
        
    def save_evaluation(self, candidate_id, evaluation_report):
        """Saves the final evaluation report and marks interview as COMPLETED."""
        self.candidates_col.update_one(
            {"_id": ObjectId(candidate_id)},
            {"$set": {
                "evaluation": evaluation_report,
                "interview_status": "COMPLETED"
            }}
        )
        
    def get_candidate(self, candidate_id):
        """Retrieves a candidate by ID."""
        return self.candidates_col.find_one({"_id": ObjectId(candidate_id)})

    def update_recruiter_status(self, candidate_id, status, notes=""):
        """Updates the recruiter review status and custom recruiter notes for a candidate."""
        self.candidates_col.update_one(
            {"_id": ObjectId(candidate_id)},
            {"$set": {"recruiter_status": status, "recruiter_notes": notes}}
        )

    def vector_search_roles(self, query_embedding, limit=5):
        """
        Performs MongoDB Atlas Vector Search on the job_roles collection.
        Raises an exception if search is not supported/configured (e.g. running on local MongoDB).
        """
        pipeline = [
            {
                "$vectorSearch": {
                    "index": "vector_index",
                    "path": "embedding",
                    "queryVector": query_embedding,
                    "numCandidates": 100,
                    "limit": limit
                }
            },
            {
                "$project": {
                    "score": {"$meta": "vectorSearchScore"},
                    "job_role": 1,
                    "job_description": 1,
                    "skills": 1,
                    "embedding": 1
                }
            }
        ]
        results = list(self.roles_col.aggregate(pipeline))
        return [
            {
                "job_role": doc.get("job_role", ""),
                "vector_score": round(doc.get("score", 0.0) * 100.0, 2),
                "role_document": doc
            }
            for doc in results
        ]

    def update_last_qa_evaluation(self, candidate_id, tech_score, soft_score, feedback, extra_eval=None):
        """Updates the evaluation scores and feedback for the most recent QA entry."""
        candidate = self.candidates_col.find_one({"_id": ObjectId(candidate_id)})
        if not candidate or not candidate.get("qas"):
            return
        qas = candidate["qas"]
        qas[-1]["technical_score"] = tech_score
        qas[-1]["soft_skills_score"] = soft_score
        qas[-1]["feedback"] = feedback
        if extra_eval is not None:
            qas[-1]["extra_eval"] = extra_eval
        self.candidates_col.update_one(
            {"_id": ObjectId(candidate_id)},
            {"$set": {"qas": qas}}
        )

    def get_candidate_by_email(self, email):
        """Retrieves the most recent candidate document matching the email."""
        return self.candidates_col.find_one(
            {"personal_info.email": email.strip()},
            sort=[("created_at", pymongo.DESCENDING)]
        )

    def update_candidate_parsed_profile(self, candidate_id, personal_info, education, extracted_skills, projects, years_of_experience):
        """Updates the parsed profile fields for the candidate."""
        self.candidates_col.update_one(
            {"_id": ObjectId(candidate_id)},
            {"$set": {
                "personal_info": personal_info,
                "education": education,
                "extracted_skills": extracted_skills,
                "projects": projects,
                "years_of_experience": years_of_experience
            }}
        )

    def save_candidate_feedback(self, candidate_id, email, role, rating, comments):
        """Saves user experience feedback to a separate feedbacks collection."""
        import datetime
        feedback_doc = {
            "candidate_id": ObjectId(candidate_id) if candidate_id else None,
            "email": email,
            "role": role,
            "rating": int(rating),
            "comments": comments.strip(),
            "submitted_at": datetime.datetime.utcnow()
        }
        self.db["feedbacks"].insert_one(feedback_doc)
