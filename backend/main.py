import asyncio
import uuid
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response

from .file_extractor import extract_text_from_epub, extract_text_from_pdf
from .gemini_client import extract_characters_from_story
from .models import ExtractRequest, ExtractResponse, StoryMeta
from .music_generator import generate_emotion_music
from .storage import (
    list_stories, load_full_session, load_music,
    music_path, save_extraction, save_meta, save_music,
    save_segment_audio, save_voices, segment_audio_path,
)
from .tts_generator import generate_segment_audio
from .voice_assigner import assign_voices

app = FastAPI(title="MagicTales-AI", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.get("/")
async def serve_frontend():
    return FileResponse("frontend/index.html")


@app.post("/api/upload-text")
async def upload_text(file: UploadFile):
    filename = (file.filename or "").lower()
    if not (filename.endswith(".pdf") or filename.endswith(".epub")):
        raise HTTPException(status_code=415, detail="Only PDF and EPUB files are supported.")

    data = await file.read()
    text = extract_text_from_pdf(data) if filename.endswith(".pdf") else extract_text_from_epub(data)
    return {"text": text, "filename": file.filename}


@app.post("/api/extract-characters", response_model=ExtractResponse)
async def extract_characters(request: ExtractRequest):
    result = await extract_characters_from_story(request.text)
    story_id = str(uuid.uuid4())

    meta = StoryMeta(
        story_id=story_id,
        filename=request.filename,
        created_at=datetime.now(timezone.utc).isoformat(),
        status="extracted",
    )
    save_meta(story_id, meta)
    save_extraction(story_id, result)

    return ExtractResponse(story_id=story_id, **result.model_dump())


@app.post("/api/stories/{story_id}/assign-voices")
async def assign_voices_endpoint(story_id: str):
    from .storage import load_extraction, load_meta, save_meta

    extraction = load_extraction(story_id)
    voice_result = await assign_voices(extraction)
    save_voices(story_id, voice_result)

    meta = load_meta(story_id)
    meta.status = "voices_assigned"
    save_meta(story_id, meta)

    return voice_result


@app.get("/api/stories/{story_id}/audio/{index}")
async def get_segment_audio_endpoint(story_id: str, index: int, force: bool = False):
    from .storage import load_extraction, load_voices, load_meta

    cached = segment_audio_path(story_id, index)
    if not force and cached.exists():
        return Response(content=cached.read_bytes(), media_type="audio/wav")

    extraction = load_extraction(story_id)
    voices = load_voices(story_id)

    if index < 0 or index >= len(extraction.segments):
        raise HTTPException(status_code=404, detail="Segment index out of bounds")

    wav_bytes = await generate_segment_audio(extraction, voices, index)
    if not wav_bytes:
        raise HTTPException(status_code=500, detail="Failed to generate audio for segment.")

    save_segment_audio(story_id, index, wav_bytes)

    if index == 0:
        meta = load_meta(story_id)
        if meta.status != "audio_generated":
            meta.status = "audio_generated"
            save_meta(story_id, meta)

    return Response(content=wav_bytes, media_type="audio/wav")


@app.post("/api/stories/{story_id}/generate-music")
async def generate_music_endpoint(story_id: str):
    from .storage import load_extraction

    extraction = load_extraction(story_id)
    unique_emotions = {seg.emotion.value for seg in extraction.segments}

    async def _gen(emotion: str) -> tuple[str, str]:
        if music_path(story_id, emotion).exists():
            return emotion, "cached"
        data = await generate_emotion_music(emotion)
        if data:
            save_music(story_id, emotion, data)
            return emotion, "generated"
        return emotion, "failed"

    results = await asyncio.gather(*[_gen(e) for e in unique_emotions])
    return {"emotions": dict(results)}


@app.get("/api/stories/{story_id}/music/{emotion}")
async def get_music_endpoint(story_id: str, emotion: str):
    data = load_music(story_id, emotion)
    if data is None:
        # Generate on demand if not cached (handles partial pre-generation failures)
        data = await generate_emotion_music(emotion)
        if data is None:
            raise HTTPException(status_code=404, detail=f"Music generation failed for emotion '{emotion}'")
        save_music(story_id, emotion, data)
    return Response(content=data, media_type="audio/mpeg")


@app.get("/api/stories")
async def list_stories_endpoint():
    return list_stories()


@app.get("/api/stories/{story_id}")
async def get_story(story_id: str):
    return load_full_session(story_id)
