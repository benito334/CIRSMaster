import json
from typing import Dict, Any, List
import httpx

from config import (
    LLM_MODE,
    LLM_LOCAL_URL,
    LLM_LOCAL_MODEL,
    LLM_REMOTE_URL,
    LLM_REMOTE_MODEL,
    LLM_API_KEY,
    MAX_TOKENS,
    TEMPERATURE,
)


async def generate_async(prompt: str) -> str:
    if LLM_MODE == "none":
        return "[LLM disabled]"
    if LLM_MODE == "local":
        # Ollama compatible
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                f"{LLM_LOCAL_URL}/api/generate",
                json={"model": LLM_LOCAL_MODEL, "prompt": prompt, "stream": False, "options": {"temperature": TEMPERATURE, "num_predict": MAX_TOKENS}},
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("response", "")
    # Remote OpenAI-compatible
    headers = {"Authorization": f"Bearer {LLM_API_KEY}"} if LLM_API_KEY else {}
    payload = {
        "model": LLM_REMOTE_MODEL,
        "messages": [
            {"role": "system", "content": "You are a careful medical assistant. Only answer using the provided CONTEXT and include citations."},
            {"role": "user", "content": prompt},
        ],
        "temperature": TEMPERATURE,
        "max_tokens": MAX_TOKENS,
    }
    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(LLM_REMOTE_URL, headers=headers, json=payload)
        resp.raise_for_status()
        data = resp.json()
        try:
            return data["choices"][0]["message"]["content"]
        except Exception:
            return json.dumps(data)
