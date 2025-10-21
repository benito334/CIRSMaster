# GPU-enabled ASR service Dockerfile
# Base with CUDA runtime and Python
FROM nvidia/cuda:12.1.1-cudnn8-runtime-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive \
    PIP_NO_CACHE_DIR=1 \
    PYTHONUNBUFFERED=1

# System deps (ffmpeg, python, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3 python3-pip python3-venv python3-dev build-essential \
        ffmpeg git pkg-config python3-av \
        libgl1 libglib2.0-0 \
        libavcodec-dev libavformat-dev libavdevice-dev libavutil-dev \
        libswresample-dev libswscale-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements first
COPY requirements.txt /app/requirements.txt

# Install pinned PyTorch CUDA 12.1 stack, then Python deps
RUN pip3 install --upgrade pip \
 && pip3 install --index-url https://download.pytorch.org/whl/cu121 \
        torch==2.1.2 torchvision==0.16.2 torchaudio==2.1.2 \
 && pip3 install --no-deps faster-whisper==1.0.3 \
 && pip3 install --no-deps whisperx==3.3.1 \
 && pip3 install pyannote.audio==3.1.1 \
 && pip3 install -r /app/requirements.txt

# Add source code
COPY . /app

# Runtime env
ENV TRANSCRIPTS_ROOT=/data/transcripts \
    INPUT_ROOT=/data/ingestion

# Create mount points
RUN mkdir -p /data/transcripts /data/ingestion

# Default command
CMD ["python3", "main.py", "--input", "/data/ingestion"]
