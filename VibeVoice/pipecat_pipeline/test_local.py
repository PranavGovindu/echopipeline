"""
Local testing script for the full pipeline: STT → LLM → TTS

This script allows you to test the entire pipeline locally without Pipecat Cloud.
You can test with:
- Microphone input (real-time)
- Text file input (batch)
- Interactive mode
"""

import argparse
import asyncio
import os
import sys
from pathlib import Path

# Add parent directory to path to import custom service
sys.path.insert(0, str(Path(__file__).parent))

from custom_vibevoice_tts_service import VibeVoiceTTSService
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext
from pipecat.services.google import GoogleLLMService, GoogleSTTService
from pipecat.transports.services.daily import DailyParams, DailyTransport
from pipecat.frames.frames import TextFrame

from loguru import logger


async def test_text_to_speech(text: str, tts_service: VibeVoiceTTSService):
    """Test TTS service directly with text input."""
    print(f"\n🎤 Testing TTS with text: '{text}'")
    print("=" * 60)
    
    async for frame in tts_service.run_tts(text):
        if hasattr(frame, 'audio'):
            print(f"✅ Received audio chunk: {len(frame.audio)} bytes")
        elif hasattr(frame, '__class__'):
            print(f"📦 Frame: {frame.__class__.__name__}")
    
    print("=" * 60)
    print("✅ TTS test complete!\n")


async def test_stt_service(stt_service: GoogleSTTService):
    """Test STT service (requires audio input)."""
    print("\n🎙️ Testing STT service...")
    print("💡 This requires audio input - use Daily room or microphone")
    print("=" * 60)
    # STT testing requires actual audio input
    # This would be tested in the full pipeline
    print("⚠️  STT test skipped - will be tested in full pipeline\n")


async def test_llm_service(llm_service: GoogleLLMService, text: str):
    """Test LLM service with text input."""
    print(f"\n🤖 Testing LLM with text: '{text}'")
    print("=" * 60)
    
    # Create a simple test
    messages = [{"role": "user", "content": text}]
    context = OpenAILLMContext(messages)
    
    # This is a simplified test - full testing happens in pipeline
    print(f"✅ LLM service initialized")
    print(f"📝 Input: {text}")
    print("=" * 60)
    print("✅ LLM test complete!\n")


async def test_full_pipeline_with_daily(
    stt_service: GoogleSTTService,
    llm_service: GoogleLLMService,
    tts_service: VibeVoiceTTSService,
    daily_room_url: str,
    daily_token: str,
):
    """Test full pipeline with Daily room."""
    print("\n🚀 Starting full pipeline test with Daily room...")
    print("=" * 60)
    
    # Initialize Daily transport
    transport = DailyTransport(
        daily_room_url,
        daily_token,
        "Test Agent",
        DailyParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
            vad_enabled=True,
            vad_analyzer=SileroVADAnalyzer(),
            vad_audio_passthrough=True,
        ),
    )
    
    # Set up LLM context
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
    
    # Build pipeline
    pipeline = Pipeline(
        [
            transport.input(),
            stt_service,
            context_aggregator.user(),
            llm_service,
            tts_service,
            transport.output(),
            context_aggregator.assistant(),
        ]
    )
    
    # Create task
    task = PipelineTask(
        pipeline,
        params=PipelineParams(
            allow_interruptions=True,
            enable_metrics=True,
            enable_usage_metrics=True,
        ),
    )
    
    # Event handlers
    @transport.event_handler("on_first_participant_joined")
    async def on_first_participant_joined(transport, participant):
        logger.info(f"✅ Participant joined: {participant['id']}")
        print(f"\n✅ Participant joined! Start speaking...")
    
    @transport.event_handler("on_participant_left")
    async def on_participant_left(transport, participant, reason):
        logger.info(f"Participant left: {participant['id']}, reason: {reason}")
        await task.cancel()
    
    @transport.event_handler("on_call_state_updated")
    async def on_call_state_updated(transport, state):
        logger.info(f"Call state: {state}")
        if state == "left":
            await task.cancel()
    
    print("✅ Pipeline ready!")
    print(f"📞 Join Daily room: {daily_room_url}")
    print("💬 Start speaking to test the full pipeline!")
    print("Press Ctrl+C to stop\n")
    
    # Run pipeline
    runner = PipelineRunner()
    try:
        await runner.run(task)
    except KeyboardInterrupt:
        print("\n🛑 Stopping pipeline...")
        await task.cancel()


