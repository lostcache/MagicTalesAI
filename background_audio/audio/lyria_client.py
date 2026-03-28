"""Client for Google Lyria music generation — via Gemini API key or Vertex AI."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Protocol

from google import genai
from google.genai import types as genai_types

from background_audio.audio.models import GenerationResult
from background_audio.config import Settings
from background_audio.prompts.models import MusicPrompt

logger = logging.getLogger(__name__)


class LyriaClientProtocol(Protocol):
    async def generate(self, prompt: MusicPrompt) -> GenerationResult | None: ...


class GeminiLyriaClient:
    """Generate music via Lyria using a Google AI Studio API key (no GCP needed)."""

    def __init__(self, settings: Settings) -> None:
        self._client = genai.Client(api_key=settings.gemini_api_key)
        self._model = settings.lyria_model
        self._semaphore = asyncio.Semaphore(settings.max_concurrent_generations)

    async def generate(self, prompt: MusicPrompt) -> GenerationResult | None:
        async with self._semaphore:
            response = await self._client.aio.models.generate_content(
                model=self._model,
                contents=prompt.prompt_text,
                config=genai_types.GenerateContentConfig(
                    response_modalities=["AUDIO"],
                ),
            )

            # Guard: no candidates returned
            if not response.candidates:
                logger.warning(
                    "Section %d (%s): Lyria returned no candidates — skipping.",
                    prompt.section_index, prompt.section_title,
                )
                return None

            candidate = response.candidates[0]

            # Guard: candidate has no content (e.g. safety block)
            if candidate.content is None:
                reason = getattr(candidate, "finish_reason", "unknown")
                logger.warning(
                    "Section %d (%s): Lyria blocked response (finish_reason=%s) — skipping.",
                    prompt.section_index, prompt.section_title, reason,
                )
                return None

            # Find the part containing audio
            audio_part = next(
                (p for p in candidate.content.parts if p.inline_data),
                None,
            )
            if audio_part is None:
                logger.warning(
                    "Section %d (%s): No audio data in response — skipping.",
                    prompt.section_index, prompt.section_title,
                )
                return None

            audio_bytes = audio_part.inline_data.data
            mime_type = audio_part.inline_data.mime_type or "audio/mpeg"

            return GenerationResult(
                section_index=prompt.section_index,
                section_title=prompt.section_title,
                audio_bytes=audio_bytes,
                mime_type=mime_type,
                duration_seconds=30.0,
                model_used=self._model,
                prompt_used=prompt,
                generated_at=datetime.now(timezone.utc),
            )


def create_lyria_client(settings: Settings) -> LyriaClientProtocol:
    """Factory: use Gemini API key if available, otherwise fall back to Vertex AI."""
    if settings.gemini_api_key:
        return GeminiLyriaClient(settings)

    # Vertex AI fallback (requires GCP project + ADC)
    from background_audio.audio._lyria_vertex import create_vertex_client
    return create_vertex_client(settings)
