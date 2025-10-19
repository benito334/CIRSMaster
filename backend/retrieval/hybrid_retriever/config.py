import os
from dotenv import load_dotenv

load_dotenv()

QDRANT_URL = os.getenv("QDRANT_URL", "http://qdrant:6333")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "cirs_chunks_v1")

BM25_INDEX_PATH = os.getenv("BM25_INDEX_PATH", "/data/index/bm25")

EMBED_MODEL = os.getenv("EMBED_MODEL", "BAAI/bge-large-en-v1.5")
USE_GPU = os.getenv("USE_GPU", "true").lower() == "true"

VECTOR_WEIGHT = float(os.getenv("VECTOR_WEIGHT", "0.6"))
LEXICAL_WEIGHT = float(os.getenv("LEXICAL_WEIGHT", "0.4"))
TOP_K_VECTOR = int(os.getenv("TOP_K_VECTOR", "20"))
TOP_K_LEXICAL = int(os.getenv("TOP_K_LEXICAL", "20"))

CHUNKS_ROOT = os.getenv("CHUNKS_ROOT", "/data/chunks")
