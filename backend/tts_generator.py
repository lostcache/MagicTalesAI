import asyncio
import io
import wave
from typing import Dict

from google.genai import types
from google.genai.errors import APIError
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from .gemini_client import _client
from .models import CharacterVoiceAssignment, ExtractionResult, StorySegment, VoiceAssignmentResult

TTS_MODEL = "gemini-2.5-flash-preview-tts"
SAMPLE_RATE = 24000
CHANNELS = 1


def _pcm_to_wav(pcm_data: bytes, sample_rate: int = SAMPLE_RATE) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(2)  # 16-bit PCM
        wf.setframerate(sample_rate)
        wf.writeframes(pcm_data)
    return buf.getvalue()


def _to_pcm(data: bytes, mime_type: str) -> tuple[bytes, int]:
    """Return raw 16-bit PCM frames and the detected sample rate."""
    if mime_type and "wav" in mime_type.lower():
        try:
            buf = io.BytesIO(data)
            with wave.open(buf, "rb") as wf:
                frames = wf.readframes(wf.getnframes())
                rate = wf.getframerate()
                return frames, rate
        except Exception:
            # Fallback if wave.open fails on a corrupted/incomplete header
            pass
    # audio/pcm or audio/L16 — assume SAMPLE_RATE
    return data, SAMPLE_RATE


@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=2, max=15),
    retry=retry_if_exception_type(APIError),
    reraise=True,
)
async def _generate_segment(
    seg: StorySegment,
    voice: str,
) -> tuple[bytes, int]:
    config = types.GenerateContentConfig(
        response_modalities=["AUDIO"],
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice)
            )
        ),
    )
    audio_chunks: list[bytes] = []
    mime_type: str = ""

    # generate_content_stream returns an async generator
    stream = await _client.aio.models.generate_content_stream(
        model=TTS_MODEL,
        contents=seg.text,
        config=config,
    )

    async for chunk in stream:
        if not chunk.candidates:
            continue
        
        cand = chunk.candidates[0]
        if cand.finish_reason and cand.finish_reason.name not in ("STOP", "MAX_TOKENS"):
             # For now we just stop and take what we have
             break

        if not cand.content or not cand.content.parts:
            continue

        for part in cand.content.parts:
            if (
                hasattr(part, "inline_data")
                and part.inline_data
                and part.inline_data.data
            ):
                if not mime_type:
                    mime_type = part.inline_data.mime_type or ""
                audio_chunks.append(part.inline_data.data)

    combined_data = b"".join(audio_chunks)
    if not combined_data:
        return b"", SAMPLE_RATE

    return _to_pcm(combined_data, mime_type)


async def generate_segment_audio(
    extraction: ExtractionResult,
    voices: VoiceAssignmentResult,
    index: int,
) -> bytes:
    """
    Generates audio for a specific story segment.

    1. Identifies the speaker for the segment.
    2. Looks up the full voice assignment for that speaker (case-insensitive).
    3. If the assignment has an elevenlabs_voice_id, uses ElevenLabs TTS.
    4. Otherwise uses Gemini TTS, defaulting to 'Aoede' (Narrator) if not found.
    5. Returns audio wrapped in a WAV container.
    """
    if index < 0 or index >= len(extraction.segments):
        raise ValueError(f"Segment index {index} out of bounds.")

    seg = extraction.segments[index]

    # Build a normalized mapping of character names to their full assignment objects.
    assignment_map: Dict[str, CharacterVoiceAssignment] = {
        a.character_name.strip().lower(): a for a in voices.assignments
    }
    assignment = assignment_map.get(seg.speaker.strip().lower())

    # Route to ElevenLabs TTS if a custom voice is assigned.
    if assignment and assignment.elevenlabs_voice_id:
        from .elevenlabs_client import tts_elevenlabs
        pcm_data = await tts_elevenlabs(assignment.elevenlabs_voice_id, seg.text)
        if not pcm_data:
            return b""
        return _pcm_to_wav(pcm_data, SAMPLE_RATE)

    # Gemini TTS path — fall back to 'Aoede' (Narrator) if no assignment found.
    voice = assignment.voice_name.value if assignment else "Aoede"
    pcm_data, rate = await _generate_segment(seg, voice)
    if not pcm_data:
        return b""

    return _pcm_to_wav(pcm_data, rate)
