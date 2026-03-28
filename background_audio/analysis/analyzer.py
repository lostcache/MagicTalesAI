"""LLM-based text analysis to extract musical qualities from book sections."""

from __future__ import annotations

import json
from typing import Protocol

import anthropic
from google import genai
from google.genai import types as genai_types

from background_audio.analysis.models import BookSection, Pacing, TextAnalysis
from background_audio.config import Settings
from background_audio.prompts.templates import ANALYSIS_SYSTEM_PROMPT, ANALYSIS_USER_PROMPT


def _parse_pacing(value: str) -> Pacing:
    """Normalize any pacing string from the LLM into a valid Pacing enum."""
    v = value.lower().strip()
    if v in ("fast", "quick", "rapid", "brisk", "allegro"):
        return Pacing.FAST
    if v in ("slow", "leisurely", "adagio", "andante", "deliberate"):
        return Pacing.SLOW
    return Pacing.MODERATE  # default for "moderate", "medium", "steady", etc.


class TextAnalyzerProtocol(Protocol):
    async def analyze(
        self, section: BookSection, total_sections: int
    ) -> TextAnalysis: ...


class ClaudeAnalyzer:
    """Analyze book sections using Claude."""

    def __init__(self, settings: Settings) -> None:
        self._client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        self._model = settings.claude_model

    async def analyze(
        self, section: BookSection, total_sections: int
    ) -> TextAnalysis:
        user_prompt = ANALYSIS_USER_PROMPT.format(
            index=section.index + 1,
            total=total_sections,
            position=section.position_in_book,
            title=section.title,
            text=section.text[:8000],  # Limit to avoid token overflow
        )

        response = await self._client.messages.create(
            model=self._model,
            max_tokens=1024,
            system=ANALYSIS_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )

        raw = response.content[0].text
        data = json.loads(raw)

        return TextAnalysis(
            section=section,
            mood=data["mood"],
            themes=data.get("themes", []),
            setting=data.get("setting", ""),
            emotional_tone=data.get("emotional_tone", ""),
            pacing=_parse_pacing(data.get("pacing", "moderate")),
            intensity=float(data.get("intensity", 0.5)),
            atmosphere=data.get("atmosphere", ""),
            key_emotions=data.get("key_emotions", []),
            suggested_genre_hints=data.get("suggested_genre_hints", []),
        )


class GeminiAnalyzer:
    """Analyze book sections using Google Gemini via AI Studio API key."""

    def __init__(self, settings: Settings) -> None:
        self._client = genai.Client(api_key=settings.gemini_api_key)
        self._model = settings.gemini_model

    async def analyze(
        self, section: BookSection, total_sections: int
    ) -> TextAnalysis:
        user_prompt = ANALYSIS_USER_PROMPT.format(
            index=section.index + 1,
            total=total_sections,
            position=section.position_in_book,
            title=section.title,
            text=section.text[:8000],
        )

        full_prompt = f"{ANALYSIS_SYSTEM_PROMPT}\n\n{user_prompt}"

        response = await self._client.aio.models.generate_content(
            model=self._model,
            contents=full_prompt,
            config=genai_types.GenerateContentConfig(
                response_mime_type="application/json",
            ),
        )

        data = json.loads(response.text)

        return TextAnalysis(
            section=section,
            mood=data["mood"],
            themes=data.get("themes", []),
            setting=data.get("setting", ""),
            emotional_tone=data.get("emotional_tone", ""),
            pacing=_parse_pacing(data.get("pacing", "moderate")),
            intensity=float(data.get("intensity", 0.5)),
            atmosphere=data.get("atmosphere", ""),
            key_emotions=data.get("key_emotions", []),
            suggested_genre_hints=data.get("suggested_genre_hints", []),
        )


def create_analyzer(settings: Settings) -> TextAnalyzerProtocol:
    """Factory: create the appropriate analyzer based on settings."""
    if settings.llm_provider == "claude":
        return ClaudeAnalyzer(settings)
    if settings.llm_provider == "gemini":
        return GeminiAnalyzer(settings)
    raise ValueError(f"Unsupported LLM provider: {settings.llm_provider}")
