import parakeet_mlx
import time
import os

class ParakeetSTT:
    def __init__(self, model_id="mlx-community/parakeet-tdt-0.6b-v3"):
        print(f"Loading model: {model_id}...")
        start_time = time.time()
        self.model = parakeet_mlx.from_pretrained(model_id)
        end_time = time.time()
        print(f"Model loaded in {end_time - start_time:.2f} seconds.")

    def transcribe(self, audio_path):
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        
        print(f"Transcribing {audio_path}...")
        start_time = time.time()
        # The transcribe method might return a string or an object. 
        # Based on inspection, it has a transcribe method.
        # We'll assume it handles file paths.
        result = self.model.transcribe(audio_path)
        end_time = time.time()
        print(f"Transcription completed in {end_time - start_time:.2f} seconds.")
        
        # Check if result is an object with 'text' attribute or just a string
        if hasattr(result, 'text'):
            return result.text
        return result

if __name__ == "__main__":
    # Simple test if run directly
    engine = ParakeetSTT()
    # Assuming test_audio.wav exists in the same dir or passed as arg
    audio_file = "parakeet/test_audio.wav"
    if os.path.exists(audio_file):
        print(f"Result: {engine.transcribe(audio_file)}")
    else:
        print(f"Please provide an audio file to test. Created {audio_file} for testing.")
