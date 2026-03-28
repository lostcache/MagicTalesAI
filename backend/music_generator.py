"""Generate mood-matched background music via Google Lyria (lyria-002)."""

import logging

from google.genai import types as genai_types
from google.genai.errors import APIError
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from .gemini_client import _client

logger = logging.getLogger(__name__)

LYRIA_MODEL = "lyria-3-clip-preview"

_NO_VOICE = "no vocals, no singing, no voice, no speech, no lyrics, no words, purely instrumental"

EMOTION_PROMPTS: dict[str, str] = {
    "happy": (
        "upbeat acoustic folk, cheerful bright piano melody, warm guitar strumming, "
        "playful flute, light percussion, major key, lively and joyful, " + _NO_VOICE
    ),
    "sad": (
        "melancholic ambient orchestral, slow solo piano, soft string quartet, "
        "minor key, somber and reflective, gentle cello sustain, muted dynamics, " + _NO_VOICE
    ),
    "excited": (
        "energetic adventure theme, driving percussion, soaring orchestral strings, "
        "triumphant brass, fast tempo, major key, heroic and uplifting, " + _NO_VOICE
    ),
    "scared": (
        "dark suspense cinematic, low cello drones, dissonant string clusters, "
        "eerie synthesizer pads, tense atmosphere, minor key, slow building dread, " + _NO_VOICE
    ),
    "angry": (
        "intense dramatic orchestral, powerful brass stabs, aggressive percussion, "
        "relentless driving rhythm, dark minor key, fury and conflict, " + _NO_VOICE
    ),
    "calm": (
        "peaceful ambient, soft piano arpeggios, gentle acoustic guitar, "
        "warm synthesizer pads, serene and meditative, slow tempo, major key, " + _NO_VOICE
    ),
    "mysterious": (
        "mysterious dark atmospheric, modal harmonics, sparse piano, "
        "eerie reverb-drenched strings, haunting melody, slow ethereal pacing, "
        "minimalist and tense, " + _NO_VOICE
    ),
    "curious": (
        "light whimsical orchestral, pizzicato strings, playful woodwinds, "
        "gentle harp arpeggios, light percussion, inquisitive and bright, major key, " + _NO_VOICE
    ),
    "neutral": (
        "neutral ambient background, soft orchestral pad, gentle strings, "
        "unobtrusive and understated, medium tempo, neither happy nor sad, " + _NO_VOICE
    ),
}


@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=2, max=15),
    retry=retry_if_exception_type(APIError),
    reraise=True,
)
async def generate_emotion_music(emotion: str) -> bytes | None:
    """Generate a ~30s background music clip for the given emotion via Lyria.

    Returns raw audio bytes (audio/mpeg) or None if generation failed.
    """
    prompt_text = EMOTION_PROMPTS.get(emotion)
    if prompt_text is None:
        logger.warning("Unknown emotion '%s', skipping music generation.", emotion)
        return None

    response = await _client.aio.models.generate_content(
        model=LYRIA_MODEL,
        contents=prompt_text,
        config=genai_types.GenerateContentConfig(
            response_modalities=["AUDIO"],
            safety_settings=[
                genai_types.SafetySetting(
                    category=genai_types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                    threshold=genai_types.HarmBlockThreshold.BLOCK_NONE,
                ),
                genai_types.SafetySetting(
                    category=genai_types.HarmCategory.HARM_CATEGORY_HARASSMENT,
                    threshold=genai_types.HarmBlockThreshold.BLOCK_NONE,
                ),
                genai_types.SafetySetting(
                    category=genai_types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                    threshold=genai_types.HarmBlockThreshold.BLOCK_NONE,
                ),
                genai_types.SafetySetting(
                    category=genai_types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                    threshold=genai_types.HarmBlockThreshold.BLOCK_NONE,
                ),
            ],
        ),
    )

    if not response.candidates:
        logger.warning("Lyria returned no candidates for emotion '%s'.", emotion)
        return None

    candidate = response.candidates[0]
    if candidate.content is None:
        reason = getattr(candidate, "finish_reason", "unknown")
        logger.warning(
            "Lyria blocked response for emotion '%s' (finish_reason=%s).", emotion, reason
        )
        return None

    audio_part = next((p for p in candidate.content.parts if p.inline_data), None)
    if audio_part is None:
        logger.warning("No audio data in Lyria response for emotion '%s'.", emotion)
        return None

    return audio_part.inline_data.data
