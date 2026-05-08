# Project deliverables checklist

Legend: Done / Partial / Missing

| Phase | Deliverable | Status | Evidence |
| --- | --- | --- | --- |
| 1 | Domain crawl (`temple.edu`) | Done | `data/raw/corpus.jsonl`, `data/raw/corpus_deduped.jsonl` |
| 2 | PyTerrier index | Done | `index/terrier/data.properties` |
| 2 | File-type distribution table | Done | `outputs/analysis/file_type_distribution.csv` |
| 2 | Vocabulary + token stats | Done | `outputs/analysis/collection_summary.csv` |
| 2 | Zipf log-log plot | Done | `outputs/analysis/zipf_loglog.png` |
| 2 | Doc length distribution | Done | `outputs/analysis/doc_length_distribution.png` |
| 2 | Stopword analysis | Done | `outputs/analysis/stopword_analysis.csv` |
| 2 | Word cloud (top non-stopwords) | Done | `outputs/analysis/wordcloud_top_terms.png` |
| 3 | Query set (class list) + intent metadata | Done | `data/processed/query_templates.tsv` |
| 4 | Pooled candidates (BM25+TFIDF+QL top-10) | Done | `data/processed/pooled_candidates.tsv` |
| 4 | Human qrels (official) | Done | `data/processed/qrels.tsv` |
| 4 | Cohen's k (secondary labels) | Done | `outputs/eval/cohen_kappa.csv` |
| 5 | Baselines BM25 + TF-IDF + QL + metrics | Done | `outputs/eval/aggregate_metrics.csv` |
| 5 | Paired t-tests | Done | `outputs/eval/paired_t_tests.csv` |
| 5 | Metrics by query type | Done | `outputs/eval/metrics_by_query_type.csv` |
| 6 | BM25 k1/b sensitivity curves | Done | `outputs/eval/bm25_sensitivity_curves.png` |
| 7 | Optimization (latency + overlap) | Done | `outputs/optimization/optimization_results.csv` |
| 8 | Modern extension (ES or LLM rerank) | Done | `outputs/extension/es_aggregate_metrics.csv` |
| 9 | Error analysis (5+ cases) | Done | `reports/error_analysis.md` |
| 10 | Final report + reproduction commands | Done | `reports/final_report.md` |

## Notes
- **HTML-only crawl:** live fetcher stores `file_type=html`. Adding PDF/DOCX from disk requires a separate ingest path for full file-type diversity.
- **`qrels_bootstrap.tsv`:** only for running metrics before human labels exist; replace for graded pooling.
