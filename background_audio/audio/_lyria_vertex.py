"""Vertex AI Lyria clients (fallback when no Gemini API key is set)."""

from __future__ import annotations

import asyncio
import base64
import logging
from datetime import datetime, timezone

import httpx
from google.auth import default as google_auth_default
from google.auth.transport.requests import Request as GoogleAuthRequest

from background_audio.audio.models import GenerationResult
from background_audio.config import Settings
from background_audio.prompts.models import MusicPrompt

logger = logging.getLogger(__name__)


class Lyria2VertexClient:
    def __init__(self, settings: Settings) -> None:
        self._project = settings.gcp_project
        self._location = settings.gcp_location
        self._semaphore = asyncio.Semaphore(settings.max_concurrent_generations)
        self._credentials, _ = google_auth_default(
            scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )

    def _get_token(self) -> str:
        self._credentials.refresh(GoogleAuthRequest())
        return self._credentials.token

    async def generate(self, prompt: MusicPrompt) -> GenerationResult:
        async with self._semaphore:
            token = await asyncio.to_thread(self._get_token)
            endpoint = (
                f"https://{self._location}-aiplatform.googleapis.com/v1/"
                f"projects/{self._project}/locations/{self._location}/"
                f"publishers/google/models/lyria-002:predict"
            )
            payload: dict = {
                "instances": [{"prompt": prompt.prompt_text}],
                "parameters": {"sample_count": 1},
            }
            if prompt.negative_prompt:
                payload["instances"][0]["negative_prompt"] = prompt.negative_prompt
            if prompt.seed is not None:
                payload["instances"][0]["seed"] = prompt.seed

            headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
            async with httpx.AsyncClient(timeout=120) as client:
                response = await client.post(endpoint, json=payload, headers=headers)
                response.raise_for_status()

            audio_bytes = base64.b64decode(response.json()["predictions"][0]["bytesBase64Encoded"])
            return GenerationResult(
                section_index=prompt.section_index,
                section_title=prompt.section_title,
                audio_bytes=audio_bytes,
                mime_type="audio/wav",
                duration_seconds=30.0,
                model_used="lyria-002",
                prompt_used=prompt,
                generated_at=datetime.now(timezone.utc),
            )


def create_vertex_client(settings: Settings):
    return Lyria2VertexClient(settings)
