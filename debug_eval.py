import sys
import os

# Add root folder to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from interview import evaluate_candidate

# Mock interview QA history
qas = [
    {
        "question": "Can you describe a challenging project where you utilized Python?",
        "answer": "I built a web scraper that processes thousands of pages per minute using asyncio and Celery. I faced rate limiting issues but resolved them using proxies and dynamic delays."
    }
]

print("Running test LLM evaluation...")
try:
    res = evaluate_candidate("Test Candidate", "Python Developer", qas)
    print("\nResult:")
    print(res)
except Exception as e:
    print(f"\nCaught direct exception: {e}")
