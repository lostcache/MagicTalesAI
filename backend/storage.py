import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Any, Optional

from fastapi import HTTPException
from google.cloud import firestore, storage

from .models import ExtractionResult, StoryMeta, VoiceAssignmentResult

logger = logging.getLogger(__name__)

project_id = os.getenv("GCP_PROJECT_ID")
bucket_name = os.getenv("GCS_BUCKET_NAME")
database_id = os.getenv("GCP_DATABASE_ID", "(default)")

DATA_DIR = Path(os.getenv("MAGIC_TALES_DATA_DIR", "data"))

db: Optional[firestore.AsyncClient] = None
gcs = None
bucket = None
_use_local = True

if project_id:
    try:
        db = firestore.AsyncClient(project=project_id, database=database_id)
        gcs = storage.Client(project=project_id) if bucket_name else None
        bucket = gcs.bucket(bucket_name) if gcs and bucket_name else None
        _use_local = False
        logger.info("Using GCP Firestore (project=%s) and GCS when bucket is set.", project_id)
    except Exception as e:
        logger.warning(
            "GCP init failed (%s). Using local folder %s instead. "
            "For Firestore, run: gcloud auth application-default login",
            e,
            DATA_DIR.resolve(),
        )
        db = None
        gcs = None
        bucket = None
        _use_local = True
else:
    logger.info("GCP_PROJECT_ID not set; using local folder %s", DATA_DIR.resolve())


def _story_dir(story_id: str) -> Path:
    p = DATA_DIR / story_id
    p.mkdir(parents=True, exist_ok=True)
    return p


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


async def save_meta(story_id: str, meta: StoryMeta) -> None:
    if not _use_local:
        doc_ref = db.collection("stories").document(story_id)
        await doc_ref.set({"meta": meta.model_dump()}, merge=True)
        return
    path = _story_dir(story_id) / "meta.json"
    await asyncio.to_thread(_write_json, path, meta.model_dump())


async def save_extraction(story_id: str, result: ExtractionResult) -> None:
    if not _use_local:
        doc_ref = db.collection("stories").document(story_id)
        await doc_ref.set({"extraction": result.model_dump()}, merge=True)
        return
    path = _story_dir(story_id) / "extraction.json"
    await asyncio.to_thread(_write_json, path, result.model_dump())


async def save_voices(story_id: str, result: VoiceAssignmentResult) -> None:
    if not _use_local:
        doc_ref = db.collection("stories").document(story_id)
        await doc_ref.set({"voices": result.model_dump()}, merge=True)
        return
    path = _story_dir(story_id) / "voices.json"
    await asyncio.to_thread(_write_json, path, result.model_dump())


async def _get_doc_field(story_id: str, field: str, label: str) -> dict:
    if not _use_local:
        doc = await db.collection("stories").document(story_id).get()
        if not doc.exists:
            raise HTTPException(status_code=404, detail=f"Story {story_id} not found.")
        data = doc.to_dict()
        if not data or field not in data:
            raise HTTPException(
                status_code=404, detail=f"{label} not found for story '{story_id}'."
            )
        return data[field]

    base = DATA_DIR / story_id
    name = f"{field}.json" if field != "meta" else "meta.json"
    if field == "extraction":
        name = "extraction.json"
    elif field == "voices":
        name = "voices.json"
    path = base / name
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Story {story_id} not found.")
    return _read_json(path)


async def load_meta(story_id: str) -> StoryMeta:
    data = await _get_doc_field(story_id, "meta", "Meta")
    return StoryMeta.model_validate(data)


async def load_extraction(story_id: str) -> ExtractionResult:
    data = await _get_doc_field(story_id, "extraction", "Extraction")
    return ExtractionResult.model_validate(data)


async def load_voices(story_id: str) -> VoiceAssignmentResult:
    data = await _get_doc_field(story_id, "voices", "Voice assignment")
    return VoiceAssignmentResult.model_validate(data)


def _get_blob(blob_name: str):
    if not bucket:
        logging.warning("GCS_BUCKET_NAME not set, cannot access storage")
        return None
    return bucket.blob(blob_name)


async def has_segment_audio(story_id: str, index: int) -> bool:
    if _use_local:
        path = DATA_DIR / story_id / f"audio_{index}.wav"
        return await asyncio.to_thread(path.exists)
    blob = _get_blob(f"{story_id}/audio_{index}.wav")
    if not blob:
        return False
    return await asyncio.to_thread(blob.exists)


