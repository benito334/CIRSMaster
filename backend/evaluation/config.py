import os
from dotenv import load_dotenv

load_dotenv()

DB_URL = os.getenv("DB_URL")  # postgresql://user:pass@host:5432/cirs
QDRANT_URL = os.getenv("QDRANT_URL", "http://qdrant:6333")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
EMBED_MODEL = os.getenv("EMBED_MODEL", "BAAI/bge-large-en-v1.5")
USE_GPU = os.getenv("USE_GPU", "true").lower() == "true"
PORT = int(os.getenv("PORT", "8011"))
