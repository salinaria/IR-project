"""Regenerate weekly reports, final report, and rubric checklist from disk outputs."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


def safe_read_csv(path: Path, sep: str = ",") -> pd.DataFrame:
    """Load a CSV/TSV if present; otherwise return an empty frame."""
    if path.exists():
        return pd.read_csv(path, sep=sep)
    return pd.DataFrame()


def count_jsonl_lines(path: Path) -> int | None:
    """Count non-empty lines in a JSONL file."""
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as handle:
        return sum(1 for line in handle if line.strip())


def count_human_qrels(qrels_path: Path) -> int:
    """Count labeled rows in the official qrels file (excluding header-only)."""
    if not qrels_path.exists():
        return 0
    frame = pd.read_csv(qrels_path, sep="\t")
    if frame.empty:
        return 0
    return len(frame)


def df_to_markdown_table(frame: pd.DataFrame, max_rows: int = 20) -> str:
    """Render a small DataFrame as a GitHub-flavored markdown table."""
    if frame.empty:
        return "_No data._\n"
    view = frame.head(max_rows)
    headers = "| " + " | ".join(view.columns) + " |"
    sep = "| " + " | ".join(["---"] * len(view.columns)) + " |"
    rows = ["| " + " | ".join(str(v) for v in row) + " |" for row in view.values.tolist()]
    return "\n".join([headers, sep, *rows]) + "\n"


def write_deliverables(base: Path, flags: dict) -> None:
    """Write a single checklist against the course rubric."""
    path = base / "reports" / "DELIVERABLES.md"
    lines = [
        "# Project deliverables checklist",
        "",
        "Legend: Done / Partial / Missing",
        "",
        "| Phase | Deliverable | Status | Evidence |",
        "| --- | --- | --- | --- |",
        f"| 1 | Domain crawl (`temple.edu`) | {flags['p1']} | `data/raw/corpus.jsonl`, `data/raw/corpus_deduped.jsonl` |",
        f"| 2 | PyTerrier index | {flags['p2_index']} | `index/terrier/data.properties` |",
        f"| 2 | File-type distribution table | {flags['p2_types']} | `outputs/analysis/file_type_distribution.csv` |",
        f"| 2 | Vocabulary + token stats | {flags['p2_vocab']} | `outputs/analysis/collection_summary.csv` |",
        f"| 2 | Zipf log-log plot | {flags['p2_zipf']} | `outputs/analysis/zipf_loglog.png` |",
        f"| 2 | Doc length distribution | {flags['p2_len']} | `outputs/analysis/doc_length_distribution.png` |",
        f"| 2 | Stopword analysis | {flags['p2_stop']} | `outputs/analysis/stopword_analysis.csv` |",
        f"| 2 | Word cloud (top non-stopwords) | {flags['p2_cloud']} | `outputs/analysis/wordcloud_top_terms.png` |",
        f"| 3 | 15 queries (nav / info / broad) + intent metadata | {flags['p3']} | `data/processed/query_templates.tsv` |",
        f"| 4 | Pooled candidates (BM25+TFIDF+QL top-10) | {flags['p4_pool']} | `data/processed/pooled_candidates.tsv` |",
        f"| 4 | Human qrels (official) | {flags['p4_qrels']} | `data/processed/qrels.tsv` |",
        f"| 4 | Cohen's k (secondary labels) | {flags['p4_kappa']} | Needs second annotator export (not automated) |",
        f"| 5 | Baselines BM25 + TF-IDF + QL + metrics | {flags['p5']} | `outputs/eval/aggregate_metrics.csv` |",
        f"| 5 | Paired t-tests | {flags['p5_t']} | `outputs/eval/paired_t_tests.csv` |",
        f"| 5 | Metrics by query type | {flags['p5_qt']} | `outputs/eval/metrics_by_query_type.csv` |",
        f"| 6 | BM25 k1/b sensitivity curves | {flags['p6']} | `outputs/eval/bm25_sensitivity_curves.png` |",
        f"| 7 | Optimization (latency + overlap) | {flags['p7']} | `outputs/optimization/optimization_results.csv` |",
        f"| 8 | Modern extension (ES or LLM rerank) | {flags['p8']} | Not implemented in repo |",
        f"| 9 | Error analysis (5+ cases) | {flags['p9']} | `src/error_analysis_template.md` + fill from eval |",
        f"| 10 | Final report + reproduction commands | {flags['p10']} | `reports/final_report.md` |",
        "",
        "## Notes",
        "- **HTML-only crawl:** live fetcher stores `file_type=html`. Adding PDF/DOCX from disk requires a separate ingest path for full file-type diversity.",
        "- **`qrels_bootstrap.tsv`:** only for running metrics before human labels exist; replace for graded pooling.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def write_all_reports(base: Path, target_docs: int = 20000) -> None:
    """Rewrite week reports and final summary from current artifacts."""
    reports_dir = base / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    raw_lines = count_jsonl_lines(base / "data/raw/corpus.jsonl")
    dedup_lines = count_jsonl_lines(base / "data/raw/corpus_deduped.jsonl")
    summary = safe_read_csv(base / "outputs/analysis/collection_summary.csv")
    query_templates = safe_read_csv(base / "data/processed/query_templates.tsv", sep="\t")
    eval_metrics = safe_read_csv(base / "outputs/eval/aggregate_metrics.csv")
    sensitivity = safe_read_csv(base / "outputs/eval/bm25_sensitivity.csv")
    optimization = safe_read_csv(base / "outputs/optimization/optimization_results.csv")
    human_qrels_n = count_human_qrels(base / "data/processed/qrels.tsv")
    bootstrap_exists = (base / "data/processed/qrels_bootstrap.tsv").exists()
    pooled_exists = (base / "data/processed/pooled_candidates.tsv").exists()
    index_ok = (base / "index/terrier/data.properties").exists()
    mq_ok = (base / "outputs/eval/metrics_by_query_type.csv").exists()

    def st(done: bool, partial: bool = False) -> str:
        if done:
            return "Done"
        if partial:
            return "Partial"
        return "Missing"

    flags = {
        "p1": st(
            dedup_lines is not None and dedup_lines >= target_docs,
            dedup_lines is not None and dedup_lines > 0,
        ),
        "p2_index": st(index_ok),
        "p2_types": st(not safe_read_csv(base / "outputs/analysis/file_type_distribution.csv").empty),
        "p2_vocab": st(not summary.empty),
        "p2_zipf": st((base / "outputs/analysis/zipf_loglog.png").exists()),
        "p2_len": st((base / "outputs/analysis/doc_length_distribution.png").exists()),
        "p2_stop": st((base / "outputs/analysis/stopword_analysis.csv").exists()),
        "p2_cloud": st((base / "outputs/analysis/wordcloud_top_terms.png").exists()),
        "p3": st((base / "data/processed/query_templates.tsv").exists()),
        "p4_pool": st(pooled_exists),
        "p4_qrels": st(human_qrels_n > 0),
        "p4_kappa": "Missing",
        "p5": st(not eval_metrics.empty),
        "p5_t": st((base / "outputs/eval/paired_t_tests.csv").exists()),
        "p5_qt": st(mq_ok),
        "p6": st((base / "outputs/eval/bm25_sensitivity_curves.png").exists() and not sensitivity.empty),
        "p7": st(not optimization.empty),
        "p8": "Missing",
        "p9": "Partial",
        "p10": st((base / "reports/final_report.md").exists()),
    }

    summary_md = df_to_markdown_table(summary, max_rows=10) if not summary.empty else "_Run collection analysis._\n"
    eval_md = df_to_markdown_table(eval_metrics, max_rows=10) if not eval_metrics.empty else "_Run evaluation with qrels._\n"

    failure_lines: list[str] = []
    perq_path = base / "outputs/eval/per_query_metrics.csv"
    if perq_path.exists():
        pq = pd.read_csv(perq_path)
        if {"name", "qid", "ndcg_cut_10"}.issubset(pq.columns):
            bm = pq[pq["name"] == "BM25"].copy()
            if not bm.empty:
                worst = bm.nsmallest(5, "ndcg_cut_10", keep="all").head(5)
                failure_lines.append("### Candidate failure queries (low BM25 nDCG@10)")
                for _, row in worst.iterrows():
                    failure_lines.append(f"- **{row['qid']}** — nDCG@10 = {float(row['ndcg_cut_10']):.4f}")
    failure_block = "\n".join(failure_lines) if failure_lines else "_Run evaluation to populate._"

    week_text = {
        1: f"""# Week 1: Data Collection

