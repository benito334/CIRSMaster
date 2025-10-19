from typing import List, Dict, Any, Tuple
import numpy as np
from .similarity import embed_texts, cosine_similarity


def compute_confidence(answer: str, chunks: List[Dict[str, Any]]) -> float:
    texts = [answer] + [c.get("text", "") for c in chunks]
    vecs = embed_texts(texts)
    ans_vec = vecs[0]
    chunk_vecs = vecs[1:]
    if len(chunk_vecs) == 0:
        return 0.0
    sims = []
    for i in range(chunk_vecs.shape[0]):
        sims.append(cosine_similarity(ans_vec, chunk_vecs[i]))
    return float(np.mean(sims))


def compute_support_ratio(answer: str, chunks: List[Dict[str, Any]], n: int = 3) -> float:
    # Simple n-gram support: fraction of answer n-grams found in any chunk text
    def ngrams(tokens: List[str], k: int) -> List[Tuple[str, ...]]:
        return [tuple(tokens[i:i+k]) for i in range(max(0, len(tokens) - k + 1))]

    ans_tokens = answer.lower().split()
    ans_ngrams = set(ngrams(ans_tokens, n))
    if not ans_ngrams:
        return 0.0

    chunk_text = "\n".join([c.get("text", "").lower() for c in chunks])
    chunk_tokens = chunk_text.split()
    chunk_ngrams = set(ngrams(chunk_tokens, n))

    supported = sum(1 for g in ans_ngrams if g in chunk_ngrams)
    return float(supported / max(1, len(ans_ngrams)))


def compute_citation_density(citations: List[Dict[str, Any]], answer_length_tokens: int) -> float:
    if answer_length_tokens <= 0:
        return 0.0
    cites = max(1, len(citations)) if citations else 0
    # A simple heuristic: more citations per ~150 tokens increases density
    return float(min(1.0, (cites * 150.0) / max(1, answer_length_tokens)))


def score_answer(answer: str, chunks: List[Dict[str, Any]], citations: List[Dict[str, Any]]) -> Dict[str, Any]:
    conf = compute_confidence(answer, chunks)
    support = compute_support_ratio(answer, chunks, n=3)
    citation_density = compute_citation_density(citations, len(answer.split()))
    hallucination_risk = float((1.0 - conf) * (1.0 - citation_density))
    return {
        "confidence_answer": conf,
        "support_ratio": support,
        "citation_density": citation_density,
        "hallucination_risk": hallucination_risk,
    }
