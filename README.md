# AI Interviewer: Backend

FastAPI backend for an AI interview practice system. It reads a candidate's resume and a job description, generates tailored questions, speaks them aloud, transcribes the spoken answers on-device, and produces a scored evaluation report.

This repository contains the backend only, with the focus on the local speech pipeline.

## Speech pipeline

| Stage | Tech | Where it runs |
|---|---|---|
| Speech-to-text | `parakeet-mlx` (`mlx-community/parakeet-tdt-0.6b-v3`) | Local, on Apple Silicon (private, no audio leaves the machine) |
| Text-to-speech | ElevenLabs (`eleven_multilingual_v2`) | Cloud API |
| Text-to-speech (offline option) | Kokoro | Local |

- `stt_engine.py` wraps Parakeet in a small `ParakeetSTT` class (model loaded once, then `transcribe(path)`).
- `run_local.py` is an interactive loop for trying the STT engine on audio files from the terminal.
- `backend/app/services/stt_service.py` exposes the engine as a singleton to the API.
- `backend/app/services/tts_service.py` and `kokoro_tts.py` generate the question audio.

## Backend features

- Resume parsing from PDF and DOCX (`resume_parser.py`).
- Question generation from resume and job description, using OpenAI or Gemini (`LLM_PROVIDER`).
- LLM evaluation of the full interview transcript into scores and feedback (`evaluation_service.py`).
- Interview session lifecycle: generate link, start, submit answer and video, complete, fail, reschedule, report and download.
- Persistence with SQLModel on PostgreSQL, with a SQLite fallback for local development.

## Endpoints (prefix `/api/v1`)

`POST /upload-resume`, `/preview-questions`, `/generate-questions`, `/generate-audio`, `/submit-answer`, `/submit-video`, `/evaluate`, `/complete`
`GET /interviews`, `/interviews/{id}`, `/interviews/{id}/report`, `/interviews/{id}/download`, `/audio/{session_id}/{filename}`
`POST /interviews/{id}/start`, `/interviews/{id}/reschedule`, `/interviews/{id}/fail`

## Requirements

- Python 3.10+ (3.11 recommended)
- Apple Silicon Mac, required by `parakeet-mlx`
- API keys for the providers you use (see `.env.example`)

## Setup

```bash
cd backend
python3 -m venv myenv && source myenv/bin/activate
pip install -r requirements.txt
cp ../.env.example .env        # then fill in your own keys
uvicorn main:app --reload --port 8000
```

Or run `./start_backend.sh` from the repo root. The first run downloads the STT model (about 1 to 2 GB).

Try the speech-to-text engine on its own:

```bash
python run_local.py
```

## Notes

- CORS is open (`*`) for development. Restrict `allow_origins` in `backend/main.py` before deploying.
- Uploaded resumes, recordings and transcripts are stored under `logs/` and are git-ignored.
