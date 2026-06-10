# Project knowledge folder

This is the AI's project knowledge base — the equivalent of uploading files to a
Claude Project. At answer time, the relevant passages from these files are
retrieved (pure-Python BM25, no GPU) and handed to the model as context; the
model then answers naturally in its own words.

## Add your files

```bash
python -m gpt_oss.brain.ingest "C:/path/to/your/files"   # extracts .txt/.md/.pdf
python -m gpt_oss.brain.ingest --list                    # show what's indexed
```

## Privacy

Files in this folder are **git-ignored by default** (see `.gitignore`) so
personal content does not get pushed to a public repo. They will NOT be present
on a remote deploy (e.g. Railway) unless you either:

1. Force-add specific files: `git add -f gpt_oss/brain/knowledge/<file>.txt`, or
2. Mount them via a volume and point `BRAIN_KNOWLEDGE_DIR` at it, or
3. Make the repo private and commit them.

## Config

| Env var | Default | Effect |
| --- | --- | --- |
| `BRAIN_KNOWLEDGE_DIR` | this folder | where knowledge files are read from |
| `ENABLE_KNOWLEDGE` | `1` | set `0` to disable retrieval |
