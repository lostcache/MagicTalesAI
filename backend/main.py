import asyncio
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles

from .elevenlabs_client import clone_voice
from .file_extractor import extract_text_from_epub, extract_text_from_pdf
from .gemini_client import extract_characters_from_story
from .models import AssignCustomVoiceRequest, CloneVoiceResponse, ExtractRequest, ExtractResponse, StoryMeta
from .music_generator import build_story_music_prompts, generate_emotion_music
from .storage import (
    delete_segment_audio, has_music, has_segment_audio, list_stories, load_full_session,
    load_music, load_segment_audio, save_extraction, save_meta,
    save_music, save_segment_audio, save_voices
)
from .tts_generator import generate_segment_audio
from .voice_assigner import assign_voices
from .live_ws import router as live_ws_router

SPA_DIST = Path(__file__).resolve().parent.parent / "magictales-ai-stories" / "dist"


def _spa_index() -> FileResponse | Response:
    index = SPA_DIST / "index.html"
    if not index.is_file():
        return Response(
            "Frontend not built. From repo root: cd magictales-ai-stories && npm install && npm run build\n",
            media_type="text/plain",
            status_code=503,
        )
    return FileResponse(index)


app = FastAPI(title="MagicTales-AI", version="0.1.0")
app.include_router(live_ws_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.get("/")
async def serve_spa_root():
    return _spa_index()


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
    await save_meta(story_id, meta)
    await save_extraction(story_id, result)

    return ExtractResponse(story_id=story_id, **result.model_dump())


@app.post("/api/stories/{story_id}/assign-voices")
async def assign_voices_endpoint(story_id: str):
    from .storage import load_extraction, load_meta, save_meta

    extraction = await load_extraction(story_id)
    voice_result = await assign_voices(extraction)
    await save_voices(story_id, voice_result)

    meta = await load_meta(story_id)
    meta.status = "voices_assigned"
    await save_meta(story_id, meta)

    return voice_result


@app.get("/api/stories/{story_id}/audio/{index}")
async def get_segment_audio_endpoint(story_id: str, index: int, force: bool = False):
    from .storage import load_extraction, load_voices, load_meta

    if not force and await has_segment_audio(story_id, index):
        cached = await load_segment_audio(story_id, index)
        if cached:
            return Response(content=cached, media_type="audio/wav")

    extraction = await load_extraction(story_id)
    voices = await load_voices(story_id)

    if index < 0 or index >= len(extraction.segments):
        raise HTTPException(status_code=404, detail="Segment index out of bounds")

    wav_bytes = await generate_segment_audio(extraction, voices, index)
    if not wav_bytes:
        raise HTTPException(status_code=500, detail="Failed to generate audio for segment.")

    await save_segment_audio(story_id, index, wav_bytes)

    if index == 0:
        meta = await load_meta(story_id)
        if meta.status != "audio_generated":
            meta.status = "audio_generated"
            await save_meta(story_id, meta)

    return Response(content=wav_bytes, media_type="audio/wav")


@app.post("/api/stories/{story_id}/generate-music")
async def generate_music_endpoint(story_id: str):
    from .storage import load_extraction, load_meta

    extraction = await load_extraction(story_id)
    meta = await load_meta(story_id)
    unique_emotions = {seg.emotion.value for seg in extraction.segments}

    story_prompts = await build_story_music_prompts(extraction, unique_emotions, meta.filename)

    async def _gen(emotion: str) -> tuple[str, str]:
        if await has_music(story_id, emotion):
            return emotion, "cached"
        data = await generate_emotion_music(emotion, story_prompts.get(emotion))
        if data:
            await save_music(story_id, emotion, data)
            return emotion, "generated"
        return emotion, "failed"

    results = await asyncio.gather(*[_gen(e) for e in unique_emotions])
    return {"emotions": dict(results)}


@app.get("/api/stories/{story_id}/music/{emotion}")
async def get_music_endpoint(story_id: str, emotion: str):
    data = await load_music(story_id, emotion)
    if data is None:
        # Generate on demand if not cached (handles partial pre-generation failures)
        from .storage import load_extraction, load_meta
        extraction = await load_extraction(story_id)
        meta = await load_meta(story_id)
        story_prompts = await build_story_music_prompts(extraction, {emotion}, meta.filename)
        data = await generate_emotion_music(emotion, story_prompts.get(emotion))
        if data is None:
            raise HTTPException(status_code=404, detail=f"Music generation failed for emotion '{emotion}'")
        await save_music(story_id, emotion, data)
    return Response(content=data, media_type="audio/mpeg")


@app.post("/api/voices/clone", response_model=CloneVoiceResponse)
async def clone_voice_endpoint(
    name: str = Form(default=""),
    files: list[UploadFile] = File(...),
):
    if not files:
        raise HTTPException(status_code=400, detail="Upload at least one audio file.")
    if len(files) > 5:
        raise HTTPException(status_code=400, detail="Maximum 5 audio files allowed.")
    audio_files = [
        (f.filename or "sample.webm", await f.read(), f.content_type or "application/octet-stream")
        for f in files
    ]
    label = name.strip() or f"Clone {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M')}"
    return await clone_voice(label, audio_files)


@app.post("/api/stories/{story_id}/assign-custom-voice")
async def assign_custom_voice_endpoint(story_id: str, request: AssignCustomVoiceRequest):
    from .storage import load_extraction, load_voices

    extraction = await load_extraction(story_id)
    voices = await load_voices(story_id)

    target = request.character_name.strip().lower()
    new_assignments = []
    updated = False
    for a in voices.assignments:
        if a.character_name.strip().lower() == target:
            new_assignments.append(a.model_copy(update={"elevenlabs_voice_id": request.elevenlabs_voice_id}))
            updated = True
        else:
            new_assignments.append(a)

    if not updated:
        raise HTTPException(
            status_code=404,
            detail=f"Character '{request.character_name}' not found in voice assignments."
        )

    await save_voices(story_id, voices.model_copy(update={"assignments": new_assignments}))

    # Bust GCS cache for all segments spoken by this character
    affected = [
        i for i, seg in enumerate(extraction.segments)
        if seg.speaker.strip().lower() == target
    ]
    for idx in affected:
        await delete_segment_audio(story_id, idx)

    return {
        "character_name": request.character_name,
        "elevenlabs_voice_id": request.elevenlabs_voice_id,
        "segments_invalidated": len(affected),
    }


@app.get("/api/stories")
async def list_stories_endpoint():
    return await list_stories()


@app.get("/api/stories/{story_id}")
async def get_story(story_id: str):
    return await load_full_session(story_id)


_assets_dir = SPA_DIST / "assets"
if _assets_dir.is_dir():
    app.mount("/assets", StaticFiles(directory=_assets_dir), name="spa_assets")


@app.get("/{full_path:path}")
async def serve_spa_or_static(full_path: str):
    """Serve files from the Vite build (e.g. favicon) or SPA index for client-side routes."""
    if full_path.startswith("api/"):
        raise HTTPException(status_code=404, detail="Not found")
    candidate = (SPA_DIST / full_path).resolve()
    try:
        candidate.relative_to(SPA_DIST.resolve())
    except ValueError:
        raise HTTPException(status_code=404, detail="Not found") from None
    if candidate.is_file():
        return FileResponse(candidate)
    return _spa_index()
