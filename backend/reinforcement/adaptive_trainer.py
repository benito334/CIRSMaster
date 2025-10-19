from typing import Dict, Any
from .config import DEFAULTS


def compute_adjustments(metrics: Dict[str, Any]) -> Dict[str, Any]:
    """
    Heuristic rules:
    - If avg_confidence < 0.8, decrease summary_temperature and raise retrieval_top_k
    - If avg_agreement < 0.85, increase chunk_overlap and retrieval_top_k
    - If hallucination_rate > 0.25, lower summary_temperature
    - If weak_claim_rate > 0.25, increase retrieval_top_k
    """
    out = dict(DEFAULTS)
    c = metrics.get("avg_confidence")
    a = metrics.get("avg_agreement")
    h = metrics.get("hallucination_rate")
    w = metrics.get("weak_claim_rate")

    if c is not None and c < 0.8:
        out["summary_temperature"] = max(0.1, out["summary_temperature"] - 0.1)
        out["retrieval_top_k"] = min(12, out["retrieval_top_k"] + 2)
    if a is not None and a < 0.85:
        out["chunk_overlap"] = min(300, out["chunk_overlap"] + 25)
        out["retrieval_top_k"] = min(12, out["retrieval_top_k"] + 2)
    if h is not None and h > 0.25:
        out["summary_temperature"] = max(0.1, out["summary_temperature"] - 0.1)
    if w is not None and w > 0.25:
        out["retrieval_top_k"] = min(12, out["retrieval_top_k"] + 2)

    return out
