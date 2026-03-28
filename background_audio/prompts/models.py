from __future__ import annotations

from dataclasses import dataclass


@dataclass
class MusicPrompt:
    section_index: int
    section_title: str
    prompt_text: str
    negative_prompt: str
    bpm: int
    seed: int | None = None
    model: str = "lyria-002"
    analysis_summary: str = ""
