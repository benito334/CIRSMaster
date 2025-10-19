import os
from dotenv import load_dotenv

load_dotenv()

# Models and thresholds
VALIDATION_MODEL = os.getenv("VALIDATION_MODEL", "biogpt")
VALIDATION_THRESHOLD = float(os.getenv("VALIDATION_THRESHOLD", "0.85"))
UMLS_PATH = os.getenv("UMLS_PATH", "/models/umls")

# IO paths
INPUT_PATH = os.getenv("INPUT_PATH", "/data/transcripts")
OUTPUT_PATH = os.getenv("OUTPUT_PATH", "/data/validated")
RUN_TAG = os.getenv("RUN_TAG")  # optional; auto timestamp if not set

# Database
DB_URL = os.getenv("DB_URL")  # postgresql://user:pass@host:5432/cirs

# Index file for resumability
VALIDATED_INDEX = os.getenv("VALIDATED_INDEX", os.path.join(OUTPUT_PATH, ".validated_index.json"))

# Performance
USE_GPU = os.getenv("USE_GPU", "true").lower() == "true"
MAX_FILES = int(os.getenv("VALIDATION_MAX_FILES", "0"))  # 0 = no limit
