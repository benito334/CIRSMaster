from typing import List, Dict, Any, Tuple
import re
import numpy as np

from .config import EMBED_MODEL, ALIGNMENT_MIN_SCORE, USE_GPU

_model = None


def _device() -> str:
    if USE_GPU:
        try:
            import torch
            return "cuda" if torch.cuda.is_available() else "cpu"
        except Exception:
            return "cpu"
    return "cpu"


def _load_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer(EMBED_MODEL, device=_device())
    return _model


def split_sentences(text: str) -> List[str]:
    # Lightweight sentence splitter; replace with spaCy for higher quality if desired
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [p.strip() for p in parts if p.strip()]


def embed_texts(texts: List[str]) -> np.ndarray:
    model = _load_model()
    vecs = model.encode(texts, convert_to_numpy=True, normalize_embeddings=True, show_progress_bar=False)
    return vecs


def align_answer_to_chunks(answer_text: str, chunks: List[Dict[str, Any]], top_k: int = 3) -> Dict[str, Any]:
    sentences = split_sentences(answer_text)
    if not sentences:
        return {
            "sentence_alignments": [],
            "alignment_coverage": 0.0,
            "agreement_score": 0.0,
            "weak_claims": 0,
        }

    sent_vecs = embed_texts(sentences)
    chunk_texts = [c.get("text", "") for c in chunks]
    if not chunk_texts:
        return {
            "sentence_alignments": [
                {"sentence": s, "chunk_ids": [], "alignment_score": 0.0} for s in sentences
            ],
            "alignment_coverage": 0.0,
            "agreement_score": 0.0,
            "weak_claims": len(sentences),
        }
    chunk_vecs = embed_texts(chunk_texts)

    # cosine similarities (sentences x chunks)
    sims = sent_vecs @ chunk_vecs.T

    sentence_alignments: List[Dict[str, Any]] = []
    covered = 0
    scores_for_agreement: List[float] = []
    weak_claims = 0

    for i, s in enumerate(sentences):
        row = sims[i]
        idx_sorted = np.argsort(-row)  # descending
        chosen: List[str] = []
        top_scores: List[float] = []
        for j in idx_sorted[:top_k]:
            score = float(row[j])
            if score >= ALIGNMENT_MIN_SCORE:
                cid = chunks[j].get("chunk_id") or f"idx_{j}"
                chosen.append(cid)
                top_scores.append(score)
        max_score = float(np.max(row)) if row.size else 0.0
        if chosen:
            covered += 1
            scores_for_agreement.append(float(np.mean(top_scores)))
        else:
            weak_claims += 1
        sentence_alignments.append({
            "sentence": s,
            "chunk_ids": chosen,
            "alignment_score": float(np.mean(top_scores)) if top_scores else max_score,
        })

    alignment_coverage = float(covered / max(1, len(sentences)))
    agreement_score = float(np.mean(scores_for_agreement)) if scores_for_agreement else 0.0

    return {
        "sentence_alignments": sentence_alignments,
        "alignment_coverage": alignment_coverage,
        "agreement_score": agreement_score,
        "weak_claims": weak_claims,
    }
