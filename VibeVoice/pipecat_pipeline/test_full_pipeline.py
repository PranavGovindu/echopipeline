"""
Test the full pipeline: Text → LLM → TTS

This is a simpler test that demonstrates the full pipeline flow.
"""

import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from custom_vibevoice_tts_service import VibeVoiceTTSService
from pipecat.frames.frames import TextFrame
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext
from pipecat.services.google import GoogleLLMService

from loguru import logger


async def test_full_pipeline(text: str):
    """Test the full LLM → TTS pipeline."""
    
    # Get config
    google_api_key = os.environ.get("GOOGLE_API_KEY")
    if not google_api_key:
        print("❌ Error: GOOGLE_API_KEY required")
        sys.exit(1)
    
    vibevoice_server_url = os.environ.get("VIBEVOICE_SERVER_URL")
    if not vibevoice_server_url:
        print("❌ Error: VIBEVOICE_SERVER_URL required")
        sys.exit(1)
    
    print(f"\n🚀 Testing Full Pipeline: LLM → TTS")
    print("=" * 60)
    print(f"📝 Input text: {text}")
    print()
    
    # Initialize services
    print("🔧 Initializing services...")
    llm_service = GoogleLLMService(
        api_key=google_api_key,
        model=os.environ.get("GEMINI_MODEL", "gemini-2.0-flash-exp"),
    )
    
    tts_service = VibeVoiceTTSService(
        server_url=vibevoice_server_url,
        voice=os.environ.get("VIBEVOICE_VOICE", "en-Carter_man"),
    )
    
    # Set up context
    messages = [
        {
            "role": "system",
            "content": os.environ.get(
                "SYSTEM_PROMPT",
                "You are a helpful voice assistant. Keep your responses concise and conversational.",
            ),
        },
    ]
    context = OpenAILLMContext(messages)
    context_aggregator = llm_service.create_context_aggregator(context)
    
    # Collect LLM response
    llm_response = ""
    
    class LLMResponseCollector:
        async def process_frame(self, frame):
            nonlocal llm_response
            if isinstance(frame, TextFrame):
                llm_response += frame.text
                print(f"🤖 LLM: {frame.text}", end="", flush=True)
            return []
    
    collector = LLMResponseCollector()
    
    # Build pipeline: Text → LLM → Collector → TTS
    pipeline = Pipeline([
        context_aggregator.user(),
        llm_service,
        collector,
        context_aggregator.assistant(),
        tts_service,
    ])
    
    task = PipelineTask(pipeline, params=PipelineParams())
    runner = PipelineRunner()
    
    print("✅ Services initialized!")
    print()
    print("🤖 Getting LLM response...")
    
    # Send text and run pipeline
    await task.queue_frames([TextFrame(text=text)])
    
    # Run for a bit to get LLM response
    try:
        await asyncio.wait_for(runner.run(task), timeout=30.0)
    except asyncio.TimeoutError:
        print("\n⏱️  Timeout waiting for response")
        await task.cancel()
    except Exception as e:
        print(f"\n⚠️  Error: {e}")
        await task.cancel()
    
    if llm_response:
        print(f"\n✅ LLM Response: {llm_response[:200]}...")
    else:
        print("\n⚠️  No LLM response received")
        llm_response = text  # Fallback
    
    print()
    print("=" * 60)
    print("✅ Pipeline test complete!")
    print(f"   Input: {text}")
    print(f"   LLM Response: {llm_response[:100]}...")
    print()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--text",
        type=str,
        default="Tell me a short joke",
        help="Text to process",
    )
    args = parser.parse_args()
    
    asyncio.run(test_full_pipeline(args.text))

