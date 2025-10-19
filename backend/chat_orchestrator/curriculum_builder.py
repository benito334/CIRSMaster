from typing import List, Dict, Any

def build_module(topic: str, chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
    # Very simple baseline: group chunks and produce objectives + quiz seed
    texts = [c.get("text", "") for c in chunks if c.get("text")]
    objectives = [
        f"Understand key aspects of {topic}",
        f"Identify clinical indicators related to {topic}",
    ]
    sections = []
    if texts:
        sections.append({
            "title": f"Overview of {topic}",
            "summary": texts[0][:500] + ("..." if len(texts[0]) > 500 else ""),
            "citations": [
                {"chunk_id": c.get("chunk_id"), "source_id": c.get("source_id"), "start_time": c.get("start_time"), "end_time": c.get("end_time")}
                for c in chunks[:5]
            ],
        })
    quiz = [
        {"question": f"List two core points about {topic}.", "answer": "", "type": "short"}
    ]
    return {
        "topic": topic,
        "objectives": objectives,
        "sections": sections,
        "quiz": quiz,
    }
