"""Shared Gemini Multimodal Live QA loop (CLI PyAudio or browser WebSocket audio)."""

import asyncio
import logging
import os

from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

logger = logging.getLogger(__name__)

# Must be a model that supports Live bidiGenerateContent (not gemini-2.0-flash-exp).
# Override with GEMINI_LIVE_MODEL if needed.
LIVE_MODEL = os.getenv(
    "GEMINI_LIVE_MODEL",
    "gemini-2.5-flash-native-audio-preview-12-2025",
)


async def run_gemini_live_qa(audio_handler, story_controller, story_script: list) -> None:
    """Stream mic chunks in, model audio out; story context in system instruction."""
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        logger.error("GOOGLE_API_KEY is not set; Gemini Live cannot start.")
        raise RuntimeError("GOOGLE_API_KEY is not set")

    client = genai.Client(api_key=api_key)

    full_story_text = " ".join([line["text"] for line in story_script])

    system_prompt = f"""You are a friendly, patient AI reading companion for a child.
The child may be listening to this story (same session can include audiobook playback):
<story_context>
{full_story_text}
</story_context>

Behavior (critical):
1. Stay completely silent until the child speaks. Do not greet, narrate, or read the story unprompted.
2. When the child speaks, treat it as a question or interruption: stop any reply you were giving and listen. Answer only what they asked.
3. Story questions: answer from <story_context> only.
4. Real-world factual questions (animals, science, "is X real?", etc.): you MUST use the Google Search tool and base your answer on what you find.
5. Replies must be very short (1–2 sentences), simple, and child-friendly. Then go silent and wait for their next question — do not ramble or continue the story.
"""

    # Without AUDIO, the model may return text only — the browser plays PCM from inline_data.
    # START_OF_ACTIVITY_INTERRUPTS: when the child starts speaking, the model stops generating audio and listens.
    config = types.LiveConnectConfig(
        response_modalities=[types.Modality.AUDIO],
        realtime_input_config=types.RealtimeInputConfig(
            activity_handling=types.ActivityHandling.START_OF_ACTIVITY_INTERRUPTS,
            automatic_activity_detection=types.AutomaticActivityDetection(
                disabled=False,
                start_of_speech_sensitivity=types.StartSensitivity.START_SENSITIVITY_HIGH,
                end_of_speech_sensitivity=types.EndSensitivity.END_SENSITIVITY_HIGH,
                prefix_padding_ms=120,
                silence_duration_ms=400,
            ),
        ),
        system_instruction=types.Content(
            parts=[types.Part.from_text(text=system_prompt)]
        ),
        tools=[types.Tool(google_search=types.GoogleSearch())],
    )

    try:
        async with client.aio.live.connect(model=LIVE_MODEL, config=config) as session:
            story_controller.gemini = session
            logger.info("Gemini Live connected (model=%s); context injected.", LIVE_MODEL)

            async def send_mic_audio():
                async for mic_data in audio_handler.get_mic_stream():
                    await session.send(
                        input=types.LiveClientRealtimeInput(
                            media_chunks=[
                                types.Blob(
                                    data=mic_data, mime_type="audio/pcm;rate=16000"
                                )
                            ]
                        )
                    )

            async def receive_api_response():
                async for response in session.receive():
                    server_content = response.server_content
                    if not server_content:
                        continue

                    if server_content.interrupted:
                        await story_controller.trigger_barge_in()
                        continue

                    model_turn = server_content.model_turn
                    if model_turn:
                        await story_controller.enter_answering()
                        for part in model_turn.parts:
                            if part.text:
                                logger.debug("Live model text: %s", part.text[:500])
                            if part.inline_data and part.inline_data.data:
                                mime = getattr(part.inline_data, "mime_type", None)
                                logger.debug(
                                    "Live audio chunk: mime=%s bytes=%s",
                                    mime,
                                    len(part.inline_data.data),
                                )
                                await audio_handler.play_audio(part.inline_data.data)

                    if server_content.turn_complete:
                        await story_controller.on_question_answered()

            await asyncio.gather(send_mic_audio(), receive_api_response())

    except asyncio.CancelledError:
        raise
    except Exception as e:
        logger.exception("Gemini Live session error: %s", e)
    finally:
        end = getattr(audio_handler, "signal_mic_end", None)
        if callable(end):
            await end()
