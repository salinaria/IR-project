# Week 5: Baseline Retrieval Models

## Deliverables
- [x] BM25, TF-IDF, Query Likelihood runs + metrics (with bootstrap qrels until human labels exist).

## Aggregate metrics
| name | map | P_5 | recall_10 | ndcg_cut_10 |
| --- | --- | --- | --- | --- |
| BM25 | 0.8444444444444444 | 0.2 | 1.0 | 0.884123967142861 |
| TFIDF | 0.0008333333333333 | 0.0 | 0.0 | 0.0 |
| QL | 0.0670121572724107 | 0.0133333333333333 | 0.0666666666666666 | 0.0666666666666666 |


### By query type
- File: `outputs/eval/metrics_by_query_type.csv` — present

### Artifacts
- `outputs/eval/per_query_metrics.csv`
- `outputs/eval/paired_t_tests.csv`

**Note:** Numbers below use **bootstrap** qrels unless you replace them with human judgments.
