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
        """Seeds the job roles from job_role.json if the collection is empty."""
        try:
            if self.roles_col.count_documents({}) == 0:
                if not os.path.exists(json_path):
                    print(f"Error: Job role definition file not found at {json_path}")
                    return False
                with open(json_path, 'r', encoding='utf-8') as f:
                    roles = json.load(f)
                
                # Make sure the roles structure is valid
                if roles and isinstance(roles, list):
                    self.roles_col.insert_many(roles)
                    print(f"Successfully seeded {len(roles)} job roles into the database.")
                    return True
            else:
                print("Job roles collection is already seeded.")
                return True
        except Exception as e:
            print(f"Error during job roles seeding: {str(e)}")
            return False
            
    def get_all_roles(self):
        """Returns all job roles as a list of dicts."""
        return list(self.roles_col.find({}))
        
    def get_role_by_name(self, role_name):
        """Returns a job role by its name."""
        return self.roles_col.find_one({"job_role": role_name})
        
    def create_candidate(self, parsed_profile, resume_text):
        """
        Creates a new candidate record with parsed details and raw text.
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
        
    def add_interview_qa(self, candidate_id, question, answer=None, score=None, feedback=None):
        """Appends a question-answer pair or updates it."""
        qa_entry = {
            "question": question,
            "answer": answer,
            "score": score,
            "feedback": feedback
        }
        self.candidates_col.update_one(
            {"_id": ObjectId(candidate_id)},
            {"$push": {"qas": qa_entry}}
        )
        
    def update_last_qa_answer(self, candidate_id, answer):
        """Updates the answer of the most recent QA entry."""
        candidate = self.candidates_col.find_one({"_id": ObjectId(candidate_id)})
        if not candidate or not candidate.get("qas"):
            return
        
        # Update the answer field of the last item in the qas array
        qas = candidate["qas"]
        qas[-1]["answer"] = answer
        
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
