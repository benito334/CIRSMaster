from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from .config import EMBED_MODEL, EMBED_BATCH_SIZE, QDRANT_URL, QDRANT_API_KEY, QDRANT_COLLECTION, USE_GPU


@dataclass
class EmbedResult:
    count: int
    dim: int


def _device() -> str:
    if USE_GPU:
        try:
            import torch
            return "cuda" if torch.cuda.is_available() else "cpu"
        except Exception:
            return "cpu"
    return "cpu"


def _load_model():
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer(EMBED_MODEL, device=_device())
    return model


def _ensure_collection(client, name: str, dim: int):
    from qdrant_client.models import Distance, VectorParams
    try:
        collections = client.get_collections().collections
        if any(c.name == name for c in collections):
            return
        client.create_collection(
            collection_name=name,
            vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
        )
    except Exception:
        # Attempt idempotent creation
        try:
            client.create_collection(
                collection_name=name,
                vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
            )
        except Exception:
            pass


def embed_and_upsert(chunks: List[Dict[str, Any]], collection: Optional[str] = None) -> EmbedResult:
    if not chunks:
        return EmbedResult(count=0, dim=0)

    from qdrant_client import QdrantClient
    from qdrant_client.models import PointStruct

    model = _load_model()
    dim = model.get_sentence_embedding_dimension()

    client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
    coll = collection or QDRANT_COLLECTION
    _ensure_collection(client, coll, dim)

    texts = [c.get("text", "") for c in chunks]

    # Batch encode
    embeddings = model.encode(texts, batch_size=EMBED_BATCH_SIZE, show_progress_bar=False, convert_to_numpy=True, normalize_embeddings=True)

    points = []
    for i, (c, vec) in enumerate(zip(chunks, embeddings)):
        cid = c.get("chunk_id")
        payload = {
            "chunk_id": cid,
            "source_id": c.get("source_id"),
            "parent_type": "transcript",
            "parent_id": None,
            "start_time": c.get("start_time"),
            "end_time": c.get("end_time"),
            "page": None,
            "text": c.get("text", ""),
            "speaker": c.get("speaker"),
            "topic_tags": c.get("topic_tags", []),
            "entities": c.get("entities", []),
            "validation_confidence": c.get("validation_confidence"),
        }
        points.append(PointStruct(id=cid, vector=vec.tolist(), payload=payload))

    # Upsert in batches
    batch = 512
    for i in range(0, len(points), batch):
        client.upsert(collection_name=coll, points=points[i:i+batch])

    return EmbedResult(count=len(points), dim=dim)
