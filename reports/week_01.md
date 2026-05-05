# Week 1: Data Collection

## Deliverables
- [x] Crawl `temple.edu` at scale (target **20000** unique docs).

## Results
- Raw JSONL lines: **71876** (includes duplicates from restarts).
- Deduped unique `docno` count: **42217** → `data/raw/corpus_deduped.jsonl`.

## Commands
```bash
.venv/bin/python3 -m src.dedupe_corpus
```
