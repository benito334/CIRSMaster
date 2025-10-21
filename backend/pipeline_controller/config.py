import os
from dotenv import load_dotenv

load_dotenv()

DB_URL = os.getenv("DB_URL", "")
PORT = int(os.getenv("PIPELINE_PORT", "8021"))
LOG_ROOT = os.getenv("PIPELINE_LOG_ROOT", "/data/logs")
# Comma-separated internal service base URLs if needed later
GPU_SERVICES_URL = os.getenv(
    "GPU_SERVICES_URL",
    "http://asr_gpu:8001,http://validation_gpu:8005,http://chunking_embeddings_gpu:8006",
)