async def load_segment_audio(story_id: str, index: int) -> Optional[bytes]:
    if _use_local:
        path = DATA_DIR / story_id / f"audio_{index}.wav"
        if await asyncio.to_thread(path.exists):
            return await asyncio.to_thread(path.read_bytes)
        return None
    blob = _get_blob(f"{story_id}/audio_{index}.wav")
    if blob and await asyncio.to_thread(blob.exists):
        return await asyncio.to_thread(blob.download_as_bytes)
    return None


async def save_segment_audio(story_id: str, index: int, wav_bytes: bytes) -> None:
    if _use_local:
        path = _story_dir(story_id) / f"audio_{index}.wav"
        await asyncio.to_thread(path.write_bytes, wav_bytes)
        return
    blob = _get_blob(f"{story_id}/audio_{index}.wav")
    if blob:
        await asyncio.to_thread(blob.upload_from_string, wav_bytes, content_type="audio/wav")


async def has_music(story_id: str, emotion: str) -> bool:
    if _use_local:
        path = DATA_DIR / story_id / f"music_{emotion}.mp3"
        return await asyncio.to_thread(path.exists)
    blob = _get_blob(f"{story_id}/music_{emotion}.mp3")
    if not blob:
        return False
    return await asyncio.to_thread(blob.exists)


async def save_music(story_id: str, emotion: str, data: bytes) -> None:
    if _use_local:
        path = _story_dir(story_id) / f"music_{emotion}.mp3"
        await asyncio.to_thread(path.write_bytes, data)
        return
    blob = _get_blob(f"{story_id}/music_{emotion}.mp3")
    if blob:
        await asyncio.to_thread(blob.upload_from_string, data, content_type="audio/mpeg")


async def load_music(story_id: str, emotion: str) -> Optional[bytes]:
    if _use_local:
        path = DATA_DIR / story_id / f"music_{emotion}.mp3"
        if await asyncio.to_thread(path.exists):
            return await asyncio.to_thread(path.read_bytes)
        return None
    blob = _get_blob(f"{story_id}/music_{emotion}.mp3")
    if blob and await asyncio.to_thread(blob.exists):
        return await asyncio.to_thread(blob.download_as_bytes)
    return None


async def list_stories() -> list[StoryMeta]:
    if not _use_local:
        stories = []
        docs = db.collection("stories").stream()
        async for doc in docs:
            data = doc.to_dict()
            if data and "meta" in data:
                try:
                    stories.append(StoryMeta.model_validate(data["meta"]))
                except Exception:
                    pass
        stories.sort(key=lambda s: s.created_at, reverse=True)
        return stories

    stories: list[StoryMeta] = []
    if not await asyncio.to_thread(DATA_DIR.exists):
        return []
    for d in sorted(await asyncio.to_thread(lambda: list(DATA_DIR.iterdir()))):
        if not d.is_dir():
            continue
        meta_path = d / "meta.json"
        if await asyncio.to_thread(meta_path.exists):
            try:
                data = await asyncio.to_thread(_read_json, meta_path)
                stories.append(StoryMeta.model_validate(data))
            except Exception:
                pass
    stories.sort(key=lambda s: s.created_at, reverse=True)
    return stories


async def load_full_session(story_id: str) -> dict:
    if not _use_local:
        doc = await db.collection("stories").document(story_id).get()
        if not doc.exists:
            raise HTTPException(status_code=404, detail="Story not found")
        data = doc.to_dict()
        meta = data.get("meta")
        extraction = data.get("extraction")
        voices = data.get("voices")
        has_audio = await has_segment_audio(story_id, 0)
        return {
            **meta,
            "characters": extraction.get("characters", []) if extraction else [],
            "segments": extraction.get("segments", []) if extraction else [],
            "voice_assignments": voices.get("assignments", []) if voices else None,
            "has_audio": has_audio,
        }

    base = DATA_DIR / story_id
    meta_path = base / "meta.json"
    if not await asyncio.to_thread(meta_path.exists):
        raise HTTPException(status_code=404, detail="Story not found")
    meta = await asyncio.to_thread(_read_json, meta_path)
    extraction_path = base / "extraction.json"
    voices_path = base / "voices.json"
    extraction = (
        await asyncio.to_thread(_read_json, extraction_path)
        if await asyncio.to_thread(extraction_path.exists)
        else None
    )
    voices = (
        await asyncio.to_thread(_read_json, voices_path)
        if await asyncio.to_thread(voices_path.exists)
        else None
    )
    has_audio = await has_segment_audio(story_id, 0)
    return {
        **meta,
        "characters": extraction.get("characters", []) if extraction else [],
        "segments": extraction.get("segments", []) if extraction else [],
        "voice_assignments": voices.get("assignments", []) if voices else None,
        "has_audio": has_audio,
    }
