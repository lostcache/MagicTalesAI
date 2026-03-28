"""Save generated audio files and metadata."""

from __future__ import annotations

import json
import re
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from background_audio.audio.models import GenerationResult


def _sanitize_filename(name: str) -> str:
    """Convert a title to a safe filename."""
    name = re.sub(r"[^\w\s-]", "", name)
    name = re.sub(r"\s+", "_", name.strip())
    return name.lower()[:60]


def save_results(
    results: list[GenerationResult],
    output_dir: Path,
    book_name: str = "book",
) -> Path:
    """Save audio files and metadata to output_dir/book_name/."""
    book_dir = output_dir / _sanitize_filename(book_name)
    book_dir.mkdir(parents=True, exist_ok=True)

    metadata_entries = []

    for result in results:
        ext = "mp3" if "mpeg" in result.mime_type else "wav"
        filename = f"{result.section_index:02d}_{_sanitize_filename(result.section_title)}.{ext}"
        filepath = book_dir / filename
        filepath.write_bytes(result.audio_bytes)

        metadata_entries.append({
            "section_index": result.section_index,
            "section_title": result.section_title,
            "filename": filename,
            "model_used": result.model_used,
            "duration_seconds": result.duration_seconds,
            "prompt_text": result.prompt_used.prompt_text,
            "negative_prompt": result.prompt_used.negative_prompt,
            "bpm": result.prompt_used.bpm,
            "analysis_summary": result.prompt_used.analysis_summary,
            "generated_at": result.generated_at.isoformat(),
        })

    # Write metadata
    metadata_path = book_dir / "metadata.json"
    metadata = {
        "book_name": book_name,
        "total_sections": len(results),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "sections": metadata_entries,
    }
    metadata_path.write_text(json.dumps(metadata, indent=2))

    return book_dir
