from typing import List, Optional
from sqlmodel import Field, SQLModel, Relationship
from sqlalchemy import Column, Text
from datetime import datetime
import uuid

class InterviewSession(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    candidate_name: Optional[str] = None
    candidate_email: Optional[str] = None
    resume_text: str = Field(sa_column=Column(Text))
    resume_file_path: Optional[str] = None
    job_description: str = Field(sa_column=Column(Text))
    status: str = Field(default="LINK_GENERATED") # LINK_GENERATED, IN_PROGRESS, COMPLETED, PENDING_REVIEW, EXPIRED
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    actual_start_time: Optional[datetime] = None
    actual_end_time: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    log_dir: Optional[str] = None
    evaluation_report: Optional[str] = Field(default=None, sa_column=Column(Text))
    
    questions: List["Question"] = Relationship(back_populates="session")
    answers: List["Answer"] = Relationship(back_populates="session")

class Question(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: str = Field(foreign_key="interviewsession.id")
    text: str
    order_index: int
    audio_path: Optional[str] = None
    
    session: InterviewSession = Relationship(back_populates="questions")
    answer: Optional["Answer"] = Relationship(back_populates="question")

class Answer(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: str = Field(foreign_key="interviewsession.id")
    question_id: int = Field(foreign_key="question.id")
    audio_path: Optional[str] = None
    transcript: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    session: InterviewSession = Relationship(back_populates="answers")
    question: Question = Relationship(back_populates="answer")
