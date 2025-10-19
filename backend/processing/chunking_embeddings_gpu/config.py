import os
from dotenv import load_dotenv

load_dotenv()

# Chunking
CHUNK_SIZE_TOKENS = int(os.getenv("CHUNK_SIZE_TOKENS", "350"))
CHUNK_OVERLAP_TOKENS = int(os.getenv("CHUNK_OVERLAP_TOKENS", "50"))

# Embedding
EMBED_MODEL = os.getenv("EMBED_MODEL", "BAAI/bge-large-en-v1.5")
EMBED_BATCH_SIZE = int(os.getenv("EMBED_BATCH_SIZE", "16"))
USE_GPU = os.getenv("USE_GPU", "true").lower() == "true"

# IO
INPUT_PATH = os.getenv("INPUT_PATH", "/data/validated")
OUTPUT_PATH = os.getenv("OUTPUT_PATH", "/data/chunks")
RUN_TAG = os.getenv("RUN_TAG")

# Qdrant
QDRANT_URL = os.getenv("QDRANT_URL", "http://qdrant:6333")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "cirs_chunks_v1")

# Postgres (optional)
DB_URL = os.getenv("DB_URL")

# Resumability
EMBEDDED_INDEX = os.getenv("EMBEDDED_INDEX", os.path.join(OUTPUT_PATH, ".embedded_index.json"))
