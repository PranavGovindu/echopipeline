"""
Test full pipeline with local microphone input (no Daily needed!)

This uses Pipecat's local audio input instead of Daily.
"""

import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from custom_vibevoice_tts_service import VibeVoiceTTSService
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext
from pipecat.services.google import GoogleLLMService, GoogleSTTService

from loguru import logger

# Try to import local audio input
try:
    from pipecat.transports.socket import SocketTransport
    HAS_SOCKET = True
except ImportError:
    HAS_SOCKET = False

try:
    from pipecat.transports.io import IOTransport
    HAS_IO = True
except ImportError:
    HAS_IO = False


async def test_with_microphone():
    """Test full pipeline with microphone input."""
    
    # Get config
    google_api_key = os.environ.get("GOOGLE_API_KEY")
    if not google_api_key:
        print("❌ Error: GOOGLE_API_KEY required")
        sys.exit(1)
    
    vibevoice_server_url = os.environ.get("VIBEVOICE_SERVER_URL")
    if not vibevoice_server_url:
        print("❌ Error: VIBEVOICE_SERVER_URL required")
        sys.exit(1)
    
    print("\n🚀 Testing Full Pipeline: Microphone → STT → LLM → TTS → Speakers")
    print("=" * 60)
    print()
    
    # Initialize services
    print("🔧 Initializing services...")
    stt_service = GoogleSTTService(api_key=google_api_key)
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
    
    # Try to use IO transport (simplest for local)
    if HAS_IO:
        print("✅ Using IO Transport (microphone/speakers)")
        transport = IOTransport()
    elif HAS_SOCKET:
        print("✅ Using Socket Transport")
        transport = SocketTransport()
    else:
        print("❌ No local transport available")
        print("💡 Install pipecat with audio support:")
        print("   pip install 'pipecat-ai[io]' or 'pipecat-ai[socket]'")
        print()
        print("Alternatively, you can test with text input:")
        print("   python test_full_pipeline.py --text 'Your text here'")
        sys.exit(1)
    
    # Build pipeline
    pipeline = Pipeline([
        transport.input(),              # Microphone input
        stt_service,                    # Gemini STT: Audio → Text
        context_aggregator.user(),     # Add user message to context
        llm_service,                    # Gemini LLM: Text → Text
        tts_service,                    # VibeVoice TTS: Text → Audio
        transport.output(),             # Speaker output
        context_aggregator.assistant(), # Add assistant message to context
    ])
    
    task = PipelineTask(
        pipeline,
        params=PipelineParams(
            allow_interruptions=True,
            enable_metrics=True,
        ),
    )
    
    print("✅ Pipeline ready!")
    print()
    print("🎙️  Start speaking into your microphone...")
    print("💬 The assistant will respond through your speakers")
    print("Press Ctrl+C to stop")
    print()
    
    # Run pipeline
    runner = PipelineRunner()
    try:
        await runner.run(task)
    except KeyboardInterrupt:
        print("\n🛑 Stopping...")
        await task.cancel()


if __name__ == "__main__":
    print("⚠️  Note: Local microphone input requires additional dependencies")
    print("   Install with: pip install 'pipecat-ai[io]'")
    print()
    print("   Or test with text input instead:")
    print("   python test_full_pipeline.py --text 'Your question'")
    print()
    
    try:
        asyncio.run(test_with_microphone())
    except ImportError as e:
        print(f"\n❌ Missing dependency: {e}")
        print("\n💡 Options:")
        print("1. Install audio support: pip install 'pipecat-ai[io]'")
        print("2. Test with text instead: python test_full_pipeline.py")
        print("3. Use Daily room (works without extra deps): python test_local.py --mode daily")

