import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    print("Error: GEMINI_API_KEY not found in environment.")
    exit(1)

print(f"API Key found: {api_key[:5]}...")

client = OpenAI(
    api_key=api_key,
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
)

try:
    print("Attempting to generate completion with gemini-1.5-flash...")
    response = client.chat.completions.create(
        model="gemini-2.0-flash-exp",
        messages=[
            {"role": "system", "content": "You are a helpful assistant. Return a JSON object."},
            {"role": "user", "content": "Say hello in JSON."}
        ],
        response_format={ "type": "json_object" }
    )
    print("Success!")
    print(response.choices[0].message.content)
except Exception as e:
    print(f"Error: {e}")
