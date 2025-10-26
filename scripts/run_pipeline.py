#!/usr/bin/env python3
"""Orchestrate the ASR ➝ validation ➝ chunking pipeline.

This helper stitches together the existing CLI entry points so a single
command can be executed locally or in CI to rebuild the retrieval index.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _parse_json_tail(output: str) -> Dict[str, Any]:
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    for line in reversed(lines):
        try:
            return json.loads(line)
        except json.JSONDecodeError:
            continue
    return {"stdout": output.strip()}


def _run_step(name: str, module: str, args: list[str], env: Dict[str, str], cwd: Path) -> Dict[str, Any]:
    cmd = [sys.executable, "-m", module, *args]
    print(f"\n==> [{name}] Running: {' '.join(cmd)}")
    result = subprocess.run(
        cmd,
        cwd=cwd,
        env=env,
        text=True,
        capture_output=True,
    )
    if result.stdout:
        print(result.stdout.rstrip())
    if result.stderr:
        print(result.stderr.rstrip(), file=sys.stderr)
    if result.returncode != 0:
        raise subprocess.CalledProcessError(result.returncode, cmd)
    return _parse_json_tail(result.stdout)


def _maybe_clear_indexes() -> None:
    from backend.transcription.asr_gpu import config as asr_config
    from backend.processing.validation_gpu import config as val_config
    from backend.processing.chunking_embeddings_gpu import config as chunk_config

    Path(asr_config.PROCESSED_INDEX).unlink(missing_ok=True)
    Path(val_config.VALIDATED_INDEX).unlink(missing_ok=True)
    Path(chunk_config.EMBEDDED_INDEX).unlink(missing_ok=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the end-to-end processing pipeline.")
    parser.add_argument("--ingestion-root", type=Path, default=Path("data/ingestion"), help="Directory containing raw media inputs.")
    parser.add_argument("--transcript-root", type=Path, default=Path("data/transcripts"), help="Directory where ASR transcripts are written.")
    parser.add_argument("--validated-root", type=Path, default=Path("data/validated"), help="Directory for validation outputs.")
    parser.add_argument("--chunks-root", type=Path, default=Path("data/chunks"), help="Directory for chunked + embedded outputs.")
    parser.add_argument("--run-tag", type=str, default=None, help="Optional run tag applied to all stages (defaults to UTC timestamp).")
    parser.add_argument("--source-id", type=str, default=None, help="Optional source identifier propagated to ASR/validation DB writes.")
    parser.add_argument("--summary-path", type=Path, default=None, help="Where to write the JSON summary (defaults to data/pipeline_runs/<tag>.json).")
    parser.add_argument("--skip-asr", action="store_true", help="Skip the ASR stage.")
    parser.add_argument("--skip-validation", action="store_true", help="Skip the validation stage.")
    parser.add_argument("--skip-chunking", action="store_true", help="Skip the chunking/embedding stage.")
    parser.add_argument("--fresh", action="store_true", help="Remove resumability indexes before running.")
    return parser


def main(argv: Optional[list[str]] = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    repo_root = _repo_root()
    run_tag = args.run_tag or datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")

    ingestion_root = (repo_root / args.ingestion_root).resolve()
    transcript_root = (repo_root / args.transcript_root).resolve()
    validated_root = (repo_root / args.validated_root).resolve()
    chunks_root = (repo_root / args.chunks_root).resolve()

    for path in (transcript_root, validated_root, chunks_root):
        path.mkdir(parents=True, exist_ok=True)

    if args.fresh:
        _maybe_clear_indexes()

    base_env = os.environ.copy()
    base_env.setdefault("PYTHONPATH", str(repo_root))
    base_env["RUN_TAG"] = run_tag

    summaries: Dict[str, Any] = {}

    if not args.skip_asr:
        env = base_env.copy()
        env["INPUT_PATH"] = str(ingestion_root)
        env["OUTPUT_PATH"] = str(transcript_root)
        step_args = ["--input", str(ingestion_root), "--tag", run_tag]
        if args.source_id:
            step_args.extend(["--source-id", args.source_id])
        summaries["asr"] = _run_step(
            "ASR",
            "backend.transcription.asr_gpu.main",
            step_args,
            env,
            repo_root,
        )

    if not args.skip_validation:
        env = base_env.copy()
        env["INPUT_PATH"] = str(transcript_root)
        env["OUTPUT_PATH"] = str(validated_root)
        step_args = ["--input", str(transcript_root), "--tag", run_tag]
        if args.source_id:
            step_args.extend(["--source-id", args.source_id])
        summaries["validation"] = _run_step(
            "Validation",
            "backend.processing.validation_gpu.main",
            step_args,
            env,
            repo_root,
        )

    if not args.skip_chunking:
        env = base_env.copy()
        env["INPUT_PATH"] = str(validated_root)
        env["OUTPUT_PATH"] = str(chunks_root)
        step_args = ["--input", str(validated_root), "--tag", run_tag]
        summaries["chunking"] = _run_step(
            "Chunking",
            "backend.processing.chunking_embeddings_gpu.main",
            step_args,
            env,
            repo_root,
        )

    summary = {
        "run_tag": run_tag,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "steps": summaries,
    }

    summary_path = args.summary_path
    if summary_path is None:
        summary_dir = repo_root / "data" / "pipeline_runs"
        summary_dir.mkdir(parents=True, exist_ok=True)
        summary_path = summary_dir / f"{run_tag}.json"
    else:
        summary_path = summary_path if summary_path.is_absolute() else (repo_root / summary_path)
        summary_path.parent.mkdir(parents=True, exist_ok=True)

    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"\nPipeline summary written to {summary_path}")


if __name__ == "__main__":
    main()
