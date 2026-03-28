from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Pacing(str, Enum):
    SLOW = "slow"
    MODERATE = "moderate"
    FAST = "fast"


@dataclass
class BookSection:
    index: int
    title: str
    text: str
    word_count: int
    position_in_book: float  # 0.0 to 1.0


@dataclass
class TextAnalysis:
    section: BookSection
    mood: str
    themes: list[str]
    setting: str
    emotional_tone: str
    pacing: Pacing
    intensity: float  # 0.0 to 1.0
    atmosphere: str
    key_emotions: list[str] = field(default_factory=list)
    suggested_genre_hints: list[str] = field(default_factory=list)
