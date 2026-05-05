# Bootstrap qrels (automation only)

`data/processed/qrels_bootstrap.tsv` labels the **BM25 rank-1** document per query as relevant.

This is **not** a TREC-style judgment set. For the course deliverable, replace it with pooled
human labels in `data/processed/qrels.tsv` and re-run:

- `src.evaluate_models`
- `src.bm25_sensitivity`
