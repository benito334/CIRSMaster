import os
from dotenv import load_dotenv

load_dotenv()

DB_URL = os.getenv("DB_URL")  # postgresql://user:pass@host:5432/cirs
PORT = int(os.getenv("PORT", "8014"))
