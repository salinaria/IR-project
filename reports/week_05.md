# Week 5: Baseline Retrieval Models

## Deliverables
- [x] BM25, TF-IDF, Query Likelihood runs + metrics (qrels mode: **human/official**).

## Aggregate metrics
| name | map | P_5 | recall_10 | ndcg_cut_10 |
| --- | --- | --- | --- | --- |
| BM25 | 0.4897853550849345 | 0.9961904761904762 | 0.4184918391876504 | 0.8300558702936255 |
| TFIDF | 0.5078014044068315 | 0.9942857142857144 | 0.4127164492343494 | 0.8243925857440955 |
| QL | 0.5411758282026168 | 0.937142857142857 | 0.3935576203971061 | 0.7732880292938707 |


### By query type
- File: `outputs/eval/metrics_by_query_type.csv` — present

### Artifacts
- `outputs/eval/per_query_metrics.csv`
- `outputs/eval/paired_t_tests.csv`
- `outputs/charts/aggregate_model_comparison.png`
- `outputs/charts/ndcg_by_query_type.png`

**Note:** Numbers below use **human/official** qrels.
