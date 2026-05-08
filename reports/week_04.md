# Week 4: Pooling and Relevance Judgments

## Deliverables
- [x] TREC-style pool (BM25 + TF-IDF + QL, depth 10).
- [x] Judgments file `data/processed/qrels.tsv` (**2558** judged rows currently).
- [x] Cohen's kappa (subset) exported to `outputs/eval/cohen_kappa.csv`.

## Artifacts
- `data/processed/pooled_candidates.tsv` — present
- `data/processed/qrels.tsv` — graded relevance file
- Bootstrap (sanity smoke): `data/processed/qrels_bootstrap.tsv` — present

Re-run pooling + labeling pipeline if queries change materially.
