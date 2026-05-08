# Week 9: Error Analysis

## Deliverables
- [x] At least **five** failure cases with causes (vocabulary mismatch, ambiguity, length bias, etc.) and **proposed fixes (not implemented)**.

## Output
- Auto-generated report: `reports/error_analysis.md` (**5** cases)
- Template: `src/error_analysis_template.md`
- Supporting chart: `outputs/charts/per_query_ndcg_distribution.png`

### Candidate failure queries (low BM25 nDCG@10)
- **Q016** — nDCG@10 = 0.5956
- **Q098** — nDCG@10 = 0.6826
- **Q051** — nDCG@10 = 0.7393
- **Q064** — nDCG@10 = 0.7595
- **Q084** — nDCG@10 = 0.7595

## Status
Done — five+ concrete cases documented.
