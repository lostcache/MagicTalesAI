"""Generate mood-matched background music via Google Lyria (lyria-002)."""

import json
import logging

from google.genai import types as genai_types
from google.genai.errors import APIError
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from .gemini_client import MODEL, _client
from .models import ExtractionResult

logger = logging.getLogger(__name__)

LYRIA_MODEL = "lyria-3-clip-preview"

_NO_VOICE = "no vocals, no singing, no voice, no speech, no lyrics, no words, purely instrumental"

EMOTION_PROMPTS: dict[str, str] = {
    "happy": (
        "warm storybook orchestral, gentle piano melody, light pizzicato strings, "
        "soft flute, cheerful and pastoral, children's film score, moderate tempo, soft dynamics, " + _NO_VOICE
    ),
    "sad": (
        "tender solo piano, gentle string underscore, bittersweet and introspective, "
        "slow tempo, muted cello, children's film emotional score, soft dynamics, " + _NO_VOICE
    ),
    "excited": (
        "adventurous children's orchestral, buoyant strings, light brass swell, "
        "playful momentum, heroic but gentle, moderate-fast tempo, soft-to-medium dynamics, " + _NO_VOICE
    ),
    "scared": (
        "eerie children's suspense score, sparse low strings, subtle dissonance, "
        "haunting woodwinds, mysterious tension, slow tempo, soft dynamics, " + _NO_VOICE
    ),
    "angry": (
        "tense dramatic underscore, brooding low brass, dissonant strings, "
        "restless rhythm, conflict and unease, children's film score, medium tempo, medium dynamics, " + _NO_VOICE
    ),
    "calm": (
        "serene pastoral orchestral, soft piano arpeggios, warm strings, "
        "peaceful and gentle, storybook lullaby feel, slow tempo, soft dynamics, " + _NO_VOICE
    ),
    "mysterious": (
        "fairy-tale mystery score, modal strings, sparse celesta, "
        "wondering and ethereal, enchanted forest atmosphere, slow tempo, soft dynamics, " + _NO_VOICE
    ),
    "curious": (
        "whimsical children's score, playful pizzicato strings, light woodwinds, "
        "inquisitive and bright, storybook wonder, moderate tempo, soft dynamics, " + _NO_VOICE
    ),
    "neutral": (
        "gentle storybook underscore, warm orchestral pad, soft strings, "
        "unobtrusive and neutral, children's film background, slow tempo, soft dynamics, " + _NO_VOICE
    ),
}


async def build_story_music_prompts(
    extraction: ExtractionResult,
    emotions: set[str],
    filename: str = "",
) -> dict[str, str]:
    """Ask Gemini to generate story-specific Lyria prompts for each emotion.

    Falls back gracefully (returns {}) on any failure; callers should then
    use EMOTION_PROMPTS as the default.
    """
    char_summary = "; ".join(
        f"{c.name} ({c.role.value}): {c.description}"
        for c in extraction.characters[:8]
    )
    story_sample = " ".join(s.text for s in extraction.segments[:12])[:1500]
    emotions_list = ", ".join(sorted(emotions))

    prompt = (
        "You are a film score consultant for a children's audiobook app. "
        "Generate Lyria AI music generation prompts for background narration music.\n\n"
        f"Story filename: {filename}\n"
        f"Characters: {char_summary}\n"
        f"Story excerpt: {story_sample}\n\n"
        f"Emotions needed: {emotions_list}\n\n"
        "For each emotion, write a short Lyria prompt (comma-separated descriptors, ~15-20 words) "
        "that reflects this story's specific setting, period, and genre. "
        "Music is soft background underscore — do NOT use: upbeat, driving, triumphant, energetic, powerful. "
        f"End every prompt with: {_NO_VOICE}\n\n"
        'Return a JSON object: {"emotion": "prompt string", ...}. Include only the requested emotions.'
    )

    try:
        response = await _client.aio.models.generate_content(
            model=MODEL,
            contents=prompt,
            config=genai_types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.5,
                max_output_tokens=1024,
            ),
        )
        if response.text:
            raw = json.loads(response.text)
            cleaned: dict[str, str] = {}
            for emotion, text in raw.items():
                if emotion in emotions:
                    if _NO_VOICE not in text:
                        text = text.rstrip(", ") + ", " + _NO_VOICE
                    cleaned[emotion] = text
            return cleaned
    except Exception:
        logger.warning("Failed to build story-specific music prompts; falling back to defaults.")
    return {}


@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=2, max=15),
    retry=retry_if_exception_type(APIError),
    reraise=True,
)
async def generate_emotion_music(emotion: str, prompt_text: str | None = None) -> bytes | None:
    """Generate a ~30s background music clip for the given emotion via Lyria.

    Returns raw audio bytes (audio/mpeg) or None if generation failed.
    """
    prompt_text = prompt_text or EMOTION_PROMPTS.get(emotion)
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
