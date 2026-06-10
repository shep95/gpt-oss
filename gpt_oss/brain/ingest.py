"""
Ingest files into the project knowledge base — the "upload to the project" step.

Point it at a folder (or individual files). It extracts text from .txt/.md/.pdf
and writes normalized .txt files into the knowledge directory, where the
retriever (knowledge.py) will pick them up. This is the equivalent of dropping
files into a Claude Project.

    python -m gpt_oss.brain.ingest "C:/path/to/your/files"
    python -m gpt_oss.brain.ingest file1.pdf notes.txt --dest gpt_oss/brain/knowledge
    python -m gpt_oss.brain.ingest "C:/files" --list   # show what's indexed

PDF extraction needs pypdf (`pip install pypdf`); .txt/.md need nothing.
"""

import argparse
import os
import re
from pathlib import Path

_DEFAULT_DEST = Path(__file__).resolve().parent / "knowledge"
_TEXT_EXT = {".txt", ".md"}
_PDF_EXT = {".pdf"}


def _safe_name(name: str) -> str:
    stem = re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("_")
    return (stem or "file") + ".txt"


def _extract_pdf(path: Path) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as exc:  # pragma: no cover - environment dependent
        raise SystemExit(
            "pypdf is required to ingest PDFs. Run: pip install pypdf"
        ) from exc
    reader = PdfReader(str(path))
    return "\n\n".join((page.extract_text() or "") for page in reader.pages)


def _extract(path: Path) -> str:
    ext = path.suffix.lower()
    if ext in _TEXT_EXT:
        return path.read_text(encoding="utf-8", errors="replace")
    if ext in _PDF_EXT:
        return _extract_pdf(path)
    return ""


def _iter_files(targets: list[str]):
    for t in targets:
        p = Path(t)
        if p.is_dir():
            for child in sorted(p.glob("**/*")):
                if child.is_file() and child.suffix.lower() in _TEXT_EXT | _PDF_EXT:
                    yield child
        elif p.is_file():
            yield p


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest files into the knowledge base")
    parser.add_argument("targets", nargs="*", help="folders or files to ingest")
    parser.add_argument(
        "--dest", default=str(_DEFAULT_DEST), help="knowledge directory to write into"
    )
    parser.add_argument("--list", action="store_true", help="list current knowledge files")
    args = parser.parse_args()

    dest = Path(args.dest)
    dest.mkdir(parents=True, exist_ok=True)

    if args.list:
        files = sorted(dest.glob("*.txt"))
        total = sum(f.stat().st_size for f in files)
        print(f"Knowledge dir: {dest}")
        print(f"Files: {len(files)} | total {round(total/1_000_000, 2)} MB")
        for f in files:
            print(f"  - {f.name} ({round(f.stat().st_size/1024)} KB)")
        return

    if not args.targets:
        parser.error("provide at least one folder or file to ingest (or use --list)")

    written = 0
    skipped = 0
    for src in _iter_files(args.targets):
        try:
            text = _extract(src).strip()
        except SystemExit:
            raise
        except Exception as exc:  # noqa: BLE001
            print(f"  skip {src.name}: {exc}")
            skipped += 1
            continue
        if not text:
            print(f"  skip {src.name}: no extractable text")
            skipped += 1
            continue
        out = dest / _safe_name(src.stem)
        out.write_text(text, encoding="utf-8")
        written += 1
        print(f"  + {src.name} -> {out.name} ({len(text)} chars)")

    print(f"\nDone. Wrote {written} file(s), skipped {skipped}. Knowledge dir: {dest}")


if __name__ == "__main__":
    main()
