import os
from dotenv import load_dotenv

load_dotenv()

DB_URL = os.getenv("DB_URL")
PORT = int(os.getenv("PORT", "8017"))
