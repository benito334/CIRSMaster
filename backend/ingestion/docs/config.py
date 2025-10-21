import os
from dotenv import load_dotenv

load_dotenv()

PDF_INPUT_PATH = os.getenv("PDF_INPUT_PATH", "/data/ingestion/pdf")
EPUB_INPUT_PATH = os.getenv("EPUB_INPUT_PATH", "/data/ingestion/epub")
OUTPUT_PATH = os.getenv("OUTPUT_PATH", "/data/transcripts")
RUN_TAG = os.getenv("RUN_TAG")  # optional; auto timestamp if not set

# Resumability index
DOCS_INDEX = os.getenv("DOCS_INDEX", os.path.join(OUTPUT_PATH, ".docs_ingest_index.json"))
