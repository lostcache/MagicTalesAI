"""ElevenLabs TTS streaming for story lines."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .audio_handler import AudioHandler
    from .story_controller import StoryController


class ElevenLabsManager:
    def __init__(
        self, audio_handler: "AudioHandler", story_controller: "StoryController"
    ) -> None:
        self.audio_handler = audio_handler
        self.story_controller = story_controller

    async def stream_character_line(self, text: str, character: str = "narrator") -> None:
        """Stream one line with a voice suited to `character`; block until finished."""
        raise NotImplementedError(
            "Implement ElevenLabs streaming (voice per character) and playback."
        )
