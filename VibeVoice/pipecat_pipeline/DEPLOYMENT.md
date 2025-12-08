# VibeVoice Server Production Deployment Guide

## Overview

The **VibeVoice TTS server** must be deployed separately from your Pipecat Cloud agent. The server URL you get after deployment is what you'll use in your Pipecat Cloud secrets.

## Deployment Options

### Option 0: Cloudflare Tunnel (Quickest - For Testing/Development)

**Perfect for quick testing without setting up a full server!**

Cloudflare Tunnel creates a public URL (like `https://xxxxx.trycloudflare.com`) that tunnels to your local server.

#### Quick Start:

```bash
# From VibeVoice repo root
cd demo
python run_with_cloudflare.py --model_path microsoft/VibeVoice-Realtime-0.5B
```

This will:
1. Start the VibeVoice server locally
2. Download and run Cloudflare Tunnel
3. Give you a public URL like `https://xxxxx.trycloudflare.com`

#### Using the URL:

The script will output something like:
```
✅ PUBLIC URL: https://xxxxx.trycloudflare.com

📋 Use this URL in your Pipecat Cloud secrets:
   VIBEVOICE_SERVER_URL=wss://xxxxx.trycloudflare.com
```

**Important:** Replace `https://` with `wss://` for WebSocket connections!

#### For Production:

For production, you can:
1. **Use Cloudflare Tunnel with your own domain** (see Cloudflare Tunnel docs)
2. **Deploy to a cloud VM** (Option 1 below) for better performance
3. **Use a container platform** (Option 2 below)

#### Limitations:

- ⚠️ **Temporary URLs:** Free `trycloudflare.com` URLs change on restart
- ⚠️ **Not for production:** Use for testing/development only
- ⚠️ **Performance:** Depends on your local machine/network

### Option 1: Cloud VM with GPU (Recommended for Production)

Deploy to a cloud provider with GPU support:

#### AWS (EC2 with GPU)
1. **Launch EC2 Instance:**
   - Instance type: `g4dn.xlarge` or `g5.xlarge` (NVIDIA GPU)
   - AMI: Deep Learning AMI (Ubuntu) or Amazon Linux
   - Security Group: Allow inbound on port 8000

2. **SSH into instance and deploy:**
   ```bash
   # Install Docker and NVIDIA Container Toolkit
   sudo apt-get update
   sudo apt-get install -y docker.io
   sudo systemctl start docker
   sudo systemctl enable docker
   
   # Install NVIDIA Container Toolkit
   distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
   curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
   curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | sudo tee /etc/apt/sources.list.d/nvidia-docker.list
   sudo apt-get update && sudo apt-get install -y nvidia-container-toolkit
   sudo systemctl restart docker
   
   # Clone your repo
   git clone <your-repo-url>
   cd VibeVoice
   
   # Build and run
   docker build -f vibevoice_server/Dockerfile -t vibevoice-tts-server .
   docker run -d --gpus all -p 8000:8000 \
       -e MODEL_PATH=microsoft/VibeVoice-Realtime-0.5B \
       -e MODEL_DEVICE=cuda \
       --name vibevoice-server \
       vibevoice-tts-server
   ```

3. **Get your server URL:**
   - Public IP: Check EC2 console → `http://YOUR_PUBLIC_IP:8000`
   - With domain: Point DNS to IP → `ws://yourdomain.com:8000`
   - **Production URL:** `ws://YOUR_PUBLIC_IP:8000` or `ws://yourdomain.com:8000`

#### Google Cloud Platform (GCP)
1. **Create VM with GPU:**
   ```bash
   gcloud compute instances create vibevoice-server \
       --machine-type=n1-standard-4 \
       --accelerator=type=nvidia-tesla-t4,count=1 \
       --image-family=ubuntu-2004-lts \
       --image-project=ubuntu-os-cloud \
       --boot-disk-size=50GB
   ```

2. **Install Docker and deploy** (same as AWS)

3. **Get server URL:**
   - External IP: `ws://EXTERNAL_IP:8000`
   - Or use Cloud Load Balancer with domain

#### Azure
1. **Create VM with GPU:**
   - VM size: `Standard_NC6s_v3` or similar
   - OS: Ubuntu Server

2. **Deploy** (same process as AWS/GCP)

3. **Get server URL:**
   - Public IP: `ws://PUBLIC_IP:8000`

