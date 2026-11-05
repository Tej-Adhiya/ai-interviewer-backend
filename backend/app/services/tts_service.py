import os
from app.services.kokoro_tts import kokoro_tts

# Initialize client lazily (ElevenLabs deprecated but kept for reference if needed)
_client = None

def get_client():
    global _client
    if not _client:
        api_key = os.getenv("ELEVENLABS_API_KEY")
        if not api_key:
            print("Warning: ELEVENLABS_API_KEY not found.")
            return None
        _client = ElevenLabs(api_key=api_key)
    return _client

async def generate_speech(text: str, output_dir: str) -> str:
    """
    Generates speech using local Kokoro TTS.
    Returns the path to the generated audio file.
    """
    try:
        # Generate audio file
        file_path = kokoro_tts.generate_audio(text, output_dir)
        return file_path
    except Exception as e:
        print(f"Error generating speech: {e}")
        return None
