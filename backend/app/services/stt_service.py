import os
import time

class STTService:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(STTService, cls).__new__(cls)
            cls._instance.model = None
        return cls._instance

    def load_model(self, model_id="mlx-community/parakeet-tdt-0.6b-v3"):
        if not self.model:
            print(f"Loading STT model: {model_id}...")
            # Lazy import
            import parakeet_mlx
            start_time = time.time()
            self.model = parakeet_mlx.from_pretrained(model_id)
            end_time = time.time()
            print(f"STT Model loaded in {end_time - start_time:.2f} seconds.")

    def transcribe(self, audio_path: str) -> str:
        if not self.model:
            self.load_model()
        
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
            
        print(f"Transcribing {audio_path}...")
        start_time = time.time()
        result = self.model.transcribe(audio_path)
        end_time = time.time()
        print(f"Transcription completed in {end_time - start_time:.2f} seconds.")
        
        if hasattr(result, 'text'):
            return result.text
        return str(result)

# Global instance
stt_service = STTService()
