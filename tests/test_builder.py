"""Tests for the prompt builder."""

from background_audio.analysis.models import BookSection, Pacing, TextAnalysis
from background_audio.prompts.builder import build_prompt


def _make_analysis(**kwargs) -> TextAnalysis:
    defaults = {
        "section": BookSection(index=0, title="Test", text="...", word_count=100, position_in_book=0.0),
        "mood": "tense",
        "themes": ["danger"],
        "setting": "dark forest at night",
        "emotional_tone": "foreboding",
        "pacing": Pacing.MODERATE,
        "intensity": 0.6,
        "atmosphere": "dark",
        "key_emotions": ["fear"],
        "suggested_genre_hints": ["cinematic"],
    }
    defaults.update(kwargs)
    return TextAnalysis(**defaults)


def test_basic_prompt_generation() -> None:
    analysis = _make_analysis()
    prompt = build_prompt(analysis)
    assert "tense mood" in prompt.prompt_text
    assert "seamless loop" in prompt.prompt_text
    assert "background music" in prompt.prompt_text
    assert prompt.section_index == 0
    assert prompt.section_title == "Test"


def test_negative_prompt_always_excludes_vocals() -> None:
    analysis = _make_analysis()
    prompt = build_prompt(analysis)
    assert "vocals" in prompt.negative_prompt
    assert "singing" in prompt.negative_prompt


def test_slow_pacing_bpm_range() -> None:
    analysis = _make_analysis(pacing=Pacing.SLOW)
    prompt = build_prompt(analysis, seed=42)
    assert 60 <= prompt.bpm <= 80


def test_fast_pacing_bpm_range() -> None:
    analysis = _make_analysis(pacing=Pacing.FAST)
    prompt = build_prompt(analysis, seed=42)
    assert 125 <= prompt.bpm <= 155


def test_seed_reproducibility() -> None:
    analysis = _make_analysis()
    p1 = build_prompt(analysis, seed=123)
    p2 = build_prompt(analysis, seed=123)
    assert p1.bpm == p2.bpm
    assert p1.prompt_text == p2.prompt_text


def test_low_intensity_negative_prompt() -> None:
    analysis = _make_analysis(intensity=0.1)
    prompt = build_prompt(analysis)
    assert "loud" in prompt.negative_prompt or "distorted" in prompt.negative_prompt


def test_peaceful_mood_negative_prompt() -> None:
    analysis = _make_analysis(mood="peaceful")
    prompt = build_prompt(analysis)
    assert "dissonant" in prompt.negative_prompt


def test_model_passthrough() -> None:
    analysis = _make_analysis()
    prompt = build_prompt(analysis, model="lyria-3-clip-preview")
    assert prompt.model == "lyria-3-clip-preview"


def test_analysis_summary_included() -> None:
    analysis = _make_analysis(mood="joyful", intensity=0.8)
    prompt = build_prompt(analysis)
    assert "joyful" in prompt.analysis_summary
    assert "0.8" in prompt.analysis_summary
