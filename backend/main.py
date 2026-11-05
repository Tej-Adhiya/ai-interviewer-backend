from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()
from app.routers import interview

from app.services.stt_service import stt_service

app = FastAPI(title="AI Interview Coach API")

@app.on_event("startup")
async def startup_event():
    print("Preloading STT model...")
    stt_service.load_model()
    print("STT model preloaded.")
    
    from app.core.database import create_db_and_tables
    create_db_and_tables()
    print("Database tables created.")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(interview.router, prefix="/api/v1", tags=["interview"])

@app.get("/")
async def root():
    return {"message": "Welcome to AI Interview Coach API"}
