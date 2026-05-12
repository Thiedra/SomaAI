"""
career/constants.py
Hardcoded career assessment questions shown to all students.
These never change — they are not stored in the database.
"""

CAREER_QUESTIONS = [
    {"id": "q1", "text": "What subjects do you enjoy most?"},
    {"id": "q2", "text": "Do you prefer working with people, data, or things?"},
    {"id": "q3", "text": "What problem in Rwanda/Africa would you like to solve?"},
    {"id": "q4", "text": "Do you prefer indoor or outdoor work?"},
    {"id": "q5", "text": "How do you feel about long years of university study?"},
    {"id": "q6", "text": "Do you prefer creativity or precision in your work?"},
    {"id": "q7", "text": "What are your strongest subjects?"},
    {"id": "q8", "text": "Would you like to work in a city or rural area?"},
]

# all required question IDs — used for validation
REQUIRED_QUESTION_IDS = {q["id"] for q in CAREER_QUESTIONS}
