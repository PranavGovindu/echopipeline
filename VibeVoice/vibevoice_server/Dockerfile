# VibeVoice TTS Server Dockerfile
# Based on NVIDIA PyTorch container for GPU support

FROM nvcr.io/nvidia/pytorch:24.07-py3

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libsndfile1 \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Copy the VibeVoice package
COPY vibevoice/ /app/vibevoice/
COPY pyproject.toml /app/
COPY demo/web/ /app/demo/web/
COPY demo/voices/ /app/demo/voices/

# Install Python dependencies
RUN pip install --no-cache-dir -e .

# Install additional dependencies for the web server
RUN pip install --no-cache-dir \
    fastapi \
    uvicorn[standard] \
    websockets

# Expose port
EXPOSE 8000

# Set environment variables
ENV MODEL_DEVICE=cuda
ENV PYTHONUNBUFFERED=1

# Run the server
WORKDIR /app/demo/web
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]

