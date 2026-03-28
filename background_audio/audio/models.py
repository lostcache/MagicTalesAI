from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from background_audio.prompts.models import MusicPrompt


@dataclass
class GenerationRequest:
    prompt: MusicPrompt
    project_id: str
    location: str


@dataclass
class GenerationResult:
    section_index: int
    section_title: str
    audio_bytes: bytes
    mime_type: str
    duration_seconds: float
    model_used: str
    prompt_used: MusicPrompt
    generated_at: datetime