### Option 2: Container Platforms

#### RunPod / Vast.ai / Lambda Labs
1. **Rent GPU instance** (cheaper than cloud VMs)
2. **Deploy Docker container** using the Dockerfile
3. **Get server URL:** Provided by platform (e.g., `ws://pod-xxxxx.runpod.io:8000`)

#### Railway / Render
1. **Deploy Docker container** from Dockerfile
2. **Get server URL:** Provided by platform (e.g., `wss://vibevoice-production.up.railway.app`)

### Option 3: Your Own Server/VPS

If you have a server with GPU:

#### Option 3a: Direct Access
```bash
# On your server
cd /path/to/VibeVoice
docker build -f vibevoice_server/Dockerfile -t vibevoice-tts-server .
docker run -d --gpus all -p 8000:8000 \
    -e MODEL_PATH=microsoft/VibeVoice-Realtime-0.5B \
    vibevoice-tts-server
```

**Server URL:** `ws://YOUR_SERVER_IP:8000` or `ws://yourdomain.com:8000`

#### Option 3b: With Cloudflare Tunnel (No Port Forwarding Needed)

If you can't expose port 8000 or want a secure tunnel:

```bash
# On your server
cd /path/to/VibeVoice/demo
python run_with_cloudflare.py --model_path microsoft/VibeVoice-Realtime-0.5B
```

This gives you a public URL without needing to:
- Open firewall ports
- Set up SSL certificates
- Configure port forwarding

**Server URL:** `wss://xxxxx.trycloudflare.com` (from script output)

## Getting Your Production URL

After deployment, your VibeVoice server URL will be:

### Format:
- **HTTP:** `ws://your-server-ip-or-domain:8000`
- **HTTPS:** `wss://your-server-ip-or-domain:8000` (if using SSL/TLS)

### Examples:
- `ws://54.123.45.67:8000` (direct IP)
- `ws://vibevoice-api.yourdomain.com:8000` (with domain)
- `wss://vibevoice-api.yourdomain.com:8000` (secure WebSocket)

### Testing Your Server URL:

```bash
# Test HTTP endpoint
curl http://YOUR_SERVER_URL:8000/config

# Test WebSocket (using wscat or similar)
wscat -c ws://YOUR_SERVER_URL:8000/stream?text=Hello
```

## Setting Up SSL/TLS (Recommended for Production)

For secure WebSocket (`wss://`), use a reverse proxy:

### Using Nginx:
```nginx
server {
    listen 443 ssl;
    server_name vibevoice-api.yourdomain.com;
    
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    
    location / {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }
}
```

Then use: `wss://vibevoice-api.yourdomain.com`

## Using the URL in Pipecat Cloud

1. **Go to Pipecat Cloud Dashboard**
2. **Create/Edit Secret Set** (e.g., `vibevoice-secrets`)
3. **Add Secret:**
   - Key: `VIBEVOICE_SERVER_URL`
   - Value: `ws://your-production-server:8000` (or `wss://` for secure)
4. **Update `pcc-deploy.toml`:**
   ```toml
   secret_set = "vibevoice-secrets"
   ```

## Security Considerations

1. **Firewall:** Only allow port 8000 from Pipecat Cloud IPs (if possible)
2. **Authentication:** Consider adding API key authentication to VibeVoice server
3. **Rate Limiting:** Implement rate limiting to prevent abuse
4. **Monitoring:** Set up monitoring/alerting for server health

## Cost Estimates

- **AWS EC2 g4dn.xlarge:** ~$0.50-1.00/hour (~$360-720/month)
- **GCP n1-standard-4 + T4:** ~$0.50-0.80/hour (~$360-580/month)
- **RunPod/Lambda Labs:** ~$0.20-0.40/hour (~$144-288/month)
- **Railway/Render:** Varies by usage

## Troubleshooting

### Server not accessible:
- Check firewall/security groups allow port 8000
- Verify Docker container is running: `docker ps`
- Check logs: `docker logs vibevoice-server`

### WebSocket connection fails:
- Ensure using `ws://` (not `http://`) for WebSocket URL
- Check if server supports WebSocket (should work on port 8000)
- Verify network connectivity from Pipecat Cloud

### High latency:
- Use GPU instance (CPU is too slow for real-time)
- Deploy server closer to Pipecat Cloud region
- Check network latency: `ping YOUR_SERVER_IP`

