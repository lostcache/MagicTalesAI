"""CLI entry point for MagicTales Background Audio."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Annotated, Optional

import typer
from rich.console import Console

from background_audio.config import load_settings
from background_audio.reader import read_book, SUPPORTED_EXTENSIONS

app = typer.Typer(
    name="magictales",
    help="Generate musical loops from book text using Google Lyria.",
)
console = Console()

_FILE_HELP = f"Path to book file ({', '.join(sorted(SUPPORTED_EXTENSIONS))})"


@app.command()
def generate(
    input_file: Annotated[Path, typer.Argument(help=_FILE_HELP)],
    book_name: Annotated[str, typer.Option(help="Name for output organization")] = "book",
    output_dir: Annotated[Optional[Path], typer.Option(help="Output directory")] = None,
    project: Annotated[Optional[str], typer.Option(help="GCP project ID")] = None,
    model: Annotated[Optional[str], typer.Option(help="Lyria model")] = None,
    no_review: Annotated[bool, typer.Option(help="Skip interactive prompt review")] = False,
    seed: Annotated[Optional[int], typer.Option(help="Seed for reproducibility")] = None,
) -> None:
    """Full pipeline: book file → analysis → prompts → audio files."""
    from background_audio.pipeline import run_pipeline

    text = read_book(input_file)
    settings = load_settings(
        gcp_project=project,
        output_dir=output_dir,
        lyria_model=model,
    )

    result_path = asyncio.run(
        run_pipeline(text, settings, book_name=book_name, review=not no_review, seed=seed)
    )
    console.print(f"\n[bold green]Done![/bold green] Output: {result_path}")


@app.command()
def analyze(
    input_file: Annotated[Path, typer.Argument(help=_FILE_HELP)],
    output_file: Annotated[Optional[Path], typer.Option("-o", help="Save JSON output")] = None,
    project: Annotated[Optional[str], typer.Option(help="GCP project ID")] = None,
) -> None:
    """Analyze book and output structured JSON (no audio generation)."""
    from background_audio.analysis.analyzer import create_analyzer
    from background_audio.analysis.chunker import chunk_text

    text = read_book(input_file)
    settings = load_settings(gcp_project=project)

    sections = chunk_text(text, settings.min_section_words, settings.max_section_words)
    analyzer = create_analyzer(settings)

    async def _run() -> list[dict]:
        results = []
        for section in sections:
            analysis = await analyzer.analyze(section, total_sections=len(sections))
            results.append({
                "section_index": analysis.section.index,
                "section_title": analysis.section.title,
                "mood": analysis.mood,
                "themes": analysis.themes,
                "setting": analysis.setting,
                "emotional_tone": analysis.emotional_tone,
                "pacing": analysis.pacing.value,
                "intensity": analysis.intensity,
                "atmosphere": analysis.atmosphere,
                "key_emotions": analysis.key_emotions,
                "suggested_genre_hints": analysis.suggested_genre_hints,
            })
        return results

    results = asyncio.run(_run())
    output = json.dumps(results, indent=2)

    if output_file:
        output_file.write_text(output)
        console.print(f"Analysis saved to [green]{output_file}[/green]")
    else:
        console.print(output)


@app.command(name="preview-prompts")
def preview_prompts(
    input_file: Annotated[Path, typer.Argument(help=_FILE_HELP)],
    project: Annotated[Optional[str], typer.Option(help="GCP project ID")] = None,
    model: Annotated[Optional[str], typer.Option(help="Lyria model")] = None,
    seed: Annotated[Optional[int], typer.Option(help="Seed for reproducibility")] = None,
) -> None:
    """Analyze book and show generated Lyria prompts (no audio generation)."""
    from rich.panel import Panel

    from background_audio.analysis.analyzer import create_analyzer
    from background_audio.analysis.chunker import chunk_text
    from background_audio.prompts.builder import build_prompt

    text = read_book(input_file)
    settings = load_settings(gcp_project=project, lyria_model=model)
    sections = chunk_text(text, settings.min_section_words, settings.max_section_words)
    analyzer = create_analyzer(settings)

    async def _run() -> None:
        for section in sections:
            analysis = await analyzer.analyze(section, total_sections=len(sections))
            prompt = build_prompt(analysis, seed=seed, model=settings.lyria_model)
            panel = Panel(
                f"[bold]Prompt:[/bold] {prompt.prompt_text}\n\n"
                f"[bold]Negative:[/bold] {prompt.negative_prompt}\n\n"
                f"[bold]BPM:[/bold] {prompt.bpm}  |  {prompt.analysis_summary}",
                title=f"Section {prompt.section_index}: \"{prompt.section_title}\"",
                border_style="cyan",
            )
            console.print(panel)

    asyncio.run(_run())


@app.command(name="generate-from-prompts")
def generate_from_prompts(
    prompts_file: Annotated[Path, typer.Argument(help="Path to prompts JSON file")],
    output_dir: Annotated[Optional[Path], typer.Option(help="Output directory")] = None,
    book_name: Annotated[str, typer.Option(help="Name for output organization")] = "book",
    project: Annotated[Optional[str], typer.Option(help="GCP project ID")] = None,
    model: Annotated[Optional[str], typer.Option(help="Lyria model")] = None,
) -> None:
    """Generate audio from a manually edited prompts JSON file."""
    from rich.progress import Progress, SpinnerColumn, TextColumn

    from background_audio.audio.lyria_client import create_lyria_client
    from background_audio.audio.storage import save_results
    from background_audio.prompts.models import MusicPrompt

    settings = load_settings(gcp_project=project, output_dir=output_dir, lyria_model=model)
    data = json.loads(prompts_file.read_text())

    prompts = [
        MusicPrompt(
            section_index=p["section_index"],
            section_title=p["section_title"],
            prompt_text=p["prompt_text"],
            negative_prompt=p.get("negative_prompt", ""),
            bpm=p.get("bpm", 100),
            seed=p.get("seed"),
            model=settings.lyria_model,
        )
        for p in data
    ]

    lyria = create_lyria_client(settings)

    async def _run() -> Path:
        results = []
        with Progress(
            SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console
        ) as progress:
            task = progress.add_task("Generating audio...", total=len(prompts))
            for prompt in prompts:
                result = await lyria.generate(prompt)
                results.append(result)
                progress.advance(task)
        return save_results(results, settings.output_dir, book_name)

    result_path = asyncio.run(_run())
    console.print(f"\n[bold green]Done![/bold green] Output: {result_path}")


@app.command(name="cache")
def cache_clear() -> None:
    """Clear the cache."""
    from background_audio.cache import Cache

    settings = load_settings()
    c = Cache(settings.cache_dir, settings.cache_enabled)
    count = c.clear()
    console.print(f"Cleared [cyan]{count}[/cyan] cached files.")


if __name__ == "__main__":
    app()
