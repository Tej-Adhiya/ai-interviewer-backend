from typing import Dict, List, Any
import uuid

# In-memory store: { session_id: { ... } }
sessions: Dict[str, Dict[str, Any]] = {}

def create_session() -> str:
    session_id = str(uuid.uuid4())
    sessions[session_id] = {
        "resume_text": "",
        "job_description": "",
        "questions": [], # List of {id, text}
        "answers": {}    # { question_id: transcribed_text }
    }
    return session_id

def get_session(session_id: str):
    return sessions.get(session_id)

def update_session(session_id: str, key: str, value: Any):
    if session_id in sessions:
        sessions[session_id][key] = value

def add_answer(session_id: str, question_id: int, answer_text: str):
    if session_id in sessions:
        sessions[session_id]["answers"][question_id] = answer_text
