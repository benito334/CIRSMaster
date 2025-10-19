from typing import Dict, Any, List
from qdrant_client import QdrantClient
from .config import QDRANT_URL, QDRANT_API_KEY

# Minimal provenance resolver using Qdrant payloads and filesystem paths

def resolve_answer_provenance(answer_id: str, retrieved: List[Dict[str, Any]]) -> Dict[str, Any]:
    # In a full implementation, answer_id would map to stored retrievals. Here we accept pre-collected retrieved items.
    # Compute summary metrics
    confidences = []
    for r in retrieved:
        vc = r.get("validation_confidence")
        if isinstance(vc, (int, float)):
            confidences.append(float(vc))
    avg_conf = sum(confidences) / len(confidences) if confidences else None

    lineage = []
    for r in retrieved:
        src = r.get("source_id")
        st = r.get("start_time")
        et = r.get("end_time")
        chunk_id = r.get("chunk_id")
        text = r.get("text") or ""
        prov_link = None
        if st is not None:
            prov_link = f"/data/transcripts/videos/versions/unknown/{src}.json#t={st}"
        lineage.append({
            "chunk_id": chunk_id,
            "source_id": src,
            "start_time": st,
            "end_time": et,
            "text": text,
            "score": r.get("score"),
            "confidence_medical": r.get("confidence_medical"),
            "provenance_link": prov_link,
        })

    return {
        "answer_id": answer_id,
        "retrieved_chunks": lineage,
        "summary": {
            "avg_confidence": avg_conf,
        }
    }
