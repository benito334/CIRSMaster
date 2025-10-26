import argparse
import json
import os
import sys
import hashlib
import uuid
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

import numpy as np
import requests
import ffmpeg
from tqdm import tqdm

from dotenv import load_dotenv
load_dotenv()

# Suppress noisy third-party deprecation/move warnings emitted by pyannote/torchaudio/speechbrain
import warnings
warnings.filterwarnings(
    "ignore",
    message="torchaudio._backend.set_audio_backend has been deprecated",
    category=UserWarning,
)
warnings.filterwarnings(
    "ignore",
    message="torchaudio._backend.get_audio_backend has been deprecated",
    category=UserWarning,
)
warnings.filterwarnings(
    "ignore",
    message="`torchaudio.backend.common.AudioMetaData` has been moved",
    category=UserWarning,
)
warnings.filterwarnings(
    "ignore",
    message="Module 'speechbrain.pretrained' was deprecated",
    category=UserWarning,
)

PIPELINE_API = os.getenv("PIPELINE_API", "http://pipeline_controller:8021")

from config import (
    ASR_MODEL,
    ASR_COMPUTE_TYPE,
    ASR_DIARIZATION,
    OUTPUT_ROOT,
    INPUT_ROOT,
    DB_URL,
    PYANNOTE_AUTH_TOKEN,
    PROCESSED_INDEX,
    AUDIO_EXTS,
    VIDEO_EXTS,
)

# Lazy imports for heavy libs
_whisperx = None

def _import_whisperx():
    global _whisperx
    if _whisperx is None:
        import whisperx
        _whisperx = whisperx
    return _whisperx


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def ensure_dir(p: Path):
    p.mkdir(parents=True, exist_ok=True)


def load_index() -> Dict[str, Any]:
    p = Path(PROCESSED_INDEX)
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def save_index(idx: Dict[str, Any]):
    p = Path(PROCESSED_INDEX)
    ensure_dir(p.parent)
    p.write_text(json.dumps(idx, indent=2), encoding="utf-8")


def detect_media_type(path: Path) -> str:
    ext = path.suffix.lower()
    if ext in AUDIO_EXTS:
        return "audio"
    if ext in VIDEO_EXTS:
        return "video"
    return "unknown"


def extract_audio(video_path: Path, wav_path: Path, sr: int = 16000):
    ensure_dir(wav_path.parent)
    (
        ffmpeg
        .input(str(video_path))
        .output(str(wav_path), ac=1, ar=sr, format='wav')
        .overwrite_output()
        .run(quiet=True)
    )


def to_timestamp_tag() -> str:
    return datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")


def run_asr(audio_path: Path, device: str = "cuda") -> Dict[str, Any]:
    whisperx = _import_whisperx()

    try:
        model = whisperx.load_model(
            ASR_MODEL,
            device=device,
            compute_type=ASR_COMPUTE_TYPE,
        )
        # Force English to skip language detection and speed up inference
        result = model.transcribe(str(audio_path), language="en")

        # Alignment model (optional but improves word timings)
        try:
            model_a, metadata = whisperx.load_align_model(language_code=result.get("language", "en"), device=device)
            result = whisperx.align(result["segments"], model_a, metadata, str(audio_path), device)
        except Exception:
            # Fallback to unaligned segments
            pass

        return result
    except TypeError as e:
        # Known mismatch between whisperx and faster-whisper TranscriptionOptions signatures.
        # Fallback to direct faster-whisper transcription.
        if "TranscriptionOptions" in str(e) or "unexpected keyword" in str(e):
            from faster_whisper import WhisperModel
            import librosa

            model = WhisperModel(ASR_MODEL, device=device, compute_type=ASR_COMPUTE_TYPE)
            # Pre-decode to 16k mono numpy to avoid PyAV path
            audio_np, sr = librosa.load(str(audio_path), sr=16000, mono=True)
            segments_iter, info = model.transcribe(audio_np, language="en")
            segments = []
            for seg in segments_iter:
                segments.append({
                    "start": float(getattr(seg, "start", 0.0)),
                    "end": float(getattr(seg, "end", 0.0)),
                    "text": getattr(seg, "text", ""),
                    "avg_logprob": getattr(seg, "avg_logprob", None),
                })
            return {"language": getattr(info, "language", None), "segments": segments}
        else:
            raise


