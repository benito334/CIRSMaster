import os
from dotenv import load_dotenv

load_dotenv()

DB_URL = os.getenv("DB_URL")
PORT = int(os.getenv("PORT", "8016"))
LOG_PATH = os.getenv("REDACTION_LOG_PATH", "/data/security/redaction_log.json")
