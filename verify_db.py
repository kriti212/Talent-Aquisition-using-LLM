import pymongo
from bson import ObjectId
import json
import config

def verify_latest_candidate():
    client = pymongo.MongoClient(config.MONGO_URI)
    db = client[config.DB_NAME]
    candidates_col = db["candidates"]
    
    # Fetch the most recently created candidate
    latest_candidate = candidates_col.find_one(sort=[("created_at", pymongo.DESCENDING)])
    
    if not latest_candidate:
        print("\n=== VERIFICATION RESULT ===")
        print("No candidates found in MongoDB. Please complete an interview run first!")
        print("===========================")
        return
        
    print("\n==================================================")
    print("      LATEST CANDIDATE DATABASE RECORD            ")
    print("==================================================")
    
    # 1. Personal Info
    personal = latest_candidate.get("personal_info", {})
    print(f"Candidate Name : {personal.get('name', 'N/A')}")
    print(f"Candidate Email: {personal.get('email', 'N/A')}")
    print(f"Selected Role  : {latest_candidate.get('selected_role', 'None Selected Yet')}")
    print(f"Status         : {latest_candidate.get('interview_status', 'N/A')}")
    print("-" * 50)
    
    # 2. QAs & Audio base64 Check
    qas = latest_candidate.get("qas", [])
    print(f"Questions Asked: {len(qas)}")
    for idx, qa in enumerate(qas):
        q_text = qa.get("question", "")[:60] + "..." if len(qa.get("question", "")) > 60 else qa.get("question", "")
        a_text = qa.get("answer", "")[:60] + "..." if len(qa.get("answer", "")) > 60 else qa.get("answer", "")
        
        has_audio = "audio_b64" in qa and qa["audio_b64"] is not None
        audio_len = len(qa["audio_b64"]) if has_audio else 0
        
        print(f"\n  [Question {idx+1}] {q_text}")
        print(f"  [Answer   {idx+1}] {a_text or 'None'}")
        print(f"  [Audio Saved] {'Yes 💚 (Length: ' + str(audio_len) + ' chars)' if has_audio else 'No ❌'}")
    print("-" * 50)
    
    # 3. Evaluation Check
    eval_report = latest_candidate.get("evaluation", {})
    has_eval = bool(eval_report)
    print(f"Evaluation Saved: {'Yes 💚' if has_eval else 'No ❌'}")
    if has_eval:
        print(f"  - Technical Score : {eval_report.get('technical_score', 0)}%")
        print(f"  - Soft Skill Score: {eval_report.get('soft_skills_score', 0)}%")
        print(f"  - Final Rating    : {eval_report.get('final_score', 0)}%")
        print(f"  - Recommendation  : {eval_report.get('recommendation', 'N/A')}")
        
        detailed = eval_report.get("detailed_feedback", [])
        if detailed:
            print("\n  Detailed Question Scoring:")
            for idx, q_feed in enumerate(detailed):
                print(f"    [Q{idx+1}] Tech: {q_feed.get('technical_score', 0)} | Soft: {q_feed.get('soft_skills_score', 0)}")
    print("==================================================")

if __name__ == "__main__":
    verify_latest_candidate()