## Deliverables
- [x] Crawl `temple.edu` at scale (target **{target_docs}** unique docs).

## Results
- Raw JSONL lines: **{raw_lines if raw_lines is not None else "n/a"}** (includes duplicates from restarts).
- Deduped unique `docno` count: **{dedup_lines if dedup_lines is not None else "n/a"}** → `data/raw/corpus_deduped.jsonl`.

## Commands
```bash
.venv/bin/python3 -m src.dedupe_corpus
```
""",
        2: f"""# Week 2: Indexing and Collection Analysis

## Deliverables
- [x] PyTerrier index (`index/terrier`).
- [x] Summary table: documents, file types, vocabulary, tokens.
- [x] Zipf (log-log), doc length hist, stopword stats, word cloud.

## Results (deduped corpus)
{summary_md}

### Artifacts
- `outputs/analysis/file_type_distribution.csv`
- `outputs/analysis/zipf_loglog.png`
- `outputs/analysis/doc_length_distribution.png`
- `outputs/analysis/stopword_analysis.csv`
- `outputs/analysis/wordcloud_top_terms.png`

### Rubric gap
- Crawl pipeline records **HTML only** (`file_type=html`). For Word/PDF counts from live site, add download + text extraction (e.g. `pdfplumber`, `python-docx`) in a follow-up ingest script.
""",
        3: f"""# Week 3: Collaborative Query Construction

## Deliverables
- [x] Query set with intent type + metadata (**{len(query_templates)}** queries).

## Artifacts
- `data/processed/query_templates.tsv` (qid, query, query_type, intent, expected_doc_types)
- `data/processed/queries.tsv` (qid, query) for PyTerrier

