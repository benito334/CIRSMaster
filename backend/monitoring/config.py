import os
from dotenv import load_dotenv

load_dotenv()

DB_URL = os.getenv("DB_URL")  # postgresql://user:pass@host:5432/cirs
QDRANT_URL = os.getenv("QDRANT_URL", "http://qdrant:6333")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
PORT = int(os.getenv("PORT", "8010"))
