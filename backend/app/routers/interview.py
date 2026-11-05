from fastapi import APIRouter, UploadFile, File, HTTPException, Form, BackgroundTasks, Depends
from datetime import datetime, timedelta
import asyncio
from pydantic import BaseModel
from typing import List, Optional
from app.services.resume_parser import parse_resume
from sqlmodel import Session, select
from app.core.database import get_session
from app.models.models import InterviewSession, Question as DBQuestion, Answer as DBAnswer

router = APIRouter()

from app.services.llm_service import generate_interview_questions
from app.services.tts_service import generate_speech
from app.services.stt_service import stt_service
from app.services.evaluation_service import evaluate_interview
import base64
import shutil
import os
import uuid
import json
from datetime import datetime

# Define logs directory
LOGS_DIR = os.path.abspath(os.path.join(os.getcwd(), "..", "logs"))
if not os.path.exists(LOGS_DIR):
    os.makedirs(LOGS_DIR)
print(f"Logging to: {LOGS_DIR}")

class JobDescription(BaseModel):
    resume_text: str
    job_description: str
    candidate_name: Optional[str] = None
    candidate_email: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    resume_file_path: Optional[str] = None
    custom_questions: Optional[List[str]] = None

class QuestionResponse(BaseModel):
    id: int
    text: str

class AudioRequest(BaseModel):
    text: str

@router.post("/upload-resume")
async def upload_resume(file: UploadFile = File(...)):
    # Ensure resumes directory exists
    resumes_dir = os.path.join(LOGS_DIR, "resumes")
    if not os.path.exists(resumes_dir):
        os.makedirs(resumes_dir)
    
    # Save file
    file_path = os.path.join(resumes_dir, f"{uuid.uuid4()}_{file.filename}")
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # Re-opening for parsing (assuming parse_resume handles file-like objects)
    # We need to mock UploadFile behavior if parse_resume relies on .filename etc.
    # Let's just use the original file object if possible, but we need to seek(0).
    await file.seek(0) 
    text = await parse_resume(file)
    
    return {
        "filename": file.filename, 
        "extracted_text_preview": text[:200] + "...", 
        "extracted_text": text,
        "file_path": file_path
    }

from fastapi.responses import FileResponse

