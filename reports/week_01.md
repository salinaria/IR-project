# Week 1: Data Collection

## Deliverables
- [x] Crawl `temple.edu` at scale (current deduped corpus: **42217** docs).

## Results
- Raw JSONL lines: **71876** (includes duplicates from restarts).
- Deduped unique `docno` count: **42217** → `data/raw/corpus_deduped.jsonl`.

## Commands
```bash
.venv/bin/python3 -m src.dedupe_corpus
```
