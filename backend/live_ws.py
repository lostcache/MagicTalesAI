"""Browser microphone → Gemini Live → browser speaker (after uvicorn is running)."""

import asyncio
import logging
from typing import Any

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState

from .story_controller import StoryController

from .gemini_live_qa import run_gemini_live_qa
from .storage import load_extraction

logger = logging.getLogger(__name__)

router = APIRouter()

# Cap context size for Live system instruction (characters, not tokens)
MAX_CONTEXT_CHARS = 32000


def segments_to_story_script(segments: list) -> list[dict[str, str]]:
    script: list[dict[str, str]] = []
    for seg in segments:
        if seg.type == "narration":
            script.append({"character": "narrator", "text": seg.text})
        else:
            script.append({"character": seg.speaker, "text": seg.text})
    return script


def truncate_story_script(script: list[dict[str, str]], max_chars: int) -> list[dict[str, str]]:
    total = 0
    out: list[dict[str, str]] = []
    for line in script:
        t = line["text"]
        if total + len(t) > max_chars:
            remain = max_chars - total
            if remain > 200:
                out.append({**line, "text": t[:remain] + "…"})
            break
        out.append(line)
        total += len(t) + 1
    return out


class BrowserLiveAudio:
    """Mic from WebSocket binary PCM; model audio sent as binary PCM to the client."""

    def __init__(self, websocket: WebSocket) -> None:
        self._ws = websocket
        self._closed = False
        self._mic_queue: asyncio.Queue[bytes | None] = asyncio.Queue(maxsize=128)

    async def get_mic_stream(self):
        while not self._closed:
            data = await self._mic_queue.get()
            if data is None:
                break
            yield data

    async def play_audio(self, data: bytes) -> None:
        if not data or self._closed:
            return
        if self._ws.client_state != WebSocketState.CONNECTED:
            return
        await self._ws.send_bytes(data)

    async def signal_mic_end(self) -> None:
        self._closed = True
        try:
            await self._mic_queue.put(None)
        except Exception:
            pass

    def close(self) -> None:
        self._closed = True

    async def feed_pcm(self, data: bytes) -> None:
        if self._closed:
            return
        try:
            self._mic_queue.put_nowait(data)
        except asyncio.QueueFull:
            try:
                _ = self._mic_queue.get_nowait()
            except asyncio.QueueEmpty:
                pass
            try:
                self._mic_queue.put_nowait(data)
            except asyncio.QueueFull:
                pass


@router.websocket("/ws/stories/{story_id}/live")
async def story_live_websocket(websocket: WebSocket, story_id: str) -> None:
    await websocket.accept()
    audio = BrowserLiveAudio(websocket)
    story_controller = StoryController(audio, None)
    pump: asyncio.Task[Any] | None = None

    try:
        extraction = await load_extraction(story_id)
    except HTTPException:
        await websocket.close(code=4404)
        return

    script = segments_to_story_script(extraction.segments)
    script = truncate_story_script(script, MAX_CONTEXT_CHARS)

    async def pump_browser_mic() -> None:
        try:
            while True:
                data = await websocket.receive_bytes()
                await audio.feed_pcm(data)
        except WebSocketDisconnect:
            logger.info("Live WS: client disconnected (pump)")
        except Exception as e:
            logger.debug("Live WS pump end: %s", e)
        finally:
            await audio.signal_mic_end()

    try:
        pump = asyncio.create_task(pump_browser_mic())
        await run_gemini_live_qa(audio, story_controller, script)
    except asyncio.CancelledError:
        raise
    except Exception as e:
        logger.exception("Live WS session error: %s", e)
    finally:
        audio.close()
        if pump and not pump.done():
            pump.cancel()
            try:
                await pump
            except asyncio.CancelledError:
                pass
        try:
            if websocket.client_state == WebSocketState.CONNECTED:
                await websocket.close()
        except Exception:
            pass
