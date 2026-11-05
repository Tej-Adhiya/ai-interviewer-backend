from stt_engine import ParakeetSTT
import os
import sys
import gc

def main():
    print("Initializing Parakeet STT...")
    print("Loading model (this takes a moment)...")
    
    # Initialize engine once
    engine = ParakeetSTT()
    
    print("\nModel loaded and ready!")
    print("Enter 'q' or press Ctrl+C to quit.")

    while True:
        try:
            user_input = input("\nEnter path to audio file: ").strip()
            
            if user_input.lower() == 'q':
                print("Exiting...")
                break
            
            # Handle quoted paths (drag & drop often adds quotes)
            file_path = user_input.strip("'\"")
            
            if not file_path:
                continue

            if not os.path.exists(file_path):
                print(f"Error: File not found: {file_path}")
                continue

            # Transcribe
            print(f"Transcribing '{file_path}'...")
            text = engine.transcribe(file_path)
            
            print("\n--- Transcript ---")
            print(text)
            print("------------------")
            
            # Clear result from memory
            del text
            # Force garbage collection to ensure memory is freed for next run
            gc.collect()
            print("(Ready for next file)")

        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except Exception as e:
            print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()
