# Echo TTS GPU Server Setup Guide

Quick guide to spin up Echo TTS server on a cloud GPU.

## Prerequisites

- Cloud GPU server (Vultr, RunPod, Lambda, etc.)
- SSH access with key file
- Voice file (e.g., `elise.wav`) on your Mac

---

## Step 1: SSH into your server

```bash
ssh -i /path/to/your/private_key.pem ubuntu@YOUR_SERVER_IP
# or
ssh -i /path/to/your/private_key.pem root@YOUR_SERVER_IP
```

---

## Step 2: Check GPU is available

```bash
nvidia-smi
```

You should see your GPU (e.g., A100, RTX 4090, etc.)

---

## Step 3: Install dependencies

```bash
# Update system
sudo apt update && sudo apt install -y python3-pip git ffmpeg

# Clone the repo
cd ~
git clone --depth 1 https://github.com/PranavGovindu/echopipeline.git
cd echopipeline

# Install Python dependencies
pip install -r requirements.txt
```

---

## Step 4: Upload your voice file

**Run this on your Mac** (new terminal):

```bash
scp -i /Users/vatsalbharti/Downloads/private_key.pem \
    "/Users/vatsalbharti/Desktop/chirp3/elise.wav" \
    ubuntu@YOUR_SERVER_IP:/home/ubuntu/echopipeline/audio_prompts/
```

For root user:
```bash
scp -i /Users/vatsalbharti/Downloads/private_key.pem \
    "/Users/vatsalbharti/Desktop/chirp3/elise.wav" \
    root@YOUR_SERVER_IP:/root/echopipeline/audio_prompts/
```

---

## Step 5: Start the server

```bash
cd ~/echopipeline

ECHO_DEVICE=cuda \
ECHO_COMPILE=1 \
ECHO_PERFORMANCE_PRESET=low_mid \
ECHO_CACHE_SPEAKER_ON_GPU=1 \
ECHO_WARMUP_VOICE=elise \
ECHO_FISH_DTYPE=bfloat16 \
python3 api_server.py --host 0.0.0.0 --port 8000
```

**First startup takes 2-3 minutes** (model download + compilation).

Wait for:
```
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

---

## Step 6: Get your server URL

Your Echo TTS server URL is:
```
ws://YOUR_SERVER_IP:8000
```

Get your IP:
```bash
curl ifconfig.me
```

---

## Step 7: Use in Pipecat

On your Mac, set the environment variable:

```bash
export ECHO_SERVER_URL=ws://YOUR_SERVER_IP:8000
```

Or in your `.env` file:
```
ECHO_SERVER_URL=ws://YOUR_SERVER_IP:8000
```

---

## Quick Reference

### Environment Variables (Optimizations)

| Variable | Value | Effect |
|----------|-------|--------|
| `ECHO_DEVICE` | `cuda` | Use GPU |
| `ECHO_COMPILE` | `1` | 100-200ms faster (slower startup) |
| `ECHO_PERFORMANCE_PRESET` | `low_mid` | 50-100ms faster |
| `ECHO_CACHE_SPEAKER_ON_GPU` | `1` | 20-60ms faster per request |
| `ECHO_WARMUP_VOICE` | `elise` | Pre-loads your voice |
| `ECHO_FISH_DTYPE` | `bfloat16` | 20-50ms faster decoder |

### Common Paths

| User | Repo Path | Audio Prompts Path |
|------|-----------|-------------------|
| `ubuntu` | `/home/ubuntu/echopipeline` | `/home/ubuntu/echopipeline/audio_prompts/` |
| `root` | `/root/echopipeline` | `/root/echopipeline/audio_prompts/` |

### Firewall

Make sure port **8000** is open:
- **Vultr**: Settings > Firewall > Allow TCP 8000
- **AWS**: Security Groups > Inbound > Add TCP 8000
- **GCP**: VPC Network > Firewall > Add TCP 8000

---

## Run in Background (Optional)

To keep server running after disconnecting:

```bash
# Using nohup
nohup bash -c 'ECHO_DEVICE=cuda ECHO_COMPILE=1 ECHO_PERFORMANCE_PRESET=low_mid ECHO_CACHE_SPEAKER_ON_GPU=1 ECHO_WARMUP_VOICE=elise ECHO_FISH_DTYPE=bfloat16 python3 api_server.py --host 0.0.0.0 --port 8000' > echo_tts.log 2>&1 &

# Check logs
tail -f echo_tts.log

# Or using screen
screen -S echo-tts
# Run the server command, then Ctrl+A, D to detach
# screen -r echo-tts to reattach
```

---

## Troubleshooting

### "No GPU detected"
```bash
nvidia-smi  # Check GPU is visible
pip install torch --upgrade  # Reinstall PyTorch with CUDA
```

### "Connection refused" from Pipecat
- Check firewall allows port 8000
- Verify server is running: `curl http://localhost:8000/v1/voices`

### "Permission denied" on SCP
- Check key file permissions: `chmod 600 /path/to/private_key.pem`
- Verify correct username (ubuntu vs root)

### Server crashes with OOM
- Use smaller model or reduce batch size
- Check GPU memory: `nvidia-smi`
