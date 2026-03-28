"""Microphone capture and speaker playback for the live pipeline."""

from collections.abc import AsyncIterator


class AudioHandler:
    """PyAudio-backed I/O; implement `get_mic_stream` / `play_audio` for your platform."""

    def __init__(self) -> None:
        self._closed = False

    async def get_mic_stream(self) -> AsyncIterator[bytes]:
        """Yield PCM chunks (e.g. 16 kHz mono) for Gemini Live."""
        raise NotImplementedError(
            "Implement mic capture (e.g. PyAudio) and yield PCM bytes."
        )
        yield b""  # pragma: no cover — makes this an async generator

    def play_audio(self, data: bytes) -> None:
        """Play Gemini reply audio (encoding depends on model output)."""
        raise NotImplementedError("Implement speaker output for Gemini audio chunks.")

    def close(self) -> None:
        self._closed = True
