"""Convert TextAnalysis into Lyria-optimized MusicPrompt."""

from __future__ import annotations

import random

from background_audio.analysis.models import Pacing, TextAnalysis
from background_audio.prompts.models import MusicPrompt

# --- Mapping tables ---

MOOD_TO_GENRE: dict[str, str] = {
    "melancholic": "ambient orchestral",
    "tense": "dark cinematic",
    "joyful": "upbeat acoustic",
    "mysterious": "ethereal electronic",
    "romantic": "warm strings and piano",
    "epic": "cinematic orchestral",
    "peaceful": "gentle ambient",
    "dark": "dark atmospheric",
    "whimsical": "playful folk",
    "nostalgic": "warm lo-fi",
    "triumphant": "epic orchestral",
    "somber": "slow strings",
    "eerie": "dark ambient",
    "hopeful": "uplifting acoustic",
    "angry": "intense percussion-driven",
    "serene": "calm ambient pads",
    "adventurous": "cinematic adventure",
    "dreamy": "ambient shoegaze",
    "suspenseful": "tension-building cinematic",
    "playful": "light jazz",
}

PACING_TO_BPM: dict[Pacing, tuple[int, int]] = {
    Pacing.SLOW: (60, 80),
    Pacing.MODERATE: (90, 120),
    Pacing.FAST: (125, 155),
}

ATMOSPHERE_TO_INSTRUMENTS: dict[str, str] = {
    "ethereal": "synthesizer pads, reverb-heavy piano, distant choir",
    "oppressive": "low brass, deep cello drones, timpani",
    "pastoral": "acoustic guitar, flute, light strings",
    "urban": "electric piano, muted trumpet, subtle beat",
    "mystical": "harp, celesta, string tremolo",
    "industrial": "metallic percussion, distorted bass, synth leads",
    "intimate": "solo piano, soft strings, acoustic guitar",
    "grand": "full orchestra, brass fanfare, choir",
    "haunting": "solo violin, music box, reverb piano",
    "warm": "acoustic guitar, soft piano, gentle strings",
    "cold": "glass-like synths, sparse piano, frozen pads",
    "chaotic": "dissonant strings, layered percussion, staccato brass",
    "dreamy": "ambient pads, arpeggiated synths, soft harp",
    "dark": "low cello, dark synth pads, sparse percussion",
    "bright": "bright piano, flute, plucked strings",
}

BASE_NEGATIVE_PROMPT = "vocals, singing, spoken word, lyrics, voice"


def _fuzzy_lookup(value: str, table: dict[str, str], default: str) -> str:
    """Look up a value in a table, falling back to substring match then default."""
    value_lower = value.lower()
    if value_lower in table:
        return table[value_lower]
    for key, result in table.items():
        if key in value_lower or value_lower in key:
            return result
    return default


def _intensity_to_dynamics(intensity: float) -> str:
    if intensity < 0.3:
        return "soft, delicate"
    if intensity < 0.7:
        return "moderate dynamics"
    return "powerful, building"


def build_prompt(analysis: TextAnalysis, seed: int | None = None, model: str = "lyria-002") -> MusicPrompt:
    """Build a MusicPrompt from a TextAnalysis."""
    genre = _fuzzy_lookup(analysis.mood, MOOD_TO_GENRE, "cinematic ambient")
    instrumentation = _fuzzy_lookup(
        analysis.atmosphere, ATMOSPHERE_TO_INSTRUMENTS, "piano, strings, subtle synths"
    )
    dynamics = _intensity_to_dynamics(analysis.intensity)

    bpm_range = PACING_TO_BPM.get(analysis.pacing, (90, 120))
    rng = random.Random(seed) if seed is not None else random.Random()
    bpm = rng.randint(bpm_range[0], bpm_range[1])

    # Assemble prompt parts
    parts = [
        genre,
        f"{analysis.mood} mood",
        instrumentation,
        f"{bpm} BPM",
        f"{dynamics} dynamics",
        f"{analysis.atmosphere} atmosphere",
    ]
    # Add LLM genre hints that aren't already covered
    for hint in analysis.suggested_genre_hints:
        if hint.lower() not in genre.lower():
            parts.append(hint)

    prompt_text = ", ".join(parts) + ", seamless loop, background music"

    # Build negative prompt
    negative_parts = [BASE_NEGATIVE_PROMPT]
    if analysis.pacing == Pacing.SLOW:
        negative_parts.append("fast tempo, aggressive drums, heavy bass")
    if analysis.intensity < 0.3:
        negative_parts.append("loud, distorted, harsh")
    if "peaceful" in analysis.mood.lower() or "gentle" in analysis.mood.lower():
        negative_parts.append("dissonant, chaotic, percussion-heavy")

    negative_prompt = ", ".join(negative_parts)

    summary = (
        f"Mood: {analysis.mood} | Pacing: {analysis.pacing.value} | "
        f"Intensity: {analysis.intensity:.1f} | Atmosphere: {analysis.atmosphere}"
    )

    return MusicPrompt(
        section_index=analysis.section.index,
        section_title=analysis.section.title,
        prompt_text=prompt_text,
        negative_prompt=negative_prompt,
        bpm=bpm,
        seed=seed,
        model=model,
        analysis_summary=summary,
    )
