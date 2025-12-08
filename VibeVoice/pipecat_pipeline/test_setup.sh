#!/bin/bash
# Quick setup script for local testing

set -e

echo "🚀 VibeVoice Pipeline Local Testing Setup"
echo "=========================================="
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "📝 Creating .env file from .env.example..."
    cp .env.example .env
    echo "⚠️  Please edit .env and add your API keys!"
    echo ""
fi

# Load environment variables
if [ -f .env ]; then
    echo "📋 Loading environment variables from .env..."
    export $(cat .env | grep -v '^#' | xargs)
    echo "✅ Environment variables loaded"
    echo ""
fi

# Check required variables
if [ -z "$GOOGLE_API_KEY" ]; then
    echo "❌ Error: GOOGLE_API_KEY not set"
    echo "   Set it in .env or export it: export GOOGLE_API_KEY=your-key"
    exit 1
fi

# Check if VibeVoice server is running
if [ -z "$VIBEVOICE_SERVER_URL" ]; then
    echo "⚠️  VIBEVOICE_SERVER_URL not set"
    echo ""
    echo "Choose an option:"
    echo "1. Start VibeVoice server locally (port 8000)"
    echo "2. Use Cloudflare Tunnel (public URL)"
    echo ""
    read -p "Enter choice (1 or 2): " choice
    
    if [ "$choice" == "1" ]; then
        echo ""
        echo "📝 To start VibeVoice server, run in another terminal:"
        echo "   cd ../demo/web"
        echo "   MODEL_PATH=microsoft/VibeVoice-Realtime-0.5B uvicorn app:app --host 0.0.0.0 --port 8000"
        echo ""
        read -p "Press Enter when server is running..."
        export VIBEVOICE_SERVER_URL="ws://localhost:8000"
    elif [ "$choice" == "2" ]; then
        echo ""
        echo "🌐 Starting VibeVoice server with Cloudflare Tunnel..."
        cd ../demo
        python run_with_cloudflare.py --model_path microsoft/VibeVoice-Realtime-0.5B &
        CLOUDFLARE_PID=$!
        echo "⏳ Waiting for Cloudflare URL..."
        sleep 10
        # Extract URL from output (simplified - user should copy it manually)
        echo "✅ Cloudflare Tunnel started (PID: $CLOUDFLARE_PID)"
        echo "📋 Copy the public URL and set VIBEVOICE_SERVER_URL (replace https:// with wss://)"
        echo "   Example: export VIBEVOICE_SERVER_URL=wss://xxxxx.trycloudflare.com"
        read -p "Enter VIBEVOICE_SERVER_URL: " server_url
        export VIBEVOICE_SERVER_URL="$server_url"
    else
        echo "❌ Invalid choice"
        exit 1
    fi
fi

echo ""
echo "✅ Setup complete!"
echo ""
echo "🧪 Testing options:"
echo ""
echo "1. Test TTS only (quickest):"
echo "   python test_local.py --mode tts-only --text 'Hello, this is a test'"
echo ""
echo "2. Test full pipeline with text (LLM + TTS):"
echo "   python test_local.py --mode text --text 'Tell me a joke'"
echo ""
echo "3. Test full pipeline with Daily room (STT + LLM + TTS):"
echo "   python test_local.py --mode daily --daily-room-url YOUR_ROOM_URL --daily-token YOUR_TOKEN"
echo ""
echo "Current configuration:"
echo "  GOOGLE_API_KEY: ${GOOGLE_API_KEY:0:10}..."
echo "  VIBEVOICE_SERVER_URL: $VIBEVOICE_SERVER_URL"
echo ""

