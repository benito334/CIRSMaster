import argparse
import json
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List

from dotenv import load_dotenv
load_dotenv()

from config import PDF_INPUT_PATH, EPUB_INPUT_PATH, OUTPUT_PATH, RUN_TAG, DOCS_INDEX

try:
    import fitz  # PyMuPDF
except Exception:
    fitz = None

try:
    from ebooklib import epub
except Exception:
    epub = None


def ensure_dir(p: Path):
    p.mkdir(parents=True, exist_ok=True)


def timestamp_tag() -> str:
    return datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")


def load_index() -> Dict[str, Dict]:
    p = Path(DOCS_INDEX)
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def save_index(idx: Dict[str, Dict]):
    p = Path(DOCS_INDEX)
    ensure_dir(p.parent)
    p.write_text(json.dumps(idx, indent=2), encoding="utf-8")


def pdf_extract_text(pdf_path: Path) -> List[str]:
    if fitz is None:
        raise RuntimeError("PyMuPDF (fitz) not installed in docs_ingest image")
    doc = fitz.open(str(pdf_path))
    pages: List[str] = []
    for page in doc:
        pages.append(page.get_text("text"))
    doc.close()
    return pages


def epub_extract_text(epub_path: Path) -> List[str]:
    if epub is None:
        raise RuntimeError("ebooklib not installed in docs_ingest image")
    book = epub.read_epub(str(epub_path))
    texts: List[str] = []
    for item in book.get_items_of_type(9):  # DOCUMENT
        try:
            content = item.get_content().decode("utf-8", errors="ignore")
            # very simple HTML strip
            text = content
            for tag in ["<br>", "<br/>", "<br />"]:
                text = text.replace(tag, "\n")
            # remove all remaining tags crudely
            import re
            text = re.sub(r"<[^>]+>", " ", text)
            texts.append(text)
        except Exception:
            continue
    return texts


def build_sidecar_from_blocks(blocks: List[str]) -> Dict:
    segments = []
    t = 0.0
    for i, txt in enumerate(blocks):
        clean = (txt or "").strip()
        if not clean:
            continue
        segments.append({
            "start_time": float(t),
            "end_time": float(t),
            "speaker": "DOC",
            "text": clean,
            "confidence": None,
        })
    full_text = "\n\n".join([s["text"] for s in segments])
    return {"segments": segments, "full_text": full_text}


def write_outputs(base_out: Path, run_tag: str, stem: str, sidecar: Dict, media_kind: str = "document") -> Path:
    # Keep parity with transcript layout; store under /data/transcripts/docs/versions/<tag>/
    out_dir = base_out / "docs" / "versions" / run_tag
    ensure_dir(out_dir)
    out_path = out_dir / f"{stem}.json"
    out_path.write_text(json.dumps(sidecar, indent=2), encoding="utf-8")
    return out_path


def scan_files(root: Path, exts: List[str]) -> List[Path]:
    files: List[Path] = []
    for dirpath, _, fns in os.walk(root):
        for fn in fns:
            if fn.lower().endswith(tuple(exts)):
                files.append(Path(dirpath) / fn)
    return sorted(files)


def move_to_processed(path: Path):
    try:
        dest = path.parent / "processed"
        dest.mkdir(parents=True, exist_ok=True)
        new_path = dest / path.name
        path.replace(new_path)
    except Exception:
        # best-effort; non-fatal on failure
        pass


def main():
    ap = argparse.ArgumentParser(description="Docs ingestion: PDF/EPUB to transcript sidecars")
    ap.add_argument("--pdf-input", type=str, default=PDF_INPUT_PATH)
    ap.add_argument("--epub-input", type=str, default=EPUB_INPUT_PATH)
    ap.add_argument("--tag", type=str, default=None)
    args = ap.parse_args()

    run_tag = args.tag or RUN_TAG or timestamp_tag()

    idx = load_index()
    out_root = Path(OUTPUT_PATH)

    # PDFs
    pdf_root = Path(args.pdf_input)
    if pdf_root.exists():
        for f in scan_files(pdf_root, [".pdf"]):
            key = f"pdf::{str(f)}"
            if idx.get(key):
                continue
            pages = pdf_extract_text(f)
            sidecar = build_sidecar_from_blocks(pages)
            out_path = write_outputs(out_root, run_tag, f.stem, sidecar)
            idx[key] = {"in": str(f), "out": str(out_path), "run_tag": run_tag}
            save_index(idx)
            move_to_processed(f)

    # EPUBs
    epub_root = Path(args.epub_input)
    if epub_root.exists():
        for f in scan_files(epub_root, [".epub"]):
            key = f"epub::{str(f)}"
            if idx.get(key):
                continue
            chapters = epub_extract_text(f)
            sidecar = build_sidecar_from_blocks(chapters)
            out_path = write_outputs(out_root, run_tag, f.stem, sidecar)
            idx[key] = {"in": str(f), "out": str(out_path), "run_tag": run_tag}
            save_index(idx)
            move_to_processed(f)

    print(json.dumps({"status": "ok", "run_tag": run_tag}, indent=2))


if __name__ == "__main__":
    main()
