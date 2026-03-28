"""Extract plain text from any supported file format."""

from __future__ import annotations

from pathlib import Path


SUPPORTED_EXTENSIONS = {".txt", ".md", ".pdf", ".epub", ".docx"}


def read_book(path: Path) -> str:
    """Read a book file and return its plain text content."""
    suffix = path.suffix.lower()

    if suffix in (".txt", ".md"):
        return path.read_text(encoding="utf-8")

    if suffix == ".pdf":
        return _read_pdf(path)

    if suffix == ".epub":
        return _read_epub(path)

    if suffix == ".docx":
        return _read_docx(path)

    raise ValueError(
        f"Unsupported file type: '{suffix}'. "
        f"Supported formats: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
    )


def _read_pdf(path: Path) -> str:
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    pages = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            pages.append(text)
    return "\n\n".join(pages)


def _read_epub(path: Path) -> str:
    import ebooklib
    from ebooklib import epub
    from bs4 import BeautifulSoup

    book = epub.read_epub(str(path), options={"ignore_ncx": True})
    chapters = []

    for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
        soup = BeautifulSoup(item.get_content(), "html.parser")
        text = soup.get_text(separator="\n")
        text = text.strip()
        if text:
            chapters.append(text)

    return "\n\n".join(chapters)


def _read_docx(path: Path) -> str:
    from docx import Document

    doc = Document(str(path))
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    return "\n\n".join(paragraphs)