@router.get("/audio/{session_id}/{filename:path}")
async def get_audio_file(session_id: str, filename: str, db: Session = Depends(get_session)):
    # Security check: ensure session exists
    session = db.get(InterviewSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
        
    # Construct path
    log_dir = session.log_dir
    file_path = os.path.join(log_dir, filename)
    
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
        
    return FileResponse(file_path)

class PreviewRequest(BaseModel):
    resume_text: str
    job_description: str

@router.post("/preview-questions")
async def preview_questions(data: PreviewRequest):
    questions_text = await generate_interview_questions(data.resume_text, data.job_description)
    return {"questions": questions_text}

@router.post("/generate-questions")
async def generate_questions(data: JobDescription, db: Session = Depends(get_session)):
    # Create timestamped log directory for this session
    timestamp = datetime.now().strftime("log_%Y-%m-%d_%H-%M-%S")
    session_log_dir = os.path.join(LOGS_DIR, timestamp)
    if not os.path.exists(session_log_dir):
        os.makedirs(session_log_dir)
    print(f"Session logging to: {session_log_dir}")
    
    # Create questions audio directory
    questions_audio_dir = os.path.join(session_log_dir, "questions")
    if not os.path.exists(questions_audio_dir):
        os.makedirs(questions_audio_dir)

    # Move resume to session log dir
    final_resume_path = data.resume_file_path
    if data.resume_file_path and os.path.exists(data.resume_file_path):
        resume_filename = os.path.basename(data.resume_file_path)
        new_resume_path = os.path.join(session_log_dir, resume_filename)
        shutil.move(data.resume_file_path, new_resume_path)
        final_resume_path = new_resume_path

    # Create DB Session
    session = InterviewSession(
        candidate_name=data.candidate_name,
        candidate_email=data.candidate_email,
        resume_text=data.resume_text,
        resume_file_path=final_resume_path,
        job_description=data.job_description,
        start_time=data.start_time,
        end_time=data.end_time,
        log_dir=session_log_dir,
        status="LINK_GENERATED"
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    if data.custom_questions and len(data.custom_questions) > 0:
        print(f"Using {len(data.custom_questions)} custom questions.")
        questions_text = data.custom_questions
    else:
        print("Generating questions using LLM...")
        questions_text = await generate_interview_questions(data.resume_text, data.job_description)
    
    questions_list = []
    for i, q_text in enumerate(questions_text):
        # Generate Audio
        audio_path = await generate_speech(q_text, questions_audio_dir)
        
        db_question = DBQuestion(
            session_id=session.id,
            text=q_text,
            order_index=i,
            audio_path=audio_path
        )
        db.add(db_question)
        db.commit()
        db.refresh(db_question)
        
        audio_filename = os.path.basename(audio_path) if audio_path else None
        audio_url = f"/api/v1/audio/{session.id}/questions/{audio_filename}" if audio_filename else None
        
        questions_list.append({
            "id": db_question.id,
            "text": q_text,
            "audio_url": audio_url
        })
    
    return {"session_id": session.id, "questions": questions_list}

@router.post("/generate-audio")
async def generate_question_audio(data: AudioRequest):
    # Deprecated or used for testing
    return {"message": "Deprecated. Audio is pre-generated."}

@router.post("/submit-answer")
async def submit_answer(
    session_id: str = Form(...),
    question_id: int = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_session)
):
    # Get session to find log dir
    session = db.get(InterviewSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
        
    log_dir = session.log_dir
    
    # Save audio file
    filename = f"session_{session_id}_q_{question_id}.wav"
    file_path = os.path.join(log_dir, filename)
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # Create or Update Answer record
    statement = select(DBAnswer).where(
        DBAnswer.session_id == session_id,
        DBAnswer.question_id == question_id
    )
    results = db.exec(statement)
    existing_answer = results.first()
    
    if existing_answer:
        existing_answer.audio_path = file_path
        existing_answer.transcript = "__PENDING__" # Mark for batch processing
        db.add(existing_answer)
    else:
        new_answer = DBAnswer(
            session_id=session_id,
            question_id=question_id,
            audio_path=file_path,
            transcript="__PENDING__"
        )
        db.add(new_answer)
    
    db.commit()
    
    return {"message": "Answer received and saved."}

def process_video(raw_file_path: str, final_file_path: str):
    """
    Process video with ffmpeg: Scale to 480p height (auto width) and Mirror (hflip).
    """
    import subprocess
    
    try:
        command = [
            "ffmpeg",
            "-y", # Overwrite output
            "-i", raw_file_path,
            "-vf", "scale=-2:480,hflip",
            "-c:v", "libvpx-vp9",
            "-deadline", "realtime",
            "-cpu-used", "4",
            "-row-mt", "1",
            final_file_path
        ]
        
        print(f"Running ffmpeg: {' '.join(command)}")
        subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        print(f"Processed video saved to {final_file_path}")
        
        # Remove raw file
        if os.path.exists(raw_file_path):
            os.remove(raw_file_path)
            
    except subprocess.CalledProcessError as e:
        print(f"Error processing video: {e}")
        # Fallback: if ffmpeg fails, just rename raw to final
        if os.path.exists(raw_file_path):
            if os.path.exists(final_file_path):
                os.remove(final_file_path)
            os.rename(raw_file_path, final_file_path)
            print("Fallback: Saved raw video due to processing error.")

@router.post("/submit-video")
async def submit_video(
    session_id: str = Form(...),
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_session)
):
    session = db.get(InterviewSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
        
    log_dir = session.log_dir
    
    # Define filenames
    raw_filename = f"temp_raw_{session_id}_video.webm"
    final_filename = f"session_{session_id}_video.webm"
    
    raw_file_path = os.path.join(log_dir, raw_filename)
    final_file_path = os.path.join(log_dir, final_filename)
    
    # Save raw video file temporarily
    with open(raw_file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    print(f"Raw video saved to {raw_file_path}")
    
    # Offload processing to background task
    background_tasks.add_task(process_video, raw_file_path, final_file_path)
            
    return {"message": "Video received and saved. Processing in background."}

@router.post("/evaluate")
async def evaluate_session(
    session_id: str = Form(...), 
    force_stt: bool = Form(False),
    db: Session = Depends(get_session)
):
    session = db.get(InterviewSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Batch Process STT
    print(f"Starting batch STT for session {session_id}...")
    
    # Get all answers
    statement = select(DBAnswer).where(DBAnswer.session_id == session_id)
    answers = db.exec(statement).all()
    
    for ans in answers:
        if force_stt or ans.transcript == "__PENDING__" or ans.transcript == "__PROCESSING__" or not ans.transcript:
            if ans.audio_path and os.path.exists(ans.audio_path):
                try:
                    transcript = stt_service.transcribe(ans.audio_path)
                    ans.transcript = transcript
                    db.add(ans)
                    db.commit() # Commit each to save progress
                except Exception as e:
                    print(f"Error transcribing answer {ans.id}: {e}")
                    ans.transcript = "Error in transcription."
                    db.add(ans)
                    db.commit()
            else:
                ans.transcript = "No audio file found."
                db.add(ans)
                db.commit()
                
    print("Batch STT completed.")
        
    # Prepare QA pairs
    # Prepare QA pairs
    qa_list = []
    
    # Re-fetch to be sure
    db.refresh(session)
    # Sort questions by order_index to ensure correct order
    sorted_questions = sorted(session.questions, key=lambda q: q.order_index)
    answer_map = {a.question_id: a for a in session.answers}
    
    for q in sorted_questions:
        ans = answer_map.get(q.id)
        ans_text = ans.transcript if ans and ans.transcript else "No answer provided."
        qa_list.append({"question": q.text, "answer": ans_text})
        
    result = await evaluate_interview(
        session.resume_text,
        session.job_description,
        qa_list
    )
    
    # Save full session log
    session_log = {
        "session_id": session_id,
        "resume_text": session.resume_text,
        "job_description": session.job_description,
        "questions": [{"id": q.id, "text": q.text} for q in sorted_questions],
        "answers": [{"question_id": a.question_id, "transcript": a.transcript} for a in session.answers],
        "evaluation": result
    }
    
    log_dir = session.log_dir or LOGS_DIR
    log_file = f"{log_dir}/session_{session_id}_report.json"
    with open(log_file, "w") as f:
        json.dump(session_log, f, indent=2)
    print(f"Saved session report: {log_file}")
    
    # Update session status and save report
    session.status = "COMPLETED"
    session.evaluation_report = json.dumps(result)
    db.add(session)
    db.commit()
    
    return result

@router.get("/interviews/{session_id}")
async def get_interview_session(session_id: str, db: Session = Depends(get_session)):
    session = db.get(InterviewSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    questions = []
    sorted_questions = sorted(session.questions, key=lambda q: q.order_index)
    
    for q in sorted_questions:
        audio_url = None
        if q.audio_path:
            # Assuming audio_path is absolute, we need to extract relative part for the URL
            # The URL structure we defined is /api/v1/audio/{session_id}/questions/{filename}
            # But wait, generate_questions saved it in session_log_dir/questions/filename
            # So filename is enough if we handle the path in get_audio_file
            filename = os.path.basename(q.audio_path)
            audio_url = f"/api/v1/audio/{session.id}/questions/{filename}"

        questions.append({
            "id": q.id,
            "text": q.text,
            "audio_url": audio_url
        })
        
    # Determine flow status
    flow_status = session.status
    
    if session.status == "FAILED":
        flow_status = "FAILED"
    elif session.actual_end_time:
        flow_status = "COMPLETED"
    elif session.status == "LINK_GENERATED":
        if session.start_time and session.end_time:
            now = datetime.now(session.start_time.tzinfo) if session.start_time.tzinfo else datetime.now()
            if now < session.start_time:
                flow_status = "UPCOMING"
            elif now > session.end_time:
                flow_status = "EXPIRED"
            else:
                flow_status = "READY"
        else:
            flow_status = "READY"

    return {
        "session_id": session.id,
        "candidate_name": session.candidate_name,
        "status": session.status, 
        "flow_status": flow_status,
        "start_time": session.start_time,
        "end_time": session.end_time,
        "questions": questions
    }


@router.post("/interviews/{session_id}/start")
async def start_session(session_id: str, db: Session = Depends(get_session)):
    session = db.get(InterviewSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session.status = "IN_PROGRESS"
    session.actual_start_time = datetime.now()
    db.add(session)
    db.commit()
    return {"status": "success"}

class RescheduleRequest(BaseModel):
    start_time: datetime
    end_time: datetime

@router.post("/interviews/{session_id}/reschedule")
async def reschedule_session(session_id: str, data: RescheduleRequest, db: Session = Depends(get_session)):
    session = db.get(InterviewSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session.start_time = data.start_time
    session.end_time = data.end_time
    
    # Always reset to LINK_GENERATED and clear actual times to allow re-taking
    session.status = "LINK_GENERATED"
    session.actual_start_time = None
    session.actual_end_time = None
    
    db.add(session)
    db.commit()
    return {"status": "success"}

@router.get("/interviews")
async def list_interviews(db: Session = Depends(get_session)):
    statement = select(InterviewSession).order_by(InterviewSession.created_at.desc())
    sessions = db.exec(statement).all()
    
    # Check for expired sessions that were not attempted
    updated = False
    for session in sessions:
        if session.status in ["LINK_GENERATED", "IN_PROGRESS"] and not session.actual_end_time:
            if session.end_time:
                now = datetime.now(session.end_time.tzinfo) if session.end_time.tzinfo else datetime.now()
                if now > session.end_time + timedelta(minutes=15):
                    session.status = "NOT_ATTEMPTED"
                    db.add(session)
                    updated = True
    
    if updated:
        db.commit()
        # Re-fetch to get updated statuses
        sessions = db.exec(statement).all()
        
    return sessions

@router.post("/complete")
async def complete_session(session_id: str = Form(...), db: Session = Depends(get_session)):
    session = db.get(InterviewSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session.status = "PENDING_REVIEW"
    session.actual_end_time = datetime.now()
    db.add(session)
    db.commit()
    
    return {"message": "Session marked as pending review"}

@router.get("/interviews/{session_id}/report")
async def get_session_report(session_id: str, db: Session = Depends(get_session)):
    session = db.get(InterviewSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if not session.evaluation_report:
        raise HTTPException(status_code=404, detail="Report not found for this session")
        
    return json.loads(session.evaluation_report)

@router.get("/interviews/{session_id}/download")
async def download_session_logs(session_id: str, db: Session = Depends(get_session)):
    session = db.get(InterviewSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    log_dir = session.log_dir
    if not log_dir or not os.path.exists(log_dir):
        raise HTTPException(status_code=404, detail="Log directory not found")
        
    # Create zip archive
    # We'll create it in the parent directory (logs root) temporarily
    zip_filename = f"session_{session_id}_logs"
    zip_path = shutil.make_archive(os.path.join(LOGS_DIR, zip_filename), 'zip', log_dir)
    
    return FileResponse(zip_path, filename=f"{zip_filename}.zip", media_type="application/zip")

@router.post("/interviews/{session_id}/fail")
async def fail_session(session_id: str, db: Session = Depends(get_session)):
    session = db.get(InterviewSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session.status = "FAILED"
    session.actual_end_time = datetime.now()
    db.add(session)
    db.commit()
    
    return {"status": "success", "message": "Session marked as failed"}
