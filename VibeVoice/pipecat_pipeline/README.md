# VibeVoice Pipecat Agent

Pipecat voice agent with **Gemini STT**, **Gemini LLM**, and **VibeVoice TTS**.

## Architecture

```
Audio Input → Gemini STT → Gemini LLM → VibeVoice TTS → Audio Output
```

## Prerequisites

1. **VibeVoice TTS Server** running and accessible via WebSocket
2. **Google API Key** for Gemini STT and LLM
3. **Pipecat Cloud account** for deployment

## Local Development

### 1. Install dependencies

```bash
# Using uv (recommended)
uv sync

# Or using pip
pip install -e .
```

### 2. Set up environment variables

```bash
cp .env.example .env
# Edit .env with your values
```

### 3. Start VibeVoice TTS server

```bash
# From the VibeVoice repo root
cd demo/web
MODEL_PATH=microsoft/VibeVoice-Realtime-0.5B uvicorn app:app --host 0.0.0.0 --port 8000
```

### 4. Run the bot locally (requires Daily room)

```bash
# Set Daily room URL and token
export DAILY_ROOM_URL=https://your-domain.daily.co/room-name
export DAILY_TOKEN=your-daily-token

python bot.py
```

## Deployment to Pipecat Cloud

### 1. Build and push Docker image

```bash
docker build -t your-dockerhub-username/vibevoice-pipecat-agent:latest .
docker push your-dockerhub-username/vibevoice-pipecat-agent:latest
```

### 2. Deploy VibeVoice TTS Server

**First, deploy the VibeVoice TTS server separately** (see [DEPLOYMENT.md](DEPLOYMENT.md) for detailed instructions).

#### Quick Option: Cloudflare Tunnel (For Testing)

**Easiest way to get a public URL quickly:**

```bash
# From VibeVoice repo root
cd demo
python run_with_cloudflare.py --model_path microsoft/VibeVoice-Realtime-0.5B
```

This will give you a public URL like `wss://xxxxx.trycloudflare.com` that you can use immediately!

> ⚠️ **Note:** Free Cloudflare URLs are temporary. For production, use a cloud VM or container platform.

#### Production Options:
- **Cloud VM (AWS/GCP/Azure):** Deploy Docker container on GPU instance
- **Container Platforms:** RunPod, Railway, Render, etc.
- **Your own server:** If you have a GPU server

**After deployment, you'll get a server URL like:**
- `ws://your-server-ip:8000` (HTTP)
- `wss://your-domain.com:8000` (HTTPS/secure)
- `wss://xxxxx.trycloudflare.com` (Cloudflare Tunnel)

### 3. Create secrets in Pipecat Cloud

Create a secret set named `vibevoice-secrets` with:
- `GOOGLE_API_KEY` - Your Google API key
- `VIBEVOICE_SERVER_URL` - **Your deployed VibeVoice server URL** (e.g., `ws://your-server:8000`)
- `VIBEVOICE_VOICE` - Voice preset (optional)
- `GEMINI_MODEL` - Gemini model (optional)
- `SYSTEM_PROMPT` - System prompt (optional)

> **Note:** The `VIBEVOICE_SERVER_URL` comes from where you deployed the VibeVoice server. See [DEPLOYMENT.md](DEPLOYMENT.md) for deployment options and how to get the URL.

### 4. Update deployment config

Edit `pcc-deploy.toml`:
- Update `image` with your Docker Hub image
- Update `secret_set` with your secret set name
- Adjust `scaling` as needed

### 5. Deploy

```bash
pcc auth login
pcc deploy
```

## Available Voices

- `en-Carter_man` - Male English voice
- `en-Davis_man` - Male English voice
- `en-Emma_woman` - Female English voice
- `en-Frank_man` - Male English voice
- `en-Grace_woman` - Female English voice
- `en-Mike_man` - Male English voice
- `in-Samuel_man` - Male Indian English voice

## Configuration Options

| Environment Variable | Description | Default |
|---------------------|-------------|---------|
| `GOOGLE_API_KEY` | Google API key for Gemini | Required |
| `VIBEVOICE_SERVER_URL` | VibeVoice WebSocket URL | Required |
| `VIBEVOICE_VOICE` | Voice preset name | `en-Carter_man` |
| `GEMINI_MODEL` | Gemini model name | `gemini-2.0-flash-exp` |
| `SYSTEM_PROMPT` | System prompt for LLM | Default assistant prompt |

## VibeVoice Server Deployment

The VibeVoice TTS server needs to be deployed separately. You can use the existing `demo/web/app.py` server.

### Using Docker

```bash
# From vibevoice_server directory
docker build -t vibevoice-tts-server .
docker run -p 8000:8000 -e MODEL_PATH=microsoft/VibeVoice-Realtime-0.5B vibevoice-tts-server
```

### Environment Variables for VibeVoice Server

- `MODEL_PATH` - Path or HuggingFace model ID
- `MODEL_DEVICE` - Device (cuda, cpu, mps)
- `VOICE_PRESET` - Default voice preset