def run_diarization(audio_path: Path) -> Optional[List[Dict[str, Any]]]:
    if not ASR_DIARIZATION:
        return None
    if not PYANNOTE_AUTH_TOKEN:
        print("[diarization] PYANNOTE_AUTH_TOKEN not set; skipping.")
        return None

    whisperx = _import_whisperx()
    try:
        diarize_model = whisperx.DiarizationPipeline(use_auth_token=PYANNOTE_AUTH_TOKEN, device="cuda")
        diarize_segments = diarize_model(str(audio_path))
        # diarize_segments is a list of dicts with start, end, speaker
        return diarize_segments
    except Exception as e:
        print(f"[diarization] error: {e}; skipping")
        return None


def merge_speaker_labels(asr_segments: List[Dict[str, Any]], diarize_segments: Optional[List[Dict[str, Any]]]):
    if not diarize_segments:
        # Assign default single speaker
        for seg in asr_segments:
            seg["speaker"] = "SPEAKER_00"
        return asr_segments

    # Naive overlap-based assignment: choose diarization speaker overlapping segment mid-point
    def seg_mid(s):
        return (s["start"] + s["end"]) / 2.0

    for seg in asr_segments:
        mid = seg_mid(seg)
        speaker = "SPEAKER_00"
        for d in diarize_segments:
            if d.get("start", 0) <= mid <= d.get("end", 0):
                speaker = d.get("speaker", "SPEAKER_00")
                break
        seg["speaker"] = speaker
    return asr_segments


def build_sidecar(asr_result: Dict[str, Any]) -> Dict[str, Any]:
    # Normalize to required schema
    segments_out = []
    segments = asr_result.get("segments", asr_result)
    for s in segments:
        segments_out.append({
            "start_time": float(s.get("start", 0.0)),
            "end_time": float(s.get("end", 0.0)),
            "speaker": s.get("speaker", "SPEAKER_00"),
            "text": s.get("text", "").strip(),
            "confidence": float(s.get("avg_logprob", np.nan)) if s.get("avg_logprob") is not None else None,
        })
    full_text = "\n".join([s["text"].strip() for s in segments_out if s.get("text")])
    return {"segments": segments_out, "full_text": full_text}


def write_outputs(base_out_dir: Path, media_kind: str, input_path: Path, sidecar: Dict[str, Any], run_tag: str) -> Dict[str, Path]:
    # Directory layout per spec
    if media_kind == "audio":
        out_dir = base_out_dir / "audio" / "versions" / run_tag
    else:
        out_dir = base_out_dir / "videos" / "versions" / run_tag
    ensure_dir(out_dir)

    stem = input_path.stem
    json_path = out_dir / f"{stem}.json"
    txt_path = out_dir / f"{stem}.txt"

    Path(json_path).write_text(json.dumps(sidecar, indent=2), encoding="utf-8")
    Path(txt_path).write_text(sidecar.get("full_text", ""), encoding="utf-8")

    return {"json": json_path, "txt": txt_path}


def move_to_processed(path: Path):
    try:
        dest_dir = path.parent / "processed"
        ensure_dir(dest_dir)
        shutil.move(str(path), str(dest_dir / path.name))
    except Exception:
        # Non-fatal: best-effort move
        pass


def maybe_write_db(sidecar: Dict[str, Any], source_id: Optional[str] = None):
    if not DB_URL or not source_id:
        return False
    try:
        import psycopg2
        import psycopg2.extras as extras
        conn = psycopg2.connect(DB_URL)
        conn.autocommit = True
        cur = conn.cursor()
        transcript_id = str(uuid.uuid4())
        payload = {
            "transcript_id": transcript_id,
            "source_id": source_id,
            "full_text": sidecar.get("full_text", ""),
            "segments_json": json.dumps(sidecar.get("segments", [])),
            "quality_metrics": json.dumps({}),
            "asr_model_version": ASR_MODEL,
            "validation_version": None,
        }
        sql = (
            "INSERT INTO cirs.transcripts (transcript_id, source_id, full_text, segments_json, quality_metrics, asr_model_version, validation_version) "
            "VALUES (%(transcript_id)s, %(source_id)s, %(full_text)s, %(segments_json)s, %(quality_metrics)s, %(asr_model_version)s, %(validation_version)s)"
        )
        cur.execute(sql, payload)
        cur.close()
        conn.close()
        return True
    except Exception as e:
        print(f"[db] Skipping DB write (error: {e})")
        return False


