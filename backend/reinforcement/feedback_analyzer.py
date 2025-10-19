from typing import Dict, Any
from datetime import datetime, timedelta

from .config import DB_URL, WINDOW_DAYS


def _range_clause():
    return f"created_at >= NOW() - INTERVAL '{WINDOW_DAYS} days'"


def aggregate_metrics() -> Dict[str, Any]:
    metrics = {
        "avg_confidence": None,
        "avg_agreement": None,
        "hallucination_rate": None,
        "weak_claim_rate": None,
    }
    if not DB_URL:
        return metrics
    try:
        import psycopg2
        conn = psycopg2.connect(DB_URL)
        cur = conn.cursor()
        # Confidence and hallucination from evaluations
        cur.execute(
            f"""
            SELECT AVG(confidence_answer), AVG(hallucination_risk)
            FROM cirs.answer_evaluations
            WHERE {_range_clause()}
            """
        )
        row = cur.fetchone()
        if row:
            metrics["avg_confidence"] = float(row[0]) if row[0] is not None else None
            # interpret hallucination rate as mean hallucination_risk
            metrics["hallucination_rate"] = float(row[1]) if row[1] is not None else None

        # Agreement and weak claims from alignment
        cur.execute(
            f"""
            SELECT AVG(agreement_score), AVG(CASE WHEN weak_claims>0 THEN 1 ELSE 0 END::int)
            FROM cirs.answer_alignment
            WHERE {_range_clause()}
            """
        )
        row = cur.fetchone()
        if row:
            metrics["avg_agreement"] = float(row[0]) if row[0] is not None else None
            metrics["weak_claim_rate"] = float(row[1]) if row[1] is not None else None

        cur.close(); conn.close()
    except Exception:
        pass
    return metrics