## Class integration
- Merge with the official ~300-query class set when available; replace `queries.tsv` paths in scripts.
""",
        4: f"""# Week 4: Pooling and Relevance Judgments

## Deliverables
- [x] TREC-style pool (BM25 + TF-IDF + QL, depth 10).
- [ ] Human qrels in `data/processed/qrels.tsv` (**{human_qrels_n}** rows currently).
- [ ] Secondary labels + Cohen's kappa (subset) — **manual**, not generated here.

## Artifacts
- `data/processed/pooled_candidates.tsv` — {"present" if pooled_exists else "missing"}
- `data/processed/qrels.tsv` — official judgments file (empty until labeling)
- Bootstrap (metrics only): `data/processed/qrels_bootstrap.tsv` — {"present" if bootstrap_exists else "missing"}

## Next step for full credit
Label pooled rows, write `qrels.tsv`, then re-run `src.refresh_phase_outputs` without bootstrap or point `--qrels` to your file.
""",
        5: f"""# Week 5: Baseline Retrieval Models

## Deliverables
- [x] BM25, TF-IDF, Query Likelihood runs + metrics (with bootstrap qrels until human labels exist).

## Aggregate metrics
{eval_md}

### By query type
- File: `outputs/eval/metrics_by_query_type.csv` — {"present" if mq_ok else "missing (needs query_templates merge)"}

### Artifacts
- `outputs/eval/per_query_metrics.csv`
- `outputs/eval/paired_t_tests.csv`

**Note:** Numbers below use **bootstrap** qrels unless you replace them with human judgments.
""",
        6: f"""# Week 6: BM25 Parameter Sensitivity

## Deliverables
- [x] Grid over `k1` and `b` with nDCG@10 curve plot.

## Artifacts
- `outputs/eval/bm25_sensitivity.csv`
- `outputs/eval/bm25_sensitivity_curves.png`

Sensitivity uses the same qrels as Week 5 (bootstrap until replaced).
""",
        7: f"""# Week 7: Optimization Experiment

## Deliverables
- [x] Conjunctive vs disjunctive BM25 comparison: latency, rows returned, overlap@10.

## Results table
{df_to_markdown_table(optimization, max_rows=10) if not optimization.empty else "_Run optimization experiment._"}

Artifact: `outputs/optimization/optimization_results.csv`
""",
        8: """# Week 8: Modern Extension

## Deliverables
- [ ] **Option A:** Elasticsearch comparison, or **Option B:** LLM reranking — **not implemented** in this repo.

## What to add
- Wire an ES index over the same corpus **or** a cross-encoder / API reranker on BM25 top-k.
- Reuse `outputs/eval/` layout: aggregate + by-query-type tables.

This week is intentionally left for you to choose stack (API keys, cluster access).
""",
        9: f"""# Week 9: Error Analysis

## Deliverables
- [ ] At least **five** failure cases with causes (vocabulary mismatch, ambiguity, length bias, etc.) and **proposed fixes (not implemented)**.

## Starter
- Template: `src/error_analysis_template.md`
- Use `outputs/eval/per_query_metrics.csv` to pick low nDCG@10 queries, inspect `pooled_candidates.tsv` + ranked runs.

{failure_block}

## Status
Partial — expand each candidate into a full write-up (non-relevant hits, why it failed, fix idea) using manual inspection.
""",
        10: f"""# Week 10: Final Integration and Presentation

## Deliverables
- [x] Consolidated report draft: `reports/final_report.md`
- [x] Repro commands and artifact index (see checklist).

## Presentation hook
- Walk through crawl → index → analysis plots → pooling → (human) qrels → baselines → sensitivity → optimization → planned extension.

## Corpus snapshot
- Deduped docs: **{dedup_lines if dedup_lines is not None else "n/a"}**
""",
    }

    for week in range(1, 11):
        (reports_dir / f"week_{week:02d}.md").write_text(week_text[week], encoding="utf-8")

    final = f"""# Final project report (working draft)

## Executive snapshot
- **Corpus (deduped):** {dedup_lines if dedup_lines is not None else "n/a"} documents (`data/raw/corpus_deduped.jsonl`).
- **Index:** {"built at `index/terrier`" if index_ok else "missing — run build_index"}.
- **Human qrels:** {human_qrels_n} rows in `data/processed/qrels.tsv` (official judgments).
- **Bootstrap qrels (temporary):** {"yes" if bootstrap_exists else "no"} — see `outputs/README_BOOTSTRAP_QRELS.md`.

## Collection summary
{summary_md}

## Baseline metrics (current qrels: bootstrap unless replaced)
{eval_md}

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
"""
    (reports_dir / "final_report.md").write_text(final, encoding="utf-8")
    write_deliverables(base, flags)


def write_weekly_reports(base_dir: Path, target_docs: int = 20000) -> None:
    """Backward-compatible entrypoint."""
    write_all_reports(base_dir, target_docs=target_docs)


if __name__ == "__main__":
    write_all_reports(Path("."))
    print("Reports and DELIVERABLES.md updated.")
