"""Split book text into meaningful sections for analysis."""

from __future__ import annotations

import re

from background_audio.analysis.models import BookSection


# Patterns that indicate chapter/section boundaries (ordered by priority)
_CHAPTER_PATTERNS = [
    re.compile(r"^(?:CHAPTER|Chapter)\s+\w+.*$", re.MULTILINE),
    re.compile(r"^(?:PART|Part)\s+\w+.*$", re.MULTILINE),
    re.compile(r"^#{1,3}\s+.+", re.MULTILINE),  # Markdown headings
    re.compile(r"^\*\s*\*\s*\*\s*$", re.MULTILINE),  # Scene break markers
    re.compile(r"^-{3,}\s*$", re.MULTILINE),  # Horizontal rules
]


def chunk_text(
    text: str,
    min_words: int = 200,
    max_words: int = 3000,
) -> list[BookSection]:
    """Split book text into sections.

    Strategy:
    1. Try to split on chapter/heading markers.
    2. Fall back to paragraph-boundary splitting at max_words.
    3. Merge tiny sections into their predecessor.
    """
    text = text.strip()
    if not text:
        return []

    # Try structured splitting first
    sections = _split_on_markers(text)

    # If no markers found and text is long enough to split, use paragraph-based splitting
    if len(sections) <= 1 and len(text.split()) > max_words:
        sections = _split_on_paragraphs(text, max_words)

    # Merge tiny sections
    sections = _merge_small_sections(sections, min_words)

    # Build BookSection objects
    total = len(sections)
    results: list[BookSection] = []
    for i, (title, body) in enumerate(sections):
        word_count = len(body.split())
        if word_count == 0:
            continue
        results.append(
            BookSection(
                index=i,
                title=title,
                text=body,
                word_count=word_count,
                position_in_book=i / max(total - 1, 1),
            )
        )
    return results


def _split_on_markers(text: str) -> list[tuple[str, str]]:
    """Try each chapter pattern; use the first one that produces multiple splits."""
    for pattern in _CHAPTER_PATTERNS:
        matches = list(pattern.finditer(text))
        if len(matches) < 2:
            continue

        sections: list[tuple[str, str]] = []

        # Text before first marker (if any)
        pre = text[: matches[0].start()].strip()
        if pre:
            sections.append(("Prologue", pre))

        for j, match in enumerate(matches):
            title = match.group().lstrip("#").strip()
            start = match.end()
            end = matches[j + 1].start() if j + 1 < len(matches) else len(text)
            body = text[start:end].strip()
            if body:
                sections.append((title, body))

        return sections

    # No pattern matched
    return [("Full Text", text)]


def _split_on_paragraphs(text: str, max_words: int) -> list[tuple[str, str]]:
    """Split text at paragraph boundaries, targeting max_words per section."""
    paragraphs = re.split(r"\n\s*\n", text)
    sections: list[tuple[str, str]] = []
    current_paragraphs: list[str] = []
    current_words = 0

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        para_words = len(para.split())

        if current_words + para_words > max_words and current_paragraphs:
            idx = len(sections) + 1
            sections.append((f"Section {idx}", "\n\n".join(current_paragraphs)))
            current_paragraphs = [para]
            current_words = para_words
        else:
            current_paragraphs.append(para)
            current_words += para_words

    if current_paragraphs:
        idx = len(sections) + 1
        sections.append((f"Section {idx}", "\n\n".join(current_paragraphs)))

    return sections


def _merge_small_sections(
    sections: list[tuple[str, str]], min_words: int
) -> list[tuple[str, str]]:
    """Merge sections smaller than min_words into the previous section."""
    if not sections:
        return sections

    merged: list[tuple[str, str]] = [sections[0]]

    for title, body in sections[1:]:
        word_count = len(body.split())
        if word_count < min_words and merged:
            prev_title, prev_body = merged[-1]
            merged[-1] = (prev_title, prev_body + "\n\n" + body)
        else:
            merged.append((title, body))

    return merged
