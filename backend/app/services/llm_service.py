import os
import sys
import traceback
import google.generativeai as genai
from openai import OpenAI
from typing import List

# Configure API keys globally or lazily
_model = None
_openai_client = None

def get_model():
    global _model
    if not _model:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            print("Warning: GEMINI_API_KEY not found.", flush=True)
            return None
        print(f"DEBUG: Found GEMINI_API_KEY: {api_key[:4]}...", flush=True)
        genai.configure(api_key=api_key)
        _model = genai.GenerativeModel("gemini-2.5-flash")
    return _model

def get_openai_client():
    global _openai_client
    if not _openai_client:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            print("Warning: OPENAI_API_KEY not found.", flush=True)
            return None
        print(f"DEBUG: Found OPENAI_API_KEY: {api_key[:4]}...", flush=True)
        _openai_client = OpenAI(api_key=api_key)
    return _openai_client

SYSTEM_PROMPT = """
You are an expert technical interviewer. 
Your goal is to generate highly personalized and challenging interview questions based on a candidate's resume and a specific job description.

Guidelines:
1.  **Conciseness**: Keep questions concise and direct.
2.  **No Names**: Do NOT mention the candidate's name in the questions.
3.  **No Abbreviations**: Avoid using abbreviations or shortforms to ensure accurate Text-to-Speech pronunciation.
4.  **Question 1 (Introduction)**: Start with a personalized "Tell me about yourself" question.
5.  **Questions 2-3 (Projects)**: Ask 2 specific questions about PROJECTS listed in their resume. Quote the project name if possible and ask about a technical challenge.
6.  **Questions 4-5 (Job Fit)**: Ask 2 questions testing their fit for the specific requirements in the Job Description.
7.  Return ONLY the questions as a list of strings, one per line. Do not number them.
"""

async def generate_interview_questions(resume_text: str, job_description: str) -> List[str]:
    provider = os.getenv("LLM_PROVIDER", "gemini").lower()
    print(f"DEBUG: Using LLM Provider: {provider}", flush=True)
    
    if provider == "openai":
        return await generate_interview_questions_openai(resume_text, job_description)
    else:
        return await generate_interview_questions_gemini(resume_text, job_description)

async def generate_interview_questions_openai(resume_text: str, job_description: str) -> List[str]:
    client = get_openai_client()
    if not client:
        print("DEBUG: OpenAI Client unavailable, falling back to defaults", flush=True)
        return get_default_questions()

    try:
        print("DEBUG: Calling OpenAI API (gpt-4o-mini)...", flush=True)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Candidate Resume:\n{resume_text}\n\nTarget Job Description:\n{job_description}\n\nGenerate 5 personalized interview questions:"}
            ]
        )
        print("DEBUG: OpenAI Response received", flush=True)
        content = response.choices[0].message.content
        questions = [q.strip().lstrip("1234567890. ") for q in content.split("\n") if q.strip()]
        return questions[:5]
    except Exception as e:
        print(f"Error generating questions (OpenAI): {e}", flush=True)
        traceback.print_exc()
        return get_default_questions()

async def generate_interview_questions_gemini(resume_text: str, job_description: str) -> List[str]:
    print("DEBUG: generate_interview_questions called (Native SDK)", flush=True)
    model = get_model()
    if not model:
        print("DEBUG: Model is None, falling back to defaults", flush=True)
        return get_default_questions()

    try:
        print(f"DEBUG: Calling Google GenAI SDK with model {model.model_name}...", flush=True)
        prompt = f"{SYSTEM_PROMPT}\n\nCandidate Resume:\n{resume_text}\n\nTarget Job Description:\n{job_description}\n\nGenerate 5 personalized interview questions:"
        response = model.generate_content(prompt)
        print("DEBUG: API Response received", flush=True)
        content = response.text
        questions = [q.strip().lstrip("1234567890. ") for q in content.split("\n") if q.strip()]
        return questions[:5]
    except Exception as e:
        print(f"Error generating questions (Gemini): {e}", flush=True)
        traceback.print_exc()
        return get_default_questions()

def get_default_questions():
    return [
        "Tell me about yourself, focusing on how your one year of experience led you to work on Generative Artificial Intelligence and automation systems.",
        "In the project 'Land Record Data Extractor', what was the most difficult technical challenge in ensuring accurate structured JSON output from multilingual scanned documents, and how did you solve it?",
        "In the project 'Hebrew Document Retrieval and Question Answering System', how did you handle semantic retrieval quality for non English text, and what trade offs did you face while designing the Retrieval Augmented Generation pipeline?",
        "This role requires strong prompt design for Large Language Models. How do you systematically test, evaluate, and improve prompts to reduce incorrect or irrelevant responses in production systems?",
        "Explain how you would design a Retrieval Augmented Generation system using Python, vector databases, and backend Application Programming Interfaces, and how you would handle edge cases like missing context or ambiguous user queries?"
    ]
