# MagicTalesAI

An AI-powered application that converts stories (PDF/EPUB) into audiobooks with character voices and background music.

## What It Does

1. **Upload** a PDF or EPUB story
2. **Extract** characters and narrative segments using Google Gemini AI
3. **Assign voices** to characters (Gemini prebuilt TTS voices or ElevenLabs voice cloning)
4. **Generate audio** segment by segment with character-appropriate voices
5. **Generate background music** matched to the emotional tone of each scene (Google Lyria)
6. **Play** the audiobook in an interactive player with character and emotion tracking

## Tech Stack

**Backend** — Python/FastAPI
- Google Gemini 2.5 Flash (story extraction, TTS, Lyria music generation)
- ElevenLabs API (voice cloning)
- Google Cloud Firestore + Storage (persistence)
- pypdf, ebooklib (file parsing)

**Frontend** — React/TypeScript
- Vite + Tailwind CSS + Shadcn UI
- TanStack React Query
- React Router 6

## Setup

### Prerequisites
- Python 3.11+
- Node.js 18+
- A Google API key with Gemini access

### Backend

```bash
pip install -r requirements.txt
cp .env.example .env
# Add your GOOGLE_API_KEY to .env
uvicorn backend.main:app --reload
```

### Frontend

```bash
cd magictales-ai-stories
npm install
npm run dev
```

The frontend runs on `http://localhost:5173` and proxies API requests to the FastAPI backend on `http://localhost:8000`.

## Environment Variables

| Variable | Description |
|---|---|
| `GOOGLE_API_KEY` | Google AI Studio API key (required) |
| `ELEVENLABS_API_KEY` | ElevenLabs API key (optional, for voice cloning) |

## Key API Endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/upload-text` | Upload PDF/EPUB |
| `POST` | `/api/extract-characters` | Extract characters and segments |
| `POST` | `/api/stories/{id}/assign-voices` | Auto-assign character voices |
| `GET` | `/api/stories/{id}/audio/{index}` | Generate/fetch segment audio |
| `POST` | `/api/stories/{id}/generate-music` | Generate background music |
| `POST` | `/api/voices/clone` | Clone a voice via ElevenLabs |
| `GET` | `/api/stories` | List all stories |

## Available Voices

8 Gemini prebuilt voices: Puck, Charon, Kore, Fenrir, Aoede, Leda, Orus, Zephyr — assigned to characters based on role, gender, and speaking style.

## License

MIT