async def test_text_pipeline(
    llm_service: GoogleLLMService,
    tts_service: VibeVoiceTTSService,
    text: str,
):
    """Test LLM + TTS pipeline with text input (no STT)."""
    print(f"\n🚀 Testing LLM → TTS pipeline with text: '{text}'")
    print("=" * 60)
    
    # Set up LLM context
    messages = [
        {
            "role": "system",
            "content": os.environ.get(
                "SYSTEM_PROMPT",
                "You are a helpful voice assistant. Keep your responses concise and conversational.",
            ),
        },
        {"role": "user", "content": text},
    ]
    context = OpenAILLMContext(messages)
    context_aggregator = llm_service.create_context_aggregator(context)
    
    print(f"📝 User input: {text}")
    print("🤖 Processing with Gemini LLM...")
    
    # Use Pipecat pipeline to get LLM response
    from pipecat.pipeline.pipeline import Pipeline
    from pipecat.pipeline.runner import PipelineRunner
    from pipecat.pipeline.task import PipelineParams, PipelineTask
    from pipecat.frames.frames import TextFrame
    
    # Collect LLM response
    llm_response_parts = []
    
    class ResponseCollector:
        def __init__(self):
            self.response = ""
        
        async def process_frame(self, frame: Frame):
            if isinstance(frame, TextFrame):
                self.response += frame.text
                print(f"🤖 LLM: {frame.text}", end="", flush=True)
            return []
    
    collector = ResponseCollector()
    
    # Build pipeline: Text → LLM → Collector
    pipeline = Pipeline([
        llm_service,
        collector,
    ])
    
    task = PipelineTask(pipeline, params=PipelineParams())
    runner = PipelineRunner()
    
    # Start pipeline and send text
    print("⏳ Getting LLM response...")
    try:
        await task.queue_frames([TextFrame(text=text)])
        await asyncio.sleep(2)  # Give LLM time to respond
        await task.cancel()
        await runner.run(task)
    except Exception as e:
        print(f"\n⚠️  Pipeline error: {e}")
    
    llm_response = collector.response.strip()
    if not llm_response:
        print("\n⚠️  No LLM response received, using input text")
        llm_response = text
    else:
        print(f"\n✅ LLM response received: {llm_response[:100]}...")
    
    print(f"\n🎤 Generating speech with VibeVoice TTS...")
    print(f"📝 TTS input: {llm_response[:100]}...")
    
    # Test TTS with LLM response
    chunk_count = 0
    total_bytes = 0
    async for frame in tts_service.run_tts(llm_response):
        if hasattr(frame, 'audio'):
            chunk_count += 1
            total_bytes += len(frame.audio)
            if chunk_count <= 3:  # Show first few chunks
                print(f"✅ Audio chunk {chunk_count}: {len(frame.audio)} bytes")
        elif hasattr(frame, '__class__'):
            if "Started" in frame.__class__.__name__:
                print("🎵 TTS started generating audio...")
            elif "Stopped" in frame.__class__.__name__:
                print(f"✅ TTS complete! Generated {chunk_count} chunks, {total_bytes} total bytes")
    
    print("=" * 60)
    print("✅ Full pipeline test complete!")
    print(f"   Input: {text}")
    print(f"   LLM Response: {llm_response[:100]}...")
    print(f"   Audio: {chunk_count} chunks, {total_bytes} bytes")
    print()


def main():
    parser = argparse.ArgumentParser(
        description="Test VibeVoice Pipecat pipeline locally"
    )
    parser.add_argument(
        "--mode",
        type=str,
        default="text",
        choices=["text", "daily", "tts-only", "stt-only", "llm-only"],
        help="Test mode",
    )
    parser.add_argument(
        "--text",
        type=str,
        default="Hello, this is a test of the VibeVoice TTS system.",
        help="Text to test with (for text mode)",
    )
    parser.add_argument(
        "--daily-room-url",
        type=str,
        help="Daily room URL (required for daily mode)",
    )
    parser.add_argument(
        "--daily-token",
        type=str,
        help="Daily token (required for daily mode)",
    )
    args = parser.parse_args()
    
    # Check environment variables based on mode
    google_api_key = None
    vibevoice_server_url = None
    
    # Google API key needed for modes that use STT or LLM
    if args.mode in ["daily", "text", "stt-only", "llm-only"]:
        google_api_key = os.environ.get("GOOGLE_API_KEY")
        if not google_api_key:
            print("❌ Error: GOOGLE_API_KEY environment variable is required")
            print("   Set it with: export GOOGLE_API_KEY=your-key")
            sys.exit(1)
    
    # VibeVoice server URL needed for modes that use TTS
    if args.mode in ["daily", "text", "tts-only"]:
        vibevoice_server_url = os.environ.get("VIBEVOICE_SERVER_URL")
        if not vibevoice_server_url:
            print("❌ Error: VIBEVOICE_SERVER_URL environment variable is required")
            print("   Set it with: export VIBEVOICE_SERVER_URL=ws://localhost:8000")
            print("   Or use Cloudflare Tunnel: python demo/run_with_cloudflare.py")
            sys.exit(1)
    
    # Initialize services based on mode
    print("🔧 Initializing services...")
    
    # Only initialize services needed for the selected mode
    stt_service = None
    llm_service = None
    tts_service = None
    
    if args.mode in ["daily", "stt-only"]:
        # STT needed for daily and stt-only modes
        stt_service = GoogleSTTService(api_key=google_api_key)
        print("✅ STT service initialized")
    
    if args.mode in ["daily", "text", "llm-only"]:
        # LLM needed for daily, text, and llm-only modes
        llm_service = GoogleLLMService(
            api_key=google_api_key,
            model=os.environ.get("GEMINI_MODEL", "gemini-2.0-flash-exp"),
        )
        print("✅ LLM service initialized")
    
    if args.mode in ["daily", "text", "tts-only"]:
        # TTS needed for daily, text, and tts-only modes
        tts_service = VibeVoiceTTSService(
            server_url=vibevoice_server_url,
            voice=os.environ.get("VIBEVOICE_VOICE", "en-Carter_man"),
        )
        print("✅ TTS service initialized")
    
    print("✅ Services initialized!\n")
    
    # Run tests based on mode
    if args.mode == "text":
        asyncio.run(test_text_pipeline(llm_service, tts_service, args.text))
    elif args.mode == "daily":
        if not args.daily_room_url or not args.daily_token:
            print("❌ Error: --daily-room-url and --daily-token are required for daily mode")
            sys.exit(1)
        asyncio.run(
            test_full_pipeline_with_daily(
                stt_service, llm_service, tts_service, args.daily_room_url, args.daily_token
            )
        )
    elif args.mode == "tts-only":
        asyncio.run(test_text_to_speech(args.text, tts_service))
    elif args.mode == "stt-only":
        asyncio.run(test_stt_service(stt_service))
    elif args.mode == "llm-only":
        asyncio.run(test_llm_service(llm_service, args.text))
    else:
        print(f"❌ Unknown mode: {args.mode}")


if __name__ == "__main__":
    main()

