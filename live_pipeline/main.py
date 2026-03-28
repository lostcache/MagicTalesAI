import asyncio
import os

from dotenv import load_dotenv
from google import genai
from google.genai import types

from .audio_handler import AudioHandler
from .elevenlabs_manager import ElevenLabsManager
from .story_controller import StoryController, StoryState

load_dotenv()


async def run_story_narration(
    story_controller: StoryController,
    elevenlabs: ElevenLabsManager,
    story_script: list,
):
    """Main storyteller loop: ElevenLabs lines with retry after QA (same line)."""
    print("\n[STORY] Audiobook starting in 3 seconds...")
    await asyncio.sleep(3)

    for line in story_script:
        character = line["character"]
        text = line["text"]

        while True:
            if story_controller.state != StoryState.PLAYING_NARRATION:
                print("[STORY] Narration paused. Waiting for QA to finish...")
                await story_controller.wait_for_narration_resume()
                print("[STORY] Resuming story. Repeating interrupted line...")

            await elevenlabs.stream_character_line(text, character=character)

            if story_controller.state == StoryState.PLAYING_NARRATION:
                await asyncio.sleep(0.8)
                break
            print(f"[STORY] Line interrupted mid-way: {text[:15]}...")

    print("\n[STORY] The end of the story!")


async def run_qa_session(
    audio_handler: AudioHandler,
    story_controller: StoryController,
    story_script: list,
):
    """Background daemon: listen and answer via Gemini Live API with story context."""
    client = genai.Client()

    full_story_text = " ".join([line["text"] for line in story_script])

    system_prompt = f"""You are a friendly, patient AI reading companion for a child.
The child is currently listening to this story:
<story_context>
{full_story_text}
</story_context>

Rules for answering questions:
1. If the child asks about the plot or characters, answer based on the <story_context>.
2. If the child asks a real-world factual question (e.g., "Are dragons real?"), you MUST use the Google Search tool to find facts.
3. Keep your answers very short, simple, and engaging (1-2 sentences).
4. Do not continue reading the story; your job is only to answer the interruption.
"""

    config = types.LiveConnectConfig(
        system_instruction=types.Content(
            parts=[types.Part.from_text(text=system_prompt)]
        ),
        tools=[{"google_search": {}}],
    )

    try:
        async with client.aio.live.connect(
            model="gemini-2.0-flash-exp", config=config
        ) as session:
            story_controller.gemini = session
            print("[QA DAEMON] 🧠 Context injected. Listening for questions...")

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
                            if part.inline_data and part.inline_data.data:
                                audio_handler.play_audio(part.inline_data.data)

                    if server_content.turn_complete:
                        await story_controller.on_question_answered()

            await asyncio.gather(send_mic_audio(), receive_api_response())

    except asyncio.CancelledError:
        pass
    except Exception as e:
        print(f"[QA DAEMON] Connection failed: {e}")


async def main():
    if not os.getenv("GOOGLE_API_KEY") and not os.getenv("GEMINI_API_KEY"):
        raise RuntimeError(
            "GOOGLE_API_KEY (or GEMINI_API_KEY) is not set. "
            "Add it to your .env file or environment."
        )
    if not os.getenv("ELEVENLABS_API_KEY"):
        raise RuntimeError(
            "ELEVENLABS_API_KEY is not set. Add it to your .env file or environment."
        )

    audio_handler = AudioHandler()
    story_controller = StoryController(audio_handler, None)
    elevenlabs_manager = ElevenLabsManager(audio_handler, story_controller)

    story_script = [
        {
            "character": "narrator",
            "text": (
                "Deep in a valley hidden behind the clouds, "
                "there lived a little dragon named Sparky."
            ),
        },
        {
            "character": "dragon",
            "text": (
                "I wish I could breathe real fire instead of this pink glitter!"
            ),
        },
        {
            "character": "narrator",
            "text": "One sunny morning, Sparky decided to visit the wise old owl.",
        },
    ]

    print("[SYSTEM] Booting up MagicTales-AI Core Pipeline...")

    qa_task = asyncio.create_task(
        run_qa_session(audio_handler, story_controller, story_script)
    )
    story_task = asyncio.create_task(
        run_story_narration(story_controller, elevenlabs_manager, story_script)
    )

    try:
        await story_task
    except KeyboardInterrupt:
        print("\n[SYSTEM] Manual override shutting down...")
    finally:
        qa_task.cancel()
        try:
            await qa_task
        except asyncio.CancelledError:
            pass
        audio_handler.close()
        print("[SYSTEM] Offline.")
