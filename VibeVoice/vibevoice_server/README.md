# VibeVoice TTS Server

Docker deployment for the VibeVoice TTS server.

## Building the Docker Image

From the **VibeVoice repo root** (not this directory):

```bash
docker build -f vibevoice_server/Dockerfile -t vibevoice-tts-server .
```

## Running the Server

### With GPU (NVIDIA)

```bash
docker run --gpus all -p 8000:8000 \
    -e MODEL_PATH=microsoft/VibeVoice-Realtime-0.5B \
    -e MODEL_DEVICE=cuda \
    vibevoice-tts-server
```

### With CPU (slower)

```bash
docker run -p 8000:8000 \
    -e MODEL_PATH=microsoft/VibeVoice-Realtime-0.5B \
    -e MODEL_DEVICE=cpu \
    vibevoice-tts-server
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `MODEL_PATH` | HuggingFace model ID or local path | Required |
| `MODEL_DEVICE` | Device to use (cuda, cpu, mps) | `cuda` |
| `VOICE_PRESET` | Default voice preset | Auto-selected |

## API Endpoints

### WebSocket `/stream`

Streaming TTS endpoint.

**Query Parameters:**
- `text` (required) - Text to synthesize
- `voice` (optional) - Voice preset name
- `cfg` (optional) - CFG scale (default: 1.5)
- `steps` (optional) - Inference steps (default: 5)

**Returns:** PCM16 audio bytes (24kHz, mono)

**Example:**
```javascript
const ws = new WebSocket('ws://localhost:8000/stream?text=Hello%20world&voice=en-Carter_man');
ws.binaryType = 'arraybuffer';
ws.onmessage = (event) => {
    // event.data contains PCM16 audio bytes
};
```

### GET `/config`

Get available voices and configuration.

**Returns:**
```json
{
    "voices": ["en-Carter_man", "en-Emma_woman", ...],
    "default_voice": "en-Carter_man"
}
```

### GET `/`

Web UI for testing the TTS server.

## Available Voices

- `en-Carter_man` - Male English voice
- `en-Davis_man` - Male English voice
- `en-Emma_woman` - Female English voice
- `en-Frank_man` - Male English voice
- `en-Grace_woman` - Female English voice
- `en-Mike_man` - Male English voice
- `in-Samuel_man` - Male Indian English voice

## Cloud Deployment

### AWS/GCP/Azure with GPU

1. Create a VM with GPU support
2. Install Docker and NVIDIA Container Toolkit
3. Build and run the container

### Using Docker Compose

```yaml
version: '3.8'
services:
  vibevoice-tts:
    build:
      context: ..
      dockerfile: vibevoice_server/Dockerfile
    ports:
      - "8000:8000"
    environment:
      - MODEL_PATH=microsoft/VibeVoice-Realtime-0.5B
      - MODEL_DEVICE=cuda
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
```

## Performance Notes

- **GPU (T4 or better)**: Real-time streaming, ~300ms first chunk latency
- **CPU**: Not recommended for real-time, significant latency
- **Memory**: ~4-8GB VRAM for the 0.5B model

