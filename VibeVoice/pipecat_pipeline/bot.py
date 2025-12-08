#
# Copyright (c) 2024–2025, Daily
#
# SPDX-License-Identifier: BSD 2-Clause License
#

import os

from dotenv import load_dotenv
from loguru import logger

from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.audio.vad.vad_analyzer import VADParams
from pipecat.frames.frames import LLMRunFrame
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext
from pipecat.runner.types import RunnerArguments
from pipecat.runner.utils import create_transport
from pipecat.services.google.gemini_live.llm import (
    GeminiLiveLLMService,
    GeminiModalities,
    InputParams,
)
from pipecat.transports.base_transport import BaseTransport, TransportParams
from pipecat.transports.daily.transport import DailyParams
from pipecat.transports.websocket.fastapi import FastAPIWebsocketParams

# Import custom Echo TTS service
from custom_echo_tts_service import EchoTTSService

# Load .env from current dir and parent dir
load_dotenv(override=True)
load_dotenv("../.env", override=True)

# Check for required API key early
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    raise ValueError(
        "GOOGLE_API_KEY environment variable is required!\n"
        "Set it with: export GOOGLE_API_KEY=your-key-here\n"
        "Or create a .env file with: GOOGLE_API_KEY=your-key-here"
    )

# System instruction for the bot
SYSTEM_INSTRUCTION = """You are a friendly AI assistant in a voice call. 
Your output will be spoken aloud with TTS, so keep responses natural and conversational.
Avoid special characters that can't easily be spoken, such as emojis or bullet points.
Respond to what the user said in a creative and helpful way.
Keep responses concise - around 1-2 sentences unless the user asks for more detail."""

# We store functions so objects (e.g. SileroVADAnalyzer) don't get
# instantiated. The function will be called when the desired transport gets
# selected.
transport_params = {
    "daily": lambda: DailyParams(
        audio_in_enabled=True,
        audio_out_enabled=True,
        vad_analyzer=SileroVADAnalyzer(params=VADParams(stop_secs=0.2)),
    ),
    "twilio": lambda: FastAPIWebsocketParams(
        audio_in_enabled=True,
        audio_out_enabled=True,
        vad_analyzer=SileroVADAnalyzer(params=VADParams(stop_secs=0.2)),
    ),
    "webrtc": lambda: TransportParams(
        audio_in_enabled=True,
        audio_out_enabled=True,
        vad_analyzer=SileroVADAnalyzer(params=VADParams(stop_secs=0.2)),
    ),
}


async def run_bot(transport: BaseTransport, runner_args: RunnerArguments):
    logger.info("Starting bot with GeminiLive STT/LLM + Echo TTS")

    # GeminiLive handles both STT and LLM in one service
    # Using TEXT modality means it outputs text (for TTS), not audio
    llm = GeminiLiveLLMService(
        api_key=GOOGLE_API_KEY,
        system_instruction=SYSTEM_INSTRUCTION,
        model=os.getenv("GEMINI_MODEL", "models/gemini-live-2.5-flash-preview"),
        params=InputParams(modalities=GeminiModalities.TEXT),
    )

    # Echo TTS
    echo_url = os.getenv("ECHO_SERVER_URL", "ws://localhost:8000")
    echo_voice = os.getenv("ECHO_VOICE", "expresso_02_ex03-ex01_calm_005")

    tts = EchoTTSService(
        server_url=echo_url,
        voice=echo_voice,
        cfg_scale_text=float(os.getenv("ECHO_CFG_SCALE_TEXT", "3.0")),
        cfg_scale_speaker=float(os.getenv("ECHO_CFG_SCALE_SPEAKER", "8.0")),
        seed=int(os.getenv("ECHO_SEED", "0")),
    )

    # Context for conversation (empty initial messages)
    messages = []
    context = OpenAILLMContext(messages)
    context_aggregator = llm.create_context_aggregator(context)

    pipeline = Pipeline(
        [
            transport.input(),              # Transport user input (audio)
            context_aggregator.user(),      # User context aggregation
            llm,                            # GeminiLive STT + LLM (audio → text)
            tts,                            # VibeVoice TTS (text → audio)
            transport.output(),             # Transport bot output (audio)
            context_aggregator.assistant(), # Assistant context aggregation
        ]
    )

    task = PipelineTask(
        pipeline,
        params=PipelineParams(
            enable_metrics=True,
            enable_usage_metrics=True,
        ),
        idle_timeout_secs=runner_args.pipeline_idle_timeout_secs,
    )

    @transport.event_handler("on_client_connected")
    async def on_client_connected(transport, client):
        logger.info("Client connected")
        # Kick off the conversation
        await task.queue_frames([LLMRunFrame()])

    @transport.event_handler("on_client_disconnected")
    async def on_client_disconnected(transport, client):
        logger.info("Client disconnected")
        await task.cancel()

    runner = PipelineRunner(handle_sigint=runner_args.handle_sigint)
    await runner.run(task)


async def bot(runner_args: RunnerArguments):
    """Main bot entry point compatible with Pipecat Cloud."""
    transport = await create_transport(runner_args, transport_params)
    await run_bot(transport, runner_args)


if __name__ == "__main__":
    from pipecat.runner.run import main
    main()
