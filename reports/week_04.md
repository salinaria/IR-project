# Week 4: Pooling and Relevance Judgments

## Deliverables
- [x] TREC-style pool (BM25 + TF-IDF + QL, depth 10).
- [ ] Human qrels in `data/processed/qrels.tsv` (**0** rows currently).
- [ ] Secondary labels + Cohen's kappa (subset) — **manual**, not generated here.

## Artifacts
- `data/processed/pooled_candidates.tsv` — present
- `data/processed/qrels.tsv` — official judgments file (empty until labeling)
- Bootstrap (metrics only): `data/processed/qrels_bootstrap.tsv` — present

## Next step for full credit
Label pooled rows, write `qrels.tsv`, then re-run `src.refresh_phase_outputs` without bootstrap or point `--qrels` to your file.
