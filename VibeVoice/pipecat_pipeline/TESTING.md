# Local Testing Guide

Test your full pipeline (STT → LLM → TTS) locally before deploying to Pipecat Cloud.

## Quick Start

### 1. Set up environment

```bash
cd pipecat_pipeline

# Copy and edit .env file
cp .env.example .env
# Edit .env and add your GOOGLE_API_KEY
```

### 2. Start VibeVoice TTS Server

**Option A: Local server (for local testing)**
```bash
# In a separate terminal
cd demo/web
MODEL_PATH=microsoft/VibeVoice-Realtime-0.5B uvicorn app:app --host 0.0.0.0 --port 8000
```

**Option B: Cloudflare Tunnel (for public access)**
```bash
# In a separate terminal
cd demo
python run_with_cloudflare.py --model_path microsoft/VibeVoice-Realtime-0.5B
# Copy the public URL (replace https:// with wss://)
```

### 3. Set VibeVoice server URL

```bash
# If using local server:
export VIBEVOICE_SERVER_URL=ws://localhost:8000

# If using Cloudflare Tunnel:
export VIBEVOICE_SERVER_URL=wss://xxxxx.trycloudflare.com
```

### 4. Install dependencies

```bash
cd pipecat_pipeline
uv sync
# or
pip install -e .
```

## Testing Modes

### Mode 1: TTS Only (Quickest Test)

Test just the VibeVoice TTS service:

```bash
python test_local.py --mode tts-only --text "Hello, this is a test"
```

**What it does:**
- ✅ Connects to VibeVoice server
- ✅ Sends text to TTS
- ✅ Receives audio chunks
- ✅ Verifies audio format

**Expected output:**
```
🎤 Testing TTS with text: 'Hello, this is a test'
============================================================
✅ Received audio chunk: 48000 bytes
✅ Received audio chunk: 48000 bytes
...
✅ TTS test complete!
```

### Mode 2: LLM + TTS (Text Pipeline)

Test LLM and TTS together (no STT):

```bash
python test_local.py --mode text --text "Tell me a joke"
```

**What it does:**
- ✅ Sends text to Gemini LLM
- ✅ Gets LLM response
- ✅ Converts response to speech with VibeVoice TTS
- ✅ Verifies full text → speech pipeline

**Expected output:**
```
🚀 Testing LLM → TTS pipeline with text: 'Tell me a joke'
============================================================
📝 User input: Tell me a joke
🤖 Processing with LLM...
🎤 Generating speech with VibeVoice TTS...
✅ Audio chunk: 48000 bytes
...
✅ Text pipeline test complete!
```

### Mode 3: Full Pipeline with Daily (STT + LLM + TTS)

Test the complete pipeline with real audio input:

```bash
# First, create a Daily room at https://dashboard.daily.co/
# Get the room URL and token

python test_local.py \
    --mode daily \
    --daily-room-url "https://your-domain.daily.co/room-name" \
    --daily-token "your-daily-token"
```

**What it does:**
- ✅ Connects to Daily room
- ✅ Receives audio input (your voice)
- ✅ Converts speech to text (Gemini STT)
- ✅ Processes with LLM (Gemini)
- ✅ Converts response to speech (VibeVoice TTS)
- ✅ Sends audio back to Daily room

**Expected output:**
```
🚀 Starting full pipeline test with Daily room...
============================================================
✅ Pipeline ready!
📞 Join Daily room: https://your-domain.daily.co/room-name
💬 Start speaking to test the full pipeline!
✅ Participant joined! Start speaking...
```

## Troubleshooting

### TTS Connection Fails

**Error:** `Connection refused` or `WebSocket connection failed`

**Solutions:**
1. Check VibeVoice server is running:
   ```bash
   curl http://localhost:8000/config
   ```

2. Verify server URL format:
   - Local: `ws://localhost:8000`
   - Cloudflare: `wss://xxxxx.trycloudflare.com` (note `wss://` not `https://`)

3. Check firewall/network:
   - Local: Ensure port 8000 is accessible
   - Cloudflare: URL should be accessible from your network

### LLM/STT API Errors

**Error:** `API key invalid` or `Authentication failed`

**Solutions:**
1. Verify `GOOGLE_API_KEY` is set:
   ```bash
   echo $GOOGLE_API_KEY
   ```

2. Check API key is valid:
   - Visit https://aistudio.google.com/app/apikey
   - Ensure API key has access to Gemini API

3. Check API quotas:
   - Free tier has rate limits
   - Paid tier has higher limits

### Audio Format Issues

**Error:** `Invalid audio format` or `Sample rate mismatch`

**Solutions:**
1. VibeVoice outputs 24kHz PCM16
2. Pipecat expects 24kHz float32
3. The custom service handles conversion automatically
4. If issues persist, check `custom_vibevoice_tts_service.py`

## Testing Checklist

Before deploying to Pipecat Cloud, verify:

- [ ] ✅ TTS service connects to VibeVoice server
- [ ] ✅ TTS generates audio from text
- [ ] ✅ LLM service responds to prompts
- [ ] ✅ LLM + TTS pipeline works end-to-end
- [ ] ✅ Full pipeline works with Daily room (if testing STT)
- [ ] ✅ Environment variables are set correctly
- [ ] ✅ Server URLs are accessible

## Next Steps

Once local testing passes:

1. **Deploy VibeVoice server** to production (see [DEPLOYMENT.md](DEPLOYMENT.md))
2. **Build Docker image** for Pipecat pipeline
3. **Deploy to Pipecat Cloud** (see [README.md](README.md))

## Example Test Session

```bash
# Terminal 1: Start VibeVoice server
cd demo
python run_with_cloudflare.py --model_path microsoft/VibeVoice-Realtime-0.5B
# Output: ✅ PUBLIC URL: https://xxxxx.trycloudflare.com

# Terminal 2: Test pipeline
cd pipecat_pipeline
export VIBEVOICE_SERVER_URL=wss://xxxxx.trycloudflare.com
export GOOGLE_API_KEY=your-key

# Test TTS only
python test_local.py --mode tts-only --text "Hello world"

# Test LLM + TTS
python test_local.py --mode text --text "What is the capital of France?"

# Test full pipeline (if you have Daily room)
python test_local.py --mode daily \
    --daily-room-url "https://your-domain.daily.co/test" \
    --daily-token "your-token"
```

