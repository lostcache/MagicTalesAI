import os

import httpx
from fastapi import HTTPException

from .models import CloneVoiceResponse

ELEVENLABS_BASE = "https://api.elevenlabs.io"
_TTS_MODEL = "eleven_multilingual_v2"


def _get_api_key() -> str:
    key = os.getenv("ELEVENLABS_API_KEY", "").strip()
    if not key:
        raise HTTPException(status_code=503, detail="ELEVENLABS_API_KEY is not configured on the server.")
    return key


async def clone_voice(name: str, audio_files: list[tuple[str, bytes, str]]) -> CloneVoiceResponse:
    """
    Clone a voice from audio samples.

    audio_files: list of (filename, content_bytes, mime_type)
    Calls POST /v1/voices/add and returns CloneVoiceResponse.
    """
    files = [("files", (fname, data, mime)) for fname, data, mime in audio_files]
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            f"{ELEVENLABS_BASE}/v1/voices/add",
            headers={"xi-api-key": _get_api_key()},
            data={"name": name},
            files=files,
        )
    if not resp.is_success:
        _raise_error(resp)
    body = resp.json()
    return CloneVoiceResponse(
        voice_id=body["voice_id"],
        requires_verification=body.get("requires_verification", False),
        name=name,
    )


async def tts_elevenlabs(voice_id: str, text: str) -> bytes:
    """
    Generate speech using an ElevenLabs voice.

    Requests pcm_24000 output (raw 16-bit PCM at 24kHz) so it is directly
    compatible with _pcm_to_wav() in tts_generator.py — no extra codec needed.
    Returns raw PCM bytes.
    """
    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(
            f"{ELEVENLABS_BASE}/v1/text-to-speech/{voice_id}",
            params={"output_format": "pcm_24000"},
            headers={"xi-api-key": _get_api_key(), "Content-Type": "application/json"},
            json={"text": text, "model_id": _TTS_MODEL},
        )
    if not resp.is_success:
        _raise_error(resp)
    return resp.content


def _raise_error(resp: httpx.Response) -> None:
    try:
        detail = resp.json().get("detail", "")
        msg = detail if isinstance(detail, str) else str(detail)
    except Exception:
        msg = resp.text[:200] or resp.reason_phrase
    raise HTTPException(status_code=resp.status_code, detail=f"ElevenLabs error: {msg}")
