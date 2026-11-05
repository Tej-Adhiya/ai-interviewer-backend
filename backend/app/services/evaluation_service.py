from typing import List, Dict, Any
from app.services.llm_service import get_model, get_openai_client
import json
import traceback
import os

EVALUATION_PROMPT = """
You are an expert technical interviewer.
Your goal is to evaluate a candidate's interview performance based on the following 5 criteria:
1.  **Technical Accuracy**: Correctness and depth of technical answers.
2.  **Communication Style**: Clarity, conciseness, and confidence.
3.  **Problem Solving**: Approach to challenges and logical thinking.
4.  **Experience Relevance**: How well their past experience aligns with the job.
5.  **Overall Fit**: General assessment of their suitability for the role.

Input:
- Job Description
- Candidate Resume
- Interview Transcript (List of Question and Answer pairs)

Instructions:
For each question, evaluate how well the candidate's answer directly addresses the specific question asked. Consider the technical accuracy, clarity, and relevance of the answer in the context of the question.

Output:
Return a JSON object with the following structure:
{
  "scores": {
    "technical_accuracy": 0-10,
    "communication_style": 0-10,
    "problem_solving": 0-10,
    "experience_relevance": 0-10,
    "overall_fit": 0-10
  },
  "feedback": {
    "strengths": ["point 1", "point 2"],
    "weaknesses": ["point 1", "point 2"],
    "improvement_points": ["specific advice 1", "specific advice 2"]
  },
  "summary": "A brief paragraph summarizing the candidate's performance."
}
"""

async def evaluate_interview(resume_text: str, job_description: str, qa_list: List[Dict[str, str]]) -> Dict:
    provider = os.getenv("LLM_PROVIDER", "gemini").lower()
    print(f"DEBUG: Evaluating with LLM Provider: {provider}", flush=True)

    if provider == "openai":
        return await evaluate_interview_openai(resume_text, job_description, qa_list)
    else:
        return await evaluate_interview_gemini(resume_text, job_description, qa_list)

async def evaluate_interview_openai(resume_text: str, job_description: str, qa_list: List[Dict[str, str]]) -> Dict:
    client = get_openai_client()
    if not client:
        return {"error": "OpenAI client not available"}

    transcript = _format_transcript(qa_list)

    try:
        print("DEBUG: Calling OpenAI (gpt-4o-mini) for evaluation...", flush=True)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": EVALUATION_PROMPT},
                {"role": "user", "content": f"Job Description:\n{job_description}\n\nResume:\n{resume_text}\n\nTranscript:\n{transcript}"}
            ],
            response_format={"type": "json_object"}
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        print(f"Error evaluating interview (OpenAI): {e}", flush=True)
        traceback.print_exc()
        return {"error": str(e)}

async def evaluate_interview_gemini(resume_text: str, job_description: str, qa_list: List[Dict[str, str]]) -> Dict:
    model = get_model()
    if not model:
        return {"error": "LLM model not available"}

    transcript = _format_transcript(qa_list)

    try:
        print("DEBUG: Calling Google GenAI SDK for evaluation...", flush=True)
        prompt = f"{EVALUATION_PROMPT}\n\nJob Description:\n{job_description}\n\nResume:\n{resume_text}\n\nTranscript:\n{transcript}"
        
        response = model.generate_content(
            prompt,
            generation_config={"response_mime_type": "application/json"}
        )
        
        print("DEBUG: Evaluation response received", flush=True)
        return json.loads(response.text)
    except Exception as e:
        print(f"Error evaluating interview (Gemini): {e}", flush=True)
        traceback.print_exc()
        return {"error": str(e)}

def _format_transcript(qa_list: List[Dict[str, str]]) -> str:
    transcript = ""
    for i, item in enumerate(qa_list, 1):
        transcript += f"Question {i}: {item['question']}\nCandidate Answer: {item['answer']}\n\n"
    return transcript
