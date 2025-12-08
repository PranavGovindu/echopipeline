#!/bin/bash
# Quick script to start VibeVoice server for testing

echo "🚀 Starting VibeVoice TTS Server..."
echo ""

# Check if MODEL_PATH is set
if [ -z "$MODEL_PATH" ]; then
    export MODEL_PATH="microsoft/VibeVoice-Realtime-0.5B"
    echo "📝 Using default MODEL_PATH: $MODEL_PATH"
    echo "   (Set MODEL_PATH env var to use a different model)"
fi

# Check if MODEL_DEVICE is set, default to cpu if no GPU
if [ -z "$MODEL_DEVICE" ]; then
    # Check for NVIDIA GPU
    if command -v nvidia-smi &> /dev/null && nvidia-smi &> /dev/null; then
        export MODEL_DEVICE="cuda"
        echo "🎮 GPU detected, using CUDA"
    else
        export MODEL_DEVICE="cpu"
        echo "💻 No GPU detected, using CPU (will be slower)"
    fi
fi

# Check if port is set
PORT=${PORT:-8000}
echo "🌐 Starting server on port $PORT"
echo ""

# Navigate to VibeVoice repo root
VIBEVOICE_ROOT="$(dirname "$0")/.."
cd "$VIBEVOICE_ROOT"

# Try different methods to run uvicorn
if command -v uv &> /dev/null; then
    echo "📦 Using uv..."
    cd demo/web
    MODEL_PATH="$MODEL_PATH" MODEL_DEVICE="$MODEL_DEVICE" uv run python -m uvicorn app:app --host 0.0.0.0 --port "$PORT"
elif [ -d ".venv" ]; then
    echo "📦 Using .venv..."
    source .venv/bin/activate
    cd demo/web
    MODEL_PATH="$MODEL_PATH" MODEL_DEVICE="$MODEL_DEVICE" python -m uvicorn app:app --host 0.0.0.0 --port "$PORT"
elif [ -d "venv" ]; then
    echo "📦 Using venv..."
    source venv/bin/activate
    cd demo/web
    MODEL_PATH="$MODEL_PATH" MODEL_DEVICE="$MODEL_DEVICE" python -m uvicorn app:app --host 0.0.0.0 --port "$PORT"
elif python3 -m uvicorn --version &> /dev/null; then
    echo "📦 Using system python3..."
    cd demo/web
    MODEL_PATH="$MODEL_PATH" MODEL_DEVICE="$MODEL_DEVICE" python3 -m uvicorn app:app --host 0.0.0.0 --port "$PORT"
else
    echo "❌ Error: uvicorn not found"
    echo ""
    echo "Please install VibeVoice dependencies first:"
    echo "  cd $VIBEVOICE_ROOT"
    echo "  pip install -e ."
    echo ""
    echo "Or use uv:"
    echo "  uv sync"
    exit 1
fi
