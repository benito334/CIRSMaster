from typing import Dict, Any, List

# Minimal QA summary generator; can be replaced with LLM call if desired

def summarize_alignment(result: Dict[str, Any]) -> str:
    cov = result.get("alignment_coverage", 0.0)
    agr = result.get("agreement_score", 0.0)
    weak = result.get("weak_claims", 0)
    if cov >= 0.9 and agr >= 0.85 and weak == 0:
        return "All claims appear well-aligned with retrieved evidence."
    notes: List[str] = []
    if cov < 0.9:
        notes.append(f"coverage={cov:.2f} below target")
    if agr < 0.85:
        notes.append(f"agreement={agr:.2f} below target")
    if weak > 0:
        notes.append(f"{weak} weakly supported sentences")
    return "; ".join(notes) or "Mixed alignment results."
