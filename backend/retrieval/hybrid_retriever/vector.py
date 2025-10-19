from typing import List, Dict, Any

from config import EMBED_MODEL, USE_GPU, QDRANT_URL, QDRANT_API_KEY, QDRANT_COLLECTION, TOP_K_VECTOR


def _device() -> str:
    if USE_GPU:
        try:
            import torch
            return "cuda" if torch.cuda.is_available() else "cpu"
        except Exception:
            return "cpu"
    return "cpu"


def _load_embedder():
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer(EMBED_MODEL, device=_device())
    return model


def vector_search(query: str, top_k: int = TOP_K_VECTOR) -> List[Dict[str, Any]]:
    from qdrant_client import QdrantClient
    client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)

    model = _load_embedder()
    qvec = model.encode([query], convert_to_numpy=True, normalize_embeddings=True)[0]

    res = client.search(
        collection_name=QDRANT_COLLECTION,
        query_vector=qvec.tolist(),
        limit=top_k,
        with_payload=True,
    )
    out: List[Dict[str, Any]] = []
    for r in res:
        payload = r.payload or {}
        out.append({
            "chunk_id": payload.get("chunk_id") or r.id,
            "score": float(r.score) if r.score is not None else None,
            "source_id": payload.get("source_id"),
            "text": payload.get("text") or "",
            "start_time": payload.get("start_time"),
            "end_time": payload.get("end_time"),
            "entities": payload.get("entities", []),
            "topic_tags": payload.get("topic_tags", []),
            "provenance": QDRANT_COLLECTION,
        })
    return out
