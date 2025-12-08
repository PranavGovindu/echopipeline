# Echo TTS + Pipecat Voice Agent Setup

Real-time voice assistant using Gemini for STT/LLM and Echo TTS for speech synthesis.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              YOUR LAPTOP                                    │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  Pipecat Bot (bot.py)                                                │   │
│  │  ┌─────────┐    ┌─────────────┐    ┌──────────────────────────────┐ │   │
│  │  │   Mic   │───▶│ Gemini Live │───▶│ Echo TTS Service (WebSocket) │ │   │
│  │  │ Speaker │◀───│  STT + LLM  │◀───│      custom_echo_tts.py      │ │   │
│  │  └─────────┘    └─────────────┘    └──────────────────────────────┘ │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      │ WebSocket (wss://)
                                      │ via Cloudflare Tunnel
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           GOOGLE COLAB (GPU)                                │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  Echo TTS Server (api_server.py)                                     │   │
│  │  - Loads Echo TTS model (2.4B DiT)                                   │   │
│  │  - Streams PCM audio at 44.1kHz                                      │   │
│  │  - Uses your cloned voice (elise.wav)                                │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Prerequisites

- **Google Account** with access to Google Colab (GPU runtime)
- **Google API Key** for Gemini Live ([Get one here](https://aistudio.google.com/app/apikey))
- **Python 3.10+** on your laptop
- **Voice sample** (5-30 seconds WAV file of the voice you want to clone)

## Quick Start

### Step 1: Start Echo TTS Server (Google Colab)

1. Open `echo_tts_colab.ipynb` in Google Colab
2. Select **GPU runtime**: Runtime → Change runtime type → T4/A100 GPU
3. Run cells in order:
   - **Cell 1**: Check GPU
   - **Cell 2**: Clone repo & install dependencies
   - **Cell 3**: Upload your voice file (e.g., `elise.wav`)
   - **Cell 4**: Download cloudflared
   - **Cell 5**: Start server + tunnel

4. Wait for startup to complete (watch for these messages):
   ```
   ✅ Warmup compile finished; cache should be saved.
   INFO:     Application startup complete.
   INFO:     Uvicorn running on http://0.0.0.0:8000
   ```

5. Copy the WebSocket URL:
   ```
   📋 For Pipecat: ECHO_SERVER_URL=wss://xxxxx.trycloudflare.com
   ```

> **Note**: First startup takes 3-5 minutes due to model compilation. Subsequent requests are fast (~1 second).

### Step 2: Run Pipecat Bot (Your Laptop)

1. Navigate to the pipecat folder:
   ```bash
   cd VibeVoice/pipecat_pipeline
   ```

2. Install dependencies:
   ```bash
   pip install -e .
   # or with uv:
   uv sync
   ```

3. Set environment variables:
   ```bash
   export GOOGLE_API_KEY="your-gemini-api-key"
   export ECHO_SERVER_URL="wss://xxxxx.trycloudflare.com"  # From Colab
   export ECHO_VOICE="elise"  # Name of your uploaded voice file (without extension)
   ```

4. Run the bot:
   ```bash
   python bot.py -t webrtc
   ```

5. Open the WebRTC URL shown in terminal (usually `http://localhost:7860`)

6. **Talk!** The bot will respond using your cloned voice.

## Environment Variables

### Pipecat Bot (Your Laptop)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GOOGLE_API_KEY` | Yes | - | Gemini API key |
| `ECHO_SERVER_URL` | Yes | - | WebSocket URL from Colab |
| `ECHO_VOICE` | No | `elise` | Voice name (file in audio_prompts/) |
| `ECHO_CFG_SCALE_TEXT` | No | `2.5` | Text guidance (lower = faster) |
| `ECHO_CFG_SCALE_SPEAKER` | No | `5.0` | Speaker guidance (lower = faster) |
| `GEMINI_MODEL` | No | `models/gemini-live-2.5-flash-preview` | Gemini model |

### Echo TTS Server (Colab)

| Variable | Default | Description |
|----------|---------|-------------|
| `ECHO_COMPILE` | `1` | Enable torch.compile (slower startup, faster inference) |
| `ECHO_PERFORMANCE_PRESET` | `low_mid` | `default`, `low_mid`, or `low` |
| `ECHO_CACHE_SPEAKER_ON_GPU` | `1` | Cache voice on GPU |
| `ECHO_WARMUP_VOICE` | `elise` | Pre-warm with this voice |
| `ECHO_FISH_DTYPE` | `bfloat16` | Decoder precision |

## Performance Tuning

### Latency Optimization

The system is tuned for low latency:

| Setting | Value | Impact |
|---------|-------|--------|
| `ECHO_COMPILE=1` | Enabled | -100-200ms per chunk |
| `ECHO_PERFORMANCE_PRESET=low_mid` | Enabled | -50-100ms per chunk |
| `cfg_scale_text=2.5` | Lower than default | -10-30ms |
| `cfg_scale_speaker=5.0` | Lower than default | -10-30ms |

### Expected Performance (A100 GPU)

- **TTFB** (time to first audio): ~300-500ms
- **RTFx**: ~0.3-0.5 (2-3x faster than real-time)
- **Total response time**: 1-2 seconds

### Voice Quality Tips

1. **Use 10-30 seconds** of clear reference audio
2. **Avoid background noise** in the reference
3. **Higher CFG scales** (3.0/8.0) = better cloning but slower
4. **Lower CFG scales** (2.5/5.0) = faster but slightly less accurate

## Troubleshooting

### "HTTP 502" Error
- Server isn't ready yet - wait for `Application startup complete`
- First startup takes 3-5 minutes for compilation

### Slow/Stretched Speech
- Text is too short - the system prompt encourages longer responses
- If still slow, your response is being split into multiple chunks

### Choppy Audio (Gaps)
- Responses are being split at sentence boundaries
- The system prompt is designed to use flowing sentences with commas

### Voice Doesn't Sound Right
- Try higher `cfg_scale_speaker` (6.0-8.0)
- Use longer/clearer reference audio
- Make sure you uploaded the correct voice file

### Connection Refused
- Check Colab is still running
- Cloudflare tunnel URL changes each session - get the new one
- Make sure you're using `wss://` not `https://`

## File Structure

```
echo-tts-api/
├── api_server.py              # Echo TTS FastAPI server
├── echo_tts_colab.ipynb       # Colab notebook for running server
├── audio_prompts/             # Voice files go here
│   └── elise.wav              # Your cloned voice
├── VibeVoice/
│   └── pipecat_pipeline/
│       ├── bot.py                      # Main Pipecat bot
│       ├── custom_echo_tts_service.py  # Echo TTS Pipecat service
│       └── pyproject.toml              # Dependencies
└── PIPECAT_SETUP.md           # This file
```

## License

Echo TTS outputs are CC-BY-NC-SA-4.0 due to Fish Speech S1-DAC dependency.

