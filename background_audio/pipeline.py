"""Orchestrator: ties text analysis, prompt building, and audio generation together."""

from __future__ import annotations

import asyncio
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.progress import Progress, SpinnerColumn, TextColumn

from background_audio.analysis.analyzer import create_analyzer
from background_audio.analysis.chunker import chunk_text
from background_audio.analysis.models import TextAnalysis
from background_audio.audio.lyria_client import create_lyria_client
from background_audio.audio.models import GenerationResult
from background_audio.audio.storage import save_results
from background_audio.config import Settings
from background_audio.prompts.builder import build_prompt
from background_audio.prompts.models import MusicPrompt

console = Console()


async def run_pipeline(
    text: str,
    settings: Settings,
    book_name: str = "book",
    review: bool = True,
    seed: int | None = None,
) -> Path:
    """Run the full pipeline: text → sections → analysis → prompts → audio → files."""

    # Step 1: Chunk
    console.print("\n[bold]Step 1:[/bold] Splitting text into sections...")
    sections = chunk_text(
        text,
        min_words=settings.min_section_words,
        max_words=settings.max_section_words,
    )
    console.print(f"  Found [cyan]{len(sections)}[/cyan] sections.\n")

    if not sections:
        console.print("[red]No sections found in text. Aborting.[/red]")
        raise SystemExit(1)

    # Step 2: Analyze
    console.print("[bold]Step 2:[/bold] Analyzing text with LLM...")
    analyzer = create_analyzer(settings)
    analyses: list[TextAnalysis] = []

    with Progress(
        SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console
    ) as progress:
        task = progress.add_task("Analyzing sections...", total=len(sections))
        for section in sections:
            analysis = await analyzer.analyze(section, total_sections=len(sections))
            analyses.append(analysis)
            progress.advance(task)

    # Step 3: Build prompts
    console.print("\n[bold]Step 3:[/bold] Generating music prompts...")
    prompts: list[MusicPrompt] = []
    for analysis in analyses:
        prompt = build_prompt(analysis, seed=seed, model=settings.lyria_model)
        prompts.append(prompt)

    # Step 4: Interactive review
    if review:
        console.print("\n[bold]Step 4:[/bold] Review generated prompts\n")
        prompts = _interactive_review(prompts)
    else:
        console.print("\n[bold]Step 4:[/bold] Skipping review (--no-review)\n")

    if not prompts:
        console.print("[red]All prompts skipped. Nothing to generate.[/red]")
        raise SystemExit(1)

    # Step 5: Generate audio
    console.print(f"[bold]Step 5:[/bold] Generating audio for {len(prompts)} sections...")
    lyria = create_lyria_client(settings)
    results: list[GenerationResult] = []

    skipped = 0
    with Progress(
        SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console
    ) as progress:
        task = progress.add_task("Generating audio...", total=len(prompts))
        for prompt in prompts:
            result = await lyria.generate(prompt)
            if result is not None:
                results.append(result)
            else:
                skipped += 1
                console.print(
                    f"  [yellow]⚠ Skipped section {prompt.section_index} "
                    f"({prompt.section_title}) — no audio returned.[/yellow]"
                )
            progress.advance(task)

    if skipped:
        console.print(f"  [yellow]{skipped} section(s) skipped.[/yellow]")

    # Step 6: Save
    if not results:
        console.print("[red]No audio was generated. Check warnings above.[/red]")
        raise SystemExit(1)

    console.print("\n[bold]Step 6:[/bold] Saving audio files...")
    output_path = save_results(results, settings.output_dir, book_name)
    console.print(f"  Saved to [green]{output_path}[/green]\n")

    return output_path


def _interactive_review(prompts: list[MusicPrompt]) -> list[MusicPrompt]:
    """Let user review, edit, or skip each prompt."""
    reviewed: list[MusicPrompt] = []

    for prompt in prompts:
        panel = Panel(
            f"[bold]Prompt:[/bold] {prompt.prompt_text}\n\n"
            f"[bold]Negative:[/bold] {prompt.negative_prompt}\n\n"
            f"[bold]BPM:[/bold] {prompt.bpm}  |  {prompt.analysis_summary}",
            title=f"Section {prompt.section_index}: \"{prompt.section_title}\"",
            border_style="cyan",
        )
        console.print(panel)

        choice = Prompt.ask(
            "  [Enter] Accept  [e] Edit prompt  [s] Skip",
            default="",
        )

        if choice.lower() == "s":
            console.print("  [dim]Skipped.[/dim]\n")
            continue
        elif choice.lower() == "e":
            new_text = Prompt.ask("  New prompt text", default=prompt.prompt_text)
            prompt.prompt_text = new_text
            console.print("  [green]Updated.[/green]\n")

        reviewed.append(prompt)

    return reviewed
