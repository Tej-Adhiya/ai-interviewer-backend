from sqlmodel import SQLModel, create_engine, Session
import os
from dotenv import load_dotenv

load_dotenv()

import urllib.parse

DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL and "postgresql" in DATABASE_URL:
    # Handle special characters in password if present
    try:
        # Check if password has special chars that might break the URL
        if "@" in DATABASE_URL.split("@")[0].split(":")[-1]: 
             # This is a naive check, better to just rely on user providing valid URL or handle it robustly
             pass
    except:
        pass
        
    # If the user provided a raw password with special chars in .env, we might need to fix it here
    # But standard practice is to put the encoded URL in .env
    pass

if not DATABASE_URL:
    # Fallback to sqlite for dev if no postgres url provided, or raise error
    # For now, let's assume the user will provide it, but default to sqlite to avoid crashing immediately if they haven't yet
    sqlite_file_name = "database.db"
    DATABASE_URL = f"sqlite:///{sqlite_file_name}"
    print("WARNING: DATABASE_URL not found in .env, using SQLite fallback.")

engine = create_engine(DATABASE_URL, echo=True)

def get_session():
    with Session(engine) as session:
        yield session

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)
