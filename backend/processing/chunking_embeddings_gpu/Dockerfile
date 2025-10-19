# Chunking & Embeddings GPU Service
FROM nvidia/cuda:12.1.1-cudnn8-runtime-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive \
    PIP_NO_CACHE_DIR=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
        python3 python3-pip python3-venv python3-dev build-essential git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt /app/requirements.txt

RUN pip3 install --upgrade pip \
 && pip3 install --index-url https://download.pytorch.org/whl/cu121 torch torchvision torchaudio \
 && pip3 install -r /app/requirements.txt

COPY . /app

ENV INPUT_PATH=/data/validated \
    OUTPUT_PATH=/data/chunks

RUN mkdir -p /data/validated /data/chunks

CMD ["python3", "main.py", "--input", "/data/validated"]
