from typing import List, Dict, Any, Tuple
import re

# Placeholder medical grounding validator
# Strategy: extract simple noun-like tokens from answer and verify presence in retrieved chunk texts.
# In future, replace with SciSpaCy/MedSpaCy entity linker to UMLS/RxNorm.

def _normalize(text: str) -> List[str]:
    toks = re.findall(r"[a-zA-Z][a-zA-Z\-]+", text.lower())
    # filter very short tokens
    return [t for t in toks if len(t) >= 4]


def validate_medical_grounding(answer: str, chunks: List[Dict[str, Any]]) -> Tuple[List[str], str]:
    ans_terms = set(_normalize(answer))
    ctx = " \n".join([c.get("text", "") for c in chunks]).lower()
    missing: List[str] = []
    for term in sorted(ans_terms):
        if term not in ctx:
            missing.append(term)
    if missing:
        note = f"Missing {len(missing)} terms from context."
    else:
        note = "All terms appear grounded in retrieved context."
    return missing[:20], note
