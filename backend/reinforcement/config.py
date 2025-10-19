import os
from dotenv import load_dotenv

load_dotenv()

DB_URL = os.getenv("DB_URL")  # postgresql://user:pass@host:5432/cirs
CONFIG_PATH = os.getenv("CONFIG_PATH", "./backend/chat_orchestrator/config.yaml")
WINDOW_DAYS = int(os.getenv("WINDOW_DAYS", "30"))
DEFAULTS = {
    "retrieval_top_k": int(os.getenv("DEFAULT_RETRIEVAL_TOP_K", "6")),
    "chunk_overlap": int(os.getenv("DEFAULT_CHUNK_OVERLAP", "100")),
    "summary_temperature": float(os.getenv("DEFAULT_SUMMARY_TEMPERATURE", "0.3")),
}
PORT = int(os.getenv("PORT", "8013"))
