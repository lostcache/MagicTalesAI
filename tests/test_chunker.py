"""Tests for the text chunker."""

from background_audio.analysis.chunker import chunk_text


def test_chunk_by_chapters(sample_chapter_text: str) -> None:
    sections = chunk_text(sample_chapter_text, min_words=50, max_words=3000)
    assert len(sections) == 3
    assert sections[0].title == "Chapter 1: The Storm Approaches"
    assert sections[1].title == "Chapter 2: Safe Harbor"
    assert sections[2].title == "Chapter 3: New Beginnings"


def test_section_positions(sample_chapter_text: str) -> None:
    sections = chunk_text(sample_chapter_text, min_words=50, max_words=3000)
    assert sections[0].position_in_book == 0.0
    assert sections[1].position_in_book == 0.5
    assert sections[2].position_in_book == 1.0


def test_section_word_counts(sample_chapter_text: str) -> None:
    sections = chunk_text(sample_chapter_text, min_words=50, max_words=3000)
    for section in sections:
        assert section.word_count > 0
        assert section.word_count == len(section.text.split())


def test_short_text_single_section(short_text: str) -> None:
    sections = chunk_text(short_text, min_words=5, max_words=3000)
    assert len(sections) == 1
    assert sections[0].title == "Full Text"


def test_empty_text() -> None:
    sections = chunk_text("")
    assert sections == []


def test_paragraph_fallback(no_chapter_text: str) -> None:
    # Force paragraph splitting by using a small max_words
    sections = chunk_text(no_chapter_text, min_words=50, max_words=100)
    assert len(sections) >= 2
    for section in sections:
        assert section.word_count > 0


def test_merge_small_sections() -> None:
    text = """\
Chapter 1: Very Short

Hello.

Chapter 2: Also Short

World.

Chapter 3: Longer Section

This section has enough words to stand on its own and should not be merged
with anything else because it is above the minimum word count threshold that
we have set for our chunker to respect when splitting text into sections.
"""
    sections = chunk_text(text, min_words=20, max_words=3000)
    # Chapters 1 and 2 are tiny and should get merged
    assert len(sections) < 3


def test_section_indices_sequential(sample_chapter_text: str) -> None:
    sections = chunk_text(sample_chapter_text, min_words=50, max_words=3000)
    for i, section in enumerate(sections):
        assert section.index == i