def process_media_file(path: Path, run_tag: str, source_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    media_kind = detect_media_type(path)
    if media_kind == "unknown":
        return None

    # Compute file hash for resumability and derive a stable UUID for pipeline status
    file_hash = sha256_file(path)
    try:
        file_id = str(uuid.uuid5(uuid.NAMESPACE_URL, str(path)))
    except Exception:
        file_id = str(uuid.uuid4())
    index = load_index()
    if index.get(file_hash):
        print(f"[skip] already processed: {path}")
        return None

    # Prepare audio
    if media_kind == "video":
        tmp_wav = Path("/tmp") / f"{path.stem}_{uuid.uuid4().hex[:8]}.wav"
        extract_audio(path, tmp_wav)
        audio_for_asr = tmp_wav
    else:
        audio_for_asr = path

    # Notify start
    try:
        try:
            requests.post(f"{PIPELINE_API}/status/update", json={
                "file_id": file_id,
                "stage": "asr",
                "done": False,
                "error": None,
                "filename": str(path),
                "file_type": media_kind,
                "run_tag": run_tag,
            }, timeout=2)
        except Exception:
            pass
        asr_result = run_asr(audio_for_asr)
        diar_segments = run_diarization(audio_for_asr)
        segments = asr_result.get("segments", asr_result)
        segments = merge_speaker_labels(segments, diar_segments)
        asr_result["segments"] = segments
        sidecar = build_sidecar(asr_result)

        outputs = write_outputs(Path(OUTPUT_ROOT), media_kind, path, sidecar, run_tag)
        maybe_write_db(sidecar, source_id=source_id)

        # Update resumability index
        index[file_hash] = {
            "path": str(path),
            "run_tag": run_tag,
            "outputs": {k: str(v) for k, v in outputs.items()},
        }
        save_index(index)
        # Move original source file to processed subfolder on success
        move_to_processed(path)
        # Notify success
        try:
            requests.post(f"{PIPELINE_API}/status/update", json={
                "file_id": file_id,
                "stage": "asr",
                "done": True,
                "error": None,
                "filename": str(path),
                "file_type": media_kind,
                "run_tag": run_tag,
            }, timeout=2)
        except Exception:
            pass
        return {"path": str(path), "outputs": outputs}
    finally:
        if media_kind == "video" and 'audio_for_asr' in locals() and Path(audio_for_asr).exists():
            try:
                Path(audio_for_asr).unlink()
            except Exception:
                pass


def scan_inputs(root: Path) -> List[Path]:
    files = []
    for dirpath, _, filenames in os.walk(root):
        for fn in filenames:
            p = Path(dirpath) / fn
            if detect_media_type(p) != "unknown":
                files.append(p)
    return files


def main():
    parser = argparse.ArgumentParser(description="ASR GPU Service: WhisperX + optional diarization")
    parser.add_argument("--input", type=str, default=INPUT_ROOT, help="Input directory to scan for media")
    parser.add_argument("--source-id", type=str, default=None, help="Optional source_id for DB write (FK must exist)")
    parser.add_argument("--tag", type=str, default=None, help="Optional run tag (defaults to UTC timestamp)")

    args = parser.parse_args()

    run_tag = args.tag or os.getenv("RUN_TAG") or to_timestamp_tag()
    input_root = Path(args.input)
    if not input_root.exists():
        print(f"Input path not found: {input_root}")
        sys.exit(1)

    media_files = scan_inputs(input_root)
    if not media_files:
        print("No media files found.")
        return

    print(f"Found {len(media_files)} files. Starting transcription. Model={ASR_MODEL}, Diarization={ASR_DIARIZATION}")
    for p in tqdm(media_files, desc="Transcribing"):
        process_media_file(p, run_tag, source_id=args.source_id)

    print("Done.")


if __name__ == "__main__":
    main()
