# Final project report (working draft)

## Executive snapshot
- **Corpus (deduped):** 42217 documents (`data/raw/corpus_deduped.jsonl`).
- **Index:** built at `index/terrier`.
- **Human qrels:** 0 rows in `data/processed/qrels.tsv` (official judgments).
- **Bootstrap qrels (temporary):** yes — see `outputs/README_BOOTSTRAP_QRELS.md`.

## Collection summary
| metric | value |
| --- | --- |
| documents | 42217.0 |
| vocabulary_size | 214003.0 |
| token_count | 37491119.0 |
| avg_doc_length | 888.0573939408296 |


## Baseline metrics (current qrels: bootstrap unless replaced)
| name | map | P_5 | recall_10 | ndcg_cut_10 |
| --- | --- | --- | --- | --- |
| BM25 | 0.8984126984126983 | 0.1999999999999996 | 1.0 | 0.9247131053061266 |
| TFIDF | 0.0559749250818046 | 0.0152380952380952 | 0.0952380952380952 | 0.0633537703790791 |
| QL | 0.0488454824194058 | 0.0152380952380952 | 0.1047619047619047 | 0.0578576255383321 |


## Reproduce
```bash
.venv/bin/python3 -m src.dedupe_corpus
.venv/bin/python3 -m src.collection_analysis --corpus data/raw/corpus_deduped.jsonl
.venv/bin/python3 -m src.build_index --corpus data/raw/corpus_deduped.jsonl --index-dir index/terrier
.venv/bin/python3 -m src.pooling
.venv/bin/python3 -m src.bootstrap_qrels
.venv/bin/python3 -m src.evaluate_models --qrels data/processed/qrels_bootstrap.tsv
.venv/bin/python3 -m src.bm25_sensitivity --qrels data/processed/qrels_bootstrap.tsv
.venv/bin/python3 -m src.optimization_experiment
.venv/bin/python3 -m src.update_reports
```

Or one step:
```bash
.venv/bin/python3 -m src.refresh_phase_outputs
```

## Rubric checklist
See `reports/DELIVERABLES.md`.
