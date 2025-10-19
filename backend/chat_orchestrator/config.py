import os
from dotenv import load_dotenv

load_dotenv()

RETRIEVER_URL = os.getenv("RETRIEVER_URL", "http://hybrid_retriever:8002")
LLM_MODE = os.getenv("LLM_MODE", "local")  # local|remote|none
LLM_LOCAL_URL = os.getenv("LLM_LOCAL_URL", "http://ollama:11434")
LLM_LOCAL_MODEL = os.getenv("LLM_LOCAL_MODEL", "llama3.1:8b-instruct")
LLM_REMOTE_URL = os.getenv("LLM_REMOTE_URL", "https://api.openai.com/v1/chat/completions")
LLM_REMOTE_MODEL = os.getenv("LLM_REMOTE_MODEL", "gpt-4o-mini")
LLM_API_KEY = os.getenv("LLM_API_KEY")
MAX_TOKENS = int(os.getenv("MAX_TOKENS", "1500"))
TEMPERATURE = float(os.getenv("TEMPERATURE", "0.3"))
TOP_K = int(os.getenv("TOP_K", "6"))

# Logging / debug
SAVE_CONTEXT = os.getenv("SAVE_CONTEXT", "true").lower() == "true"
CONTEXT_DIR = os.getenv("CONTEXT_DIR", "/data/context_debug")
