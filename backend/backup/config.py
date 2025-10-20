import os
from dotenv import load_dotenv

load_dotenv()

BACKUP_ROOT = os.getenv("BACKUP_ROOT", "/backups/snapshots")
INCLUDE_DIRS = os.getenv("INCLUDE_DIRS", "/data").split(",")
PG_HOST = os.getenv("PG_HOST", "db")
PG_USER = os.getenv("PG_USER", "cirs")
PG_DB = os.getenv("PG_DB", "cirs")
PG_PORT = int(os.getenv("PG_PORT", "5432"))
DB_URL = os.getenv("DB_URL")
QDRANT_URL = os.getenv("QDRANT_URL", "http://qdrant:6333")
PORT = int(os.getenv("PORT", "8018"))
DAILY_KEEP = int(os.getenv("BACKUP_DAILY_KEEP", "7"))
WEEKLY_KEEP = int(os.getenv("BACKUP_WEEKLY_KEEP", "4"))
MONTHLY_KEEP = int(os.getenv("BACKUP_MONTHLY_KEEP", "3"))
OFFSITE_ENABLED = os.getenv("OFFSITE_ENABLED", "false").lower() == "true"
