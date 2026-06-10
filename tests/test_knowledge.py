"""Tests for the project knowledge base (BM25 retrieval)."""

from gpt_oss.brain import knowledge
from gpt_oss.brain.knowledge import KnowledgeBase, _chunk, _load_passages, format_for_prompt


def _kb_from(texts):
    """Build a KnowledgeBase directly from (source, text) pairs."""
    from gpt_oss.brain.knowledge import Passage, _tokenize

    passages = []
    for source, text in texts:
        for ch in _chunk(text):
            toks = _tokenize(ch)
            if toks:
                passages.append(Passage(source, ch, tuple(toks), len(toks)))
    return KnowledgeBase(passages)


def test_retrieval_ranks_relevant_passage_first():
    kb = _kb_from([
        ("astro.txt", "Venus in the ninth house as atmakaraka teaches a karmic lesson about the father and dharma."),
        ("security.txt", "A buffer overflow occurs when input exceeds the allocated stack space."),
        ("comedy.txt", "Deadpan delivery means the narrator does not know they are funny."),
    ])
    hits = kb.retrieve("what does venus in the ninth house mean", k=2)
    assert hits, "expected at least one hit"
    assert hits[0].source == "astro.txt"


def test_retrieval_returns_nothing_for_unrelated_query():
    kb = _kb_from([("astro.txt", "Venus in the ninth house as atmakaraka.")])
    assert kb.retrieve("kubernetes ingress controller tls termination") == []


def test_empty_kb_is_safe():
    kb = KnowledgeBase([])
    assert kb.retrieve("anything") == []


def test_chunking_splits_on_paragraphs():
    text = "para one.\n\n" + ("x" * 50 + "\n\n") * 60
    chunks = _chunk(text)
    assert len(chunks) > 1
    assert all(len(c) <= 1200 for c in chunks)  # ~_CHUNK_CHARS with slack


def test_format_for_prompt_labels_sources_and_instructs_natural_answer():
    from gpt_oss.brain.knowledge import Hit

    block = format_for_prompt([Hit("notes.txt", "the moon rules emotion", 1.0)])
    assert "PROJECT KNOWLEDGE" in block
    assert "notes.txt" in block
    assert "OWN WORDS" in block.upper()


def test_format_for_prompt_empty_is_none():
    assert format_for_prompt([]) is None


def test_retrieve_respects_disable_flag(monkeypatch):
    monkeypatch.setenv("ENABLE_KNOWLEDGE", "0")
    assert knowledge.retrieve("venus ninth house") == []


def test_load_passages_missing_dir_is_empty(tmp_path):
    assert _load_passages(tmp_path / "does_not_exist") == []
