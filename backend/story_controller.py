import asyncio
from enum import Enum, auto
from typing import Any


class StoryState(Enum):
    PLAYING_NARRATION = auto()
    ANSWERING = auto()
    INTERRUPTED = auto()


class StoryController:
    """Coordinates Gemini Live QA state (barge-in, answering, back to listening)."""

    def __init__(self, audio_handler: Any, gemini: Any) -> None:
        self.audio_handler = audio_handler
        self.gemini = gemini
        self.state = StoryState.PLAYING_NARRATION
        self._narration_resumed = asyncio.Event()
        self._narration_resumed.set()

    async def wait_for_narration_resume(self) -> None:
        await self._narration_resumed.wait()

    async def trigger_barge_in(self) -> None:
        self.state = StoryState.INTERRUPTED
        self._narration_resumed.clear()

    async def enter_answering(self) -> None:
        self.state = StoryState.ANSWERING
        self._narration_resumed.clear()

    async def on_question_answered(self) -> None:
        self.state = StoryState.PLAYING_NARRATION
        self._narration_resumed.set()
