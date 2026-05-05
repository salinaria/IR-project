# Week 9: Error Analysis

## Deliverables
- [ ] At least **five** failure cases with causes (vocabulary mismatch, ambiguity, length bias, etc.) and **proposed fixes (not implemented)**.

## Starter
- Template: `src/error_analysis_template.md`
- Use `outputs/eval/per_query_metrics.csv` to pick low nDCG@10 queries, inspect `pooled_candidates.tsv` + ranked runs.

### Candidate failure queries (low BM25 nDCG@10)
- **Q009** — nDCG@10 = 0.5000
- **Q012** — nDCG@10 = 0.5000
- **Q003** — nDCG@10 = 0.6309
- **Q013** — nDCG@10 = 0.6309
- **Q001** — nDCG@10 = 1.0000

## Status
Partial — expand each candidate into a full write-up (non-relevant hits, why it failed, fix idea) using manual inspection.
