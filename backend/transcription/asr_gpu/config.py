import os
from dotenv import load_dotenv

load_dotenv()

ASR_MODEL = os.getenv("ASR_MODEL", "large-v3")
ASR_COMPUTE_TYPE = os.getenv("ASR_COMPUTE_TYPE", "float16")  # for GPU use float16/int8
ASR_DIARIZATION = os.getenv("ASR_DIARIZATION", "false").lower() == "true"
OUTPUT_ROOT = os.getenv("OUTPUT_PATH", "/data/transcripts")
INPUT_ROOT = os.getenv("INPUT_PATH", "/data/ingestion")
DB_URL = os.getenv("DB_URL")  # e.g., postgresql://user:pass@host:5432/dbname
PYANNOTE_AUTH_TOKEN = os.getenv("PYANNOTE_AUTH_TOKEN")  # required for diarization models
RUN_TAG = os.getenv("RUN_TAG")  # optional manual override for version directory timestamp/tag

# Resumability index path
PROCESSED_INDEX = os.getenv("PROCESSED_INDEX", os.path.join(OUTPUT_ROOT, ".processed_index.json"))

# Optional: limit processed file types
AUDIO_EXTS = {".wav", ".mp3", ".m4a", ".flac", ".ogg"}
VIDEO_EXTS = {".mp4", ".mov", ".mkv", ".avi", ".webm"}

# Batch behavior
MAX_CONCURRENT = int(os.getenv("ASR_MAX_CONCURRENT", "1"))
