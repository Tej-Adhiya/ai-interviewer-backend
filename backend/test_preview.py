import requests
import asyncio
import os

BASE_URL = "http://localhost:8000/api/v1"

def test_preview_endpoint():
    print("Testing /preview-questions endpoint...")
    
    payload = {
        "resume_text": "Experienced software engineer with python and react skills.",
        "job_description": "We are looking for a senior backend developer."
    }
    
    try:
        response = requests.post(f"{BASE_URL}/preview-questions", json=payload)
        if response.status_code == 200:
            data = response.json()
            questions = data.get("questions", [])
            print("Success! Generated Questions:")
            for i, q in enumerate(questions):
                print(f"{i+1}. {q}")
        else:
            print(f"Failed with status {response.status_code}: {response.text}")
    except Exception as e:
        print(f"Error connecting to backend: {e}")

if __name__ == "__main__":
    test_preview_endpoint()
