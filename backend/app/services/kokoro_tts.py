import os
import torch
from kokoro import KPipeline
import soundfile as sf
import uuid

class KokoroTTS:
    def __init__(self):
        self.pipeline = KPipeline(lang_code='a') # 'a' for American English
        self.voice = 'af_heart' # Default voice
        self.sample_rate = 24000

    def generate_audio(self, text: str, output_dir: str) -> str:
        """
        Generates audio for the given text and saves it to the output directory.
        Returns the absolute path to the saved audio file.
        """
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            
        filename = f"{uuid.uuid4()}.wav"
        output_path = os.path.join(output_dir, filename)
        
        generator = self.pipeline(text, voice=self.voice, speed=1)
        
        # Kokoro returns a generator, we take the first segment (or concat if needed)
        # For simple questions, usually one segment.
        # The generator yields (graphemes, phonemes, audio_tensor)
        
        all_audio = []
        for _, _, audio in generator:
            all_audio.append(audio)
            
        if not all_audio:
            raise Exception("No audio generated")
            
        # Concatenate if multiple segments
        final_audio = torch.cat(all_audio, dim=0) if len(all_audio) > 1 else all_audio[0]
        
        # Save to file
        sf.write(output_path, final_audio.numpy(), self.sample_rate)
        
        return output_path

# Global instance
kokoro_tts = KokoroTTS()
