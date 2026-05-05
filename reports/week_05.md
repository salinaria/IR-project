# Week 5: Baseline Retrieval Models

## Deliverables
- [x] BM25, TF-IDF, Query Likelihood runs + metrics (with bootstrap qrels until human labels exist).

## Aggregate metrics
| name | map | P_5 | recall_10 | ndcg_cut_10 |
| --- | --- | --- | --- | --- |
| BM25 | 0.8984126984126983 | 0.1999999999999996 | 1.0 | 0.9247131053061266 |
| TFIDF | 0.0559749250818046 | 0.0152380952380952 | 0.0952380952380952 | 0.0633537703790791 |
| QL | 0.0488454824194058 | 0.0152380952380952 | 0.1047619047619047 | 0.0578576255383321 |


### By query type
- File: `outputs/eval/metrics_by_query_type.csv` — present

### Artifacts
- `outputs/eval/per_query_metrics.csv`
- `outputs/eval/paired_t_tests.csv`

**Note:** Numbers below use **bootstrap** qrels unless you replace them with human judgments.
