"""
Project knowledge base — the "upload files and it pulls from them" layer.

This mirrors how a Claude Project works: you drop your files into a knowledge
folder, and at answer time the relevant passages are RETRIEVED and handed to the
model as context. The model then answers naturally, in its own words — it does
not dump the files back at the user.

Two layers, kept separate on purpose:
  - doctrines.py / orchestrator.py = the BRAINS (how it thinks — personality).
  - knowledge.py (this file)       = the KNOWLEDGE (what it knows — your files).

Retrieval is pure-Python BM25 lexical search: deterministic, no model, no GPU,
no network, no third-party dependency. It runs fine on the stub backend. Build
the knowledge folder with `python -m gpt_oss.brain.ingest <your folder>`.

Config:
  BRAIN_KNOWLEDGE_DIR   directory of .txt/.md knowledge files
                        (default: gpt_oss/brain/knowledge/)
  ENABLE_KNOWLEDGE      0/false/off to disable retrieval (default: on)
"""

from __future__ import annotations

import math
import os
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Optional

_DEFAULT_DIR = Path(__file__).resolve().parent / "knowledge"

# BM25 parameters (standard defaults).
_K1 = 1.5
_B = 0.75

# Chunking: split source text into passages of roughly this many characters,
# on paragraph boundaries, so a retrieved hit is a coherent passage.
_CHUNK_CHARS = 1100
_CHUNK_OVERLAP = 150

_TOKEN_RE = re.compile(r"[a-z0-9]+")
_STOPWORDS = frozenset(
    """
    a an the and or but if then else of to in on at by for with from into over
    is are was were be been being it its this that these those as i you he she
    they we me my your our their his her them us do does did has have had not no
    yes so than too very can will just about above below up down out off again
    """.split()
)


def _knowledge_dir() -> Path:
    env = os.environ.get("BRAIN_KNOWLEDGE_DIR", "").strip()
    return Path(env) if env else _DEFAULT_DIR


def knowledge_enabled() -> bool:
    return os.environ.get("ENABLE_KNOWLEDGE", "1").strip() not in {
        "0", "false", "FALSE", "off", "OFF", "no", "NO", ""
    }


def _tokenize(text: str) -> list[str]:
    return [t for t in _TOKEN_RE.findall(text.lower()) if t not in _STOPWORDS and len(t) > 1]


def _chunk(text: str) -> list[str]:
    """Split text into overlapping, paragraph-aligned passages."""
    text = text.strip()
    if not text:
        return []
    paras = re.split(r"\n\s*\n", text)
    chunks: list[str] = []
    buf = ""
    for para in paras:
        para = para.strip()
        if not para:
            continue
        if len(buf) + len(para) + 2 <= _CHUNK_CHARS:
            buf = f"{buf}\n\n{para}" if buf else para
        else:
            if buf:
                chunks.append(buf)
            if len(para) <= _CHUNK_CHARS:
                buf = para
            else:
                # A single huge paragraph: hard-split with overlap.
                start = 0
                while start < len(para):
                    chunks.append(para[start : start + _CHUNK_CHARS])
                    start += _CHUNK_CHARS - _CHUNK_OVERLAP
                buf = ""
    if buf:
        chunks.append(buf)
    return chunks


@dataclass
class Passage:
    source: str          # filename the passage came from
    text: str            # the passage itself
    tokens: tuple[str, ...]
    length: int


@dataclass
class Hit:
    source: str
    text: str
    score: float


class KnowledgeBase:
    """In-memory BM25 index over the knowledge directory."""

    def __init__(self, passages: list[Passage]):
        self.passages = passages
        self.n = len(passages)
        self.avg_len = (sum(p.length for p in passages) / self.n) if self.n else 0.0
        # document frequency per term
        df: dict[str, int] = {}
        for p in passages:
            for term in set(p.tokens):
                df[term] = df.get(term, 0) + 1
        self.idf = {
            term: math.log(1 + (self.n - freq + 0.5) / (freq + 0.5))
            for term, freq in df.items()
        }

    def retrieve(self, query: str, k: int = 4, min_score: float = 0.1) -> list[Hit]:
        if self.n == 0:
            return []
        q_terms = _tokenize(query)
        if not q_terms:
            return []
        scored: list[Hit] = []
        for p in self.passages:
            score = 0.0
            tf: dict[str, int] = {}
            for t in p.tokens:
                tf[t] = tf.get(t, 0) + 1
            for term in q_terms:
                f = tf.get(term)
                if not f:
                    continue
                idf = self.idf.get(term, 0.0)
                denom = f + _K1 * (1 - _B + _B * p.length / (self.avg_len or 1))
                score += idf * (f * (_K1 + 1)) / denom
            if score > min_score:
                scored.append(Hit(source=p.source, text=p.text, score=score))
        scored.sort(key=lambda h: h.score, reverse=True)
        return scored[:k]


def _load_passages(directory: Path) -> list[Passage]:
    passages: list[Passage] = []
    if not directory.is_dir():
        return passages
    for path in sorted(directory.glob("**/*")):
        if path.suffix.lower() not in {".txt", ".md"} or not path.is_file():
            continue
        try:
            raw = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for chunk in _chunk(raw):
            toks = _tokenize(chunk)
            if toks:
                passages.append(
                    Passage(source=path.name, text=chunk, tokens=tuple(toks), length=len(toks))
                )
    return passages


@lru_cache(maxsize=1)
def _cached_kb(dir_key: str) -> KnowledgeBase:
    return KnowledgeBase(_load_passages(Path(dir_key)))


def get_kb() -> KnowledgeBase:
    """Return the (cached) knowledge base for the configured directory."""
    return _cached_kb(str(_knowledge_dir()))


def retrieve(query: str, k: int = 4) -> list[Hit]:
    """Top-k relevant passages for a query. Empty list if no knowledge exists."""
    if not knowledge_enabled():
        return []
    try:
        return get_kb().retrieve(query, k=k)
    except Exception:
        # Knowledge must never take the request down — degrade to no retrieval.
        return []


def format_for_prompt(hits: list[Hit], char_budget: int = 6000) -> Optional[str]:
    """Render retrieved passages as a PROJECT KNOWLEDGE block for the prompt."""
    if not hits:
        return None
    lines = [
        "=== PROJECT KNOWLEDGE (pulled from your uploaded files) ===",
        "Relevant passages retrieved for THIS question. Ground your answer in "
        "them and weave the facts into a natural reply IN YOUR OWN WORDS. Do not "
        "quote them verbatim, do not dump them, and do not mention that you "
        "retrieved anything. If they are not actually relevant, ignore them.",
        "",
    ]
    used = 0
    for h in hits:
        block = f"[from {h.source}]\n{h.text.strip()}"
        if used + len(block) > char_budget:
            break
        lines.append(block)
        lines.append("")
        used += len(block)
    return "\n".join(lines).strip()
