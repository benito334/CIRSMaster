import os
from dotenv import load_dotenv

load_dotenv()

DB_URL = os.getenv("DB_URL")
PORT = int(os.getenv("PORT", "8019"))
JWT_ALG = os.getenv("AUTH_JWT_ALG", "HS256")
JWT_SECRET = os.getenv("AUTH_JWT_SECRET", "change_me")
ACCESS_TTL_MIN = int(os.getenv("AUTH_ACCESS_TTL_MIN", "15"))
REFRESH_TTL_DAYS = int(os.getenv("AUTH_REFRESH_TTL_DAYS", "14"))
PASSWORD_HASH = os.getenv("AUTH_PASSWORD_HASH", "bcrypt")
TENANCY_DEFAULT_NAME = os.getenv("TENANCY_DEFAULT_NAME", "default")
