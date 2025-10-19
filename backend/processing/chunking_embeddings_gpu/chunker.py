import json
from pathlib import Path
from typing import List, Dict, Any, Optional
import uuid

from config import CHUNK_SIZE_TOKENS, CHUNK_OVERLAP_TOKENS


def _token_count(text: str) -> int:
    # Lightweight token count
    return len(text.split())


def _join_with_overlap(buffer: List[Dict[str, Any]]) -> str:
    return " ".join(seg["text_validated"].strip() for seg in buffer if seg.get("text_validated"))


def chunk_validated_segments(
    segments: List[Dict[str, Any]],
    source_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    chunks: List[Dict[str, Any]] = []
    buf: List[Dict[str, Any]] = []
    tokens = 0
    current_speaker = None

    for seg in segments:
        txt = seg.get("text_validated") or seg.get("text") or ""
        if not txt.strip():
            continue
        seg_tokens = _token_count(txt)
        speaker = seg.get("speaker", current_speaker)

        # Start new chunk when exceeding target size or speaker changed
        if buf and (tokens + seg_tokens > CHUNK_SIZE_TOKENS or (current_speaker is not None and speaker != current_speaker)):
            chunk_text = _join_with_overlap(buf)
            chunks.append({
                "chunk_id": str(uuid.uuid4()),
                "source_id": source_id,
                "start_time": float(buf[0].get("start_time", buf[0].get("start", 0.0))),
                "end_time": float(buf[-1].get("end_time", buf[-1].get("end", 0.0))),
                "speaker": current_speaker or buf[0].get("speaker", "SPEAKER_00"),
                "text": chunk_text,
                "validation_confidence": float(sum(
                    (s.get("confidence_medical", 0.9) + s.get("confidence_contextual", 0.9)) / 2.0 for s in buf
                ) / max(1, len(buf))),
                "topic_tags": [],
                "entities": [],
            })
            # Overlap
            if CHUNK_OVERLAP_TOKENS > 0:
                # retain tail tokens for continuity
                retained: List[Dict[str, Any]] = []
                t = 0
                for s in reversed(buf):
                    t += _token_count(s.get("text_validated", ""))
                    retained.insert(0, s)
                    if t >= CHUNK_OVERLAP_TOKENS:
                        break
                buf = retained
                tokens = sum(_token_count(s.get("text_validated", "")) for s in buf)
            else:
                buf = []
                tokens = 0
        # Append current seg
        buf.append({
            "start_time": seg.get("start_time", seg.get("start")),
            "end_time": seg.get("end_time", seg.get("end")),
            "speaker": seg.get("speaker", "SPEAKER_00"),
            "text_validated": txt,
            "confidence_medical": seg.get("confidence_medical", 0.9),
            "confidence_contextual": seg.get("confidence_contextual", 0.9),
        })
        tokens += seg_tokens
        current_speaker = speaker

    if buf:
        chunk_text = _join_with_overlap(buf)
        chunks.append({
            "chunk_id": str(uuid.uuid4()),
            "source_id": source_id,
            "start_time": float(buf[0].get("start_time", buf[0].get("start", 0.0))),
            "end_time": float(buf[-1].get("end_time", buf[-1].get("end", 0.0))),
            "speaker": current_speaker or buf[0].get("speaker", "SPEAKER_00"),
            "text": chunk_text,
            "validation_confidence": float(sum(
                (s.get("confidence_medical", 0.9) + s.get("confidence_contextual", 0.9)) / 2.0 for s in buf
            ) / max(1, len(buf))),
            "topic_tags": [],
            "entities": [],
        })

    return chunks


def write_chunks_json(out_dir: Path, stem: str, chunks: List[Dict[str, Any]]) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{stem}.json"
    out_path.write_text(json.dumps(chunks, indent=2), encoding="utf-8")
    return out_path
