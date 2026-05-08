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


def count_error_cases(path: Path) -> int:
    """Count populated error-analysis cases in markdown by '## Case ' headings."""
    if not path.exists():
        return 0
    text = path.read_text(encoding="utf-8")
    return text.count("## Case ")


def df_to_markdown_table(frame: pd.DataFrame, max_rows: int = 20) -> str:
    """Render a small DataFrame as a GitHub-flavored markdown table."""
    if frame.empty:
        return "_No data._\n"
    view = frame.head(max_rows)
    headers = "| " + " | ".join(view.columns) + " |"
    sep = "| " + " | ".join(["---"] * len(view.columns)) + " |"
    rows = ["| " + " | ".join(str(v) for v in row) + " |" for row in view.values.tolist()]
    return "\n".join([headers, sep, *rows]) + "\n"


def md_figure_from_reports(md_path: Path, image_rel_to_root: str, caption: str) -> str:
    """Embed a PNG for viewing from ``reports/*.md`` (uses ``../`` prefix)."""
    root = md_path.parent.parent if md_path.parent.name == "reports" else md_path.parent
    full = root / image_rel_to_root
    if not full.exists():
        return f"### {caption}\n\n_Missing `{image_rel_to_root}` — run `refresh_phase_outputs` or plotting steps._\n\n"
    rel = f"../{image_rel_to_root}"
    return f"### {caption}\n\n![{caption}]({rel})\n\n"


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
        f"| 3 | Query set (class list) + intent metadata | {flags['p3']} | `data/processed/query_templates.tsv` |",
        f"| 4 | Pooled candidates (BM25+TFIDF+QL top-10) | {flags['p4_pool']} | `data/processed/pooled_candidates.tsv` |",
        f"| 4 | Human qrels (official) | {flags['p4_qrels']} | `data/processed/qrels.tsv` |",
        f"| 4 | Cohen's k (secondary labels) | {flags['p4_kappa']} | `outputs/eval/cohen_kappa.csv` |",
        f"| 5 | Baselines BM25 + TF-IDF + QL + metrics | {flags['p5']} | `outputs/eval/aggregate_metrics.csv` |",
        f"| 5 | Paired t-tests | {flags['p5_t']} | `outputs/eval/paired_t_tests.csv` |",
        f"| 5 | Metrics by query type | {flags['p5_qt']} | `outputs/eval/metrics_by_query_type.csv` |",
        f"| 6 | BM25 k1/b sensitivity curves | {flags['p6']} | `outputs/eval/bm25_sensitivity_curves.png` |",
        f"| 7 | Optimization (latency + overlap) | {flags['p7']} | `outputs/optimization/optimization_results.csv` |",
        f"| 8 | Modern extension (ES or LLM rerank) | {flags['p8']} | `outputs/extension/es_aggregate_metrics.csv` |",
        f"| 9 | Error analysis (5+ cases) | {flags['p9']} | `reports/error_analysis.md` |",
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
    extension = safe_read_csv(base / "outputs/extension/es_aggregate_metrics.csv")
    error_cases = count_error_cases(base / "reports/error_analysis.md")
    kappa = safe_read_csv(base / "outputs/eval/cohen_kappa.csv")
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

    qrels_mode = "human/official" if human_qrels_n > 0 else "bootstrap unless replaced"

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
        "p4_kappa": st(not kappa.empty),
        "p5": st(not eval_metrics.empty),
        "p5_t": st((base / "outputs/eval/paired_t_tests.csv").exists()),
        "p5_qt": st(mq_ok),
        "p6": st((base / "outputs/eval/bm25_sensitivity_curves.png").exists() and not sensitivity.empty),
        "p7": st(not optimization.empty),
        "p8": st(not extension.empty),
        "p9": st(error_cases >= 5, partial=error_cases > 0),
        "p10": st((base / "reports/final_report.md").exists()),
    }

    summary_md = df_to_markdown_table(summary, max_rows=10) if not summary.empty else "_Run collection analysis._\n"
    stopword_analysis = safe_read_csv(base / "outputs/analysis/stopword_analysis.csv")
    zipf_fit = safe_read_csv(base / "outputs/analysis/zipf_power_law_fit.csv")
    stopword_analysis_md = df_to_markdown_table(stopword_analysis, max_rows=12)
    zipf_fit_md = df_to_markdown_table(zipf_fit, max_rows=6)
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
- [x] Crawl `temple.edu` at scale (current deduped corpus: **{dedup_lines if dedup_lines is not None else "n/a"}** docs).

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
- `outputs/analysis/zipf_loglog.png` (empirical rank–frequency + **dashed** log–log OLS fit)
- `outputs/analysis/zipf_power_law_fit.csv`
- `outputs/analysis/doc_length_distribution.png`
- `outputs/analysis/stopword_analysis.csv` (NLTK + corpus TF–IDF low-IDF stoplist mix)
- `outputs/analysis/corpus_tfidf_stopwords.csv` (lowest-IDF terms used as corpus stopwords)
- `outputs/analysis/wordcloud_top_terms.png`

### Corpus-specific stopwords (TF–IDF)
Low document-level IDF ≈ globally frequent boilerplate across `temple.edu` pages. Those terms are merged with NLTK English stopwords before top-20/word-cloud analysis (see CSVs above).

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
- [{'x' if human_qrels_n > 0 else ' '}] Judgments file `data/processed/qrels.tsv` (**{human_qrels_n}** judged rows currently).
- [{'x' if not kappa.empty else ' '}] Cohen's kappa (subset) exported to `outputs/eval/cohen_kappa.csv`.

## Artifacts
- `data/processed/pooled_candidates.tsv` — {"present" if pooled_exists else "missing"}
- `data/processed/qrels.tsv` — graded relevance file
- Bootstrap (sanity smoke): `data/processed/qrels_bootstrap.tsv` — {"present" if bootstrap_exists else "missing"}

Re-run pooling + labeling pipeline if queries change materially.
""",
        5: f"""# Week 5: Baseline Retrieval Models

## Deliverables
- [x] BM25, TF-IDF, Query Likelihood runs + metrics (qrels mode: **{qrels_mode}**).

## Aggregate metrics
{eval_md}

### By query type
- File: `outputs/eval/metrics_by_query_type.csv` — {"present" if mq_ok else "missing (needs query_templates merge)"}

### Artifacts
- `outputs/eval/per_query_metrics.csv`
- `outputs/eval/paired_t_tests.csv`
- `outputs/charts/aggregate_model_comparison.png`
- `outputs/charts/ndcg_by_query_type.png`

**Note:** Numbers below use **{qrels_mode}** qrels.
""",
        6: f"""# Week 6: BM25 Parameter Sensitivity

## Deliverables
- [x] Grid over `k1` and `b` with nDCG@10 curve plot.

## Artifacts
- `outputs/eval/bm25_sensitivity.csv`
- `outputs/eval/bm25_sensitivity_curves.png`

Sensitivity runs on the **same judged qrels** as baseline evaluation (**{qrels_mode}**).
""",
        7: f"""# Week 7: Optimization Experiment

## Deliverables
- [x] Conjunctive vs disjunctive BM25 comparison: latency, rows returned, overlap@10.

## Results table
{df_to_markdown_table(optimization, max_rows=10) if not optimization.empty else "_Run optimization experiment._"}

Artifact: `outputs/optimization/optimization_results.csv`
""",
        8: f"""# Week 8: Modern Extension

## Deliverables
- [{"x" if not extension.empty else " "}] **Option A:** Elasticsearch comparison.

## Elasticsearch outputs
- `outputs/extension/es_aggregate_metrics.csv`
- `outputs/extension/es_per_query_metrics.csv`
- `outputs/extension/es_metrics_by_query_type.csv`
- `outputs/extension/es_vs_pyterrier_ttest.csv`

## Aggregate metrics
{df_to_markdown_table(extension, max_rows=10) if not extension.empty else "_Elasticsearch run not available in this environment._"}
""",
        9: f"""# Week 9: Error Analysis

## Deliverables
- [{"x" if error_cases >= 5 else " "}] At least **five** failure cases with causes (vocabulary mismatch, ambiguity, length bias, etc.) and **proposed fixes (not implemented)**.

## Output
- Auto-generated report: `reports/error_analysis.md` (**{error_cases}** cases)
- Template: `src/error_analysis_template.md`
- Supporting chart: `outputs/charts/per_query_ndcg_distribution.png`

{failure_block}

## Status
{"Done — five+ concrete cases documented." if error_cases >= 5 else "Partial — expand each candidate into a full write-up (non-relevant hits, why it failed, fix idea) using manual inspection."}
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

    final_path = reports_dir / "final_report.md"
    file_types = safe_read_csv(base / "outputs/analysis/file_type_distribution.csv")
    top20_terms = safe_read_csv(base / "outputs/analysis/top20_non_stopwords.csv")
    mq_eval_bt = safe_read_csv(base / "outputs/eval/metrics_by_query_type.csv")
    mq_es_bt = safe_read_csv(base / "outputs/extension/es_metrics_by_query_type.csv")
    paired_bt = safe_read_csv(base / "outputs/eval/paired_t_tests.csv")
    es_ttest_bt = safe_read_csv(base / "outputs/extension/es_vs_pyterrier_ttest.csv")
    corpus_prev = safe_read_csv(base / "outputs/analysis/corpus_tfidf_stopwords.csv")

    paired_md = df_to_markdown_table(paired_bt, max_rows=20)
    kappa_md = df_to_markdown_table(kappa, max_rows=10)
    es_tt_md = df_to_markdown_table(es_ttest_bt, max_rows=10)
    mq_eval_md = df_to_markdown_table(mq_eval_bt, max_rows=30)
    mq_es_md = df_to_markdown_table(mq_es_bt, max_rows=30)
    file_types_md = df_to_markdown_table(file_types, max_rows=30)
    top20_md = df_to_markdown_table(top20_terms, max_rows=25)
    corpus_prev_md = df_to_markdown_table(corpus_prev, max_rows=25)
    ext_md_table = df_to_markdown_table(extension, max_rows=10)
    opt_md_table = df_to_markdown_table(optimization, max_rows=20)
    sensitivity_md_table = df_to_markdown_table(sensitivity, max_rows=40)

    if not sensitivity.empty and "ndcg@10" in sensitivity.columns:
        best_row = sensitivity.loc[sensitivity["ndcg@10"].idxmax()]
        sens_best_note = (
            f"Best grid point in this sweep: **k1={best_row['k1']}**, **b={best_row['b']}**, "
            f"nDCG@10={float(best_row['ndcg@10']):.6f}"
        )
    else:
        sens_best_note = ""

    pooled_path = base / "data/processed/pooled_candidates.tsv"
    if pooled_exists and pooled_path.exists():
        pooled_lines = pooled_path.read_text(encoding="utf-8").strip().splitlines()
        pooled_rows = max(len(pooled_lines) - 1, 0)
    else:
        pooled_rows = 0

    fig_zipf = md_figure_from_reports(final_path, "outputs/analysis/zipf_loglog.png", "Zipf (log-log) + dashed fit")
    fig_doclen = md_figure_from_reports(
        final_path, "outputs/analysis/doc_length_distribution.png", "Document length distribution"
    )
    fig_cloud = md_figure_from_reports(
        final_path, "outputs/analysis/wordcloud_top_terms.png", "Word cloud (top non-stop terms)"
    )
    fig_sens = md_figure_from_reports(
        final_path, "outputs/eval/bm25_sensitivity_curves.png", "BM25 sensitivity curves"
    )
    fig_agg = md_figure_from_reports(
        final_path, "outputs/charts/aggregate_model_comparison.png", "Aggregate metrics: baselines vs Elasticsearch"
    )
    fig_qt = md_figure_from_reports(final_path, "outputs/charts/ndcg_by_query_type.png", "nDCG@10 by query type")
    fig_pq = md_figure_from_reports(
        final_path, "outputs/charts/per_query_ndcg_distribution.png", "Per-query nDCG@10 distribution"
    )

    err_link = "**Full write-up:** `reports/error_analysis.md`"

    final = f"""# Final project report (consolidated)

This document summarizes **figures, tables, and file paths** for the Temple IR project in one place.
When viewing from `reports/` on GitHub, figures use paths like `../outputs/...`.

## 1 Executive snapshot
- **Raw corpus lines:** {raw_lines if raw_lines is not None else "n/a"} (`data/raw/corpus.jsonl`)
- **Deduped docs:** {dedup_lines if dedup_lines is not None else "n/a"} (`data/raw/corpus_deduped.jsonl`)
- **PyTerrier index:** {"present at `index/terrier`" if index_ok else "missing"}
- **Queries (+ metadata):** {len(query_templates)} rows in `data/processed/query_templates.tsv`
- **Pool candidates (lines):** {pooled_rows} in `data/processed/pooled_candidates.tsv`
- **Graded qrels rows:** {human_qrels_n} in `data/processed/qrels.tsv`
- **Bootstrap rank-1 qrels:** {"present" if bootstrap_exists else "absent"} (`data/processed/qrels_bootstrap.tsv`)
- **Evaluation qrels mode:** **{qrels_mode}**

## 2 Reproduce everything
One command after crawl / query edits:
```bash
.venv/bin/python3 -m src.refresh_phase_outputs
```
Pieces:
```bash
.venv/bin/python3 -m src.collection_analysis --corpus data/raw/corpus_deduped.jsonl
.venv/bin/python3 -m src.evaluate_models --qrels data/processed/qrels.tsv
.venv/bin/python3 -m src.bm25_sensitivity --qrels data/processed/qrels.tsv
.venv/bin/python3 -m src.optimization_experiment
.venv/bin/python3 -m src.elasticsearch_experiment   # requires Elasticsearch on localhost:9200
.venv/bin/python3 -m src.plot_results
.venv/bin/python3 -m src.error_analysis
.venv/bin/python3 -m src.update_reports
```

## 3 Corpus & collection analysis

### Tables (`outputs/analysis/collection_summary.csv`)
{summary_md}

File type counts (`outputs/analysis/file_type_distribution.csv`):
{file_types_md}

Stopword / TF-IDF augmentation summary:
{stopword_analysis_md}

Zipf OLS coefficients (first 5000 ranks):
{zipf_fit_md}

Top 20 non-stop terms (after merged stoplist):
{top20_md}

Sample of corpus TF-IDF low-IDF terms (see full file):
{corpus_prev_md}

### Figures
{fig_zipf}
{fig_doclen}
{fig_cloud}

## 4 Retrieval baselines (PyTerrier)

### Aggregate metrics
{eval_md}

### Statistical tests (paired t-test, per-query nDCG@10)
{paired_md}

## 5 Metrics by query type (PyTerrier)
{mq_eval_md}

### Figure — model comparison & query types
{fig_agg}
{fig_qt}

## 6 BM25 parameter sensitivity ({qrels_mode} qrels)
{sens_best_note if sens_best_note else "_(See full grid in the table below.)_"}

### Table (`outputs/eval/bm25_sensitivity.csv`)
{sensitivity_md_table}

### Figure
{fig_sens}

## 7 Optimization experiment (conjunctive vs disjunctive BM25)

### Results (`outputs/optimization/optimization_results.csv`)
{opt_md_table}

## 8 Elasticsearch extension (optional; needs local ES)

### Aggregate Elasticsearch BM25
{ext_md_table if not extension.empty else "_No Elasticsearch run — run `src.elasticsearch_experiment` with Elasticsearch up._"}

### ES vs BM25 paired t-test (nDCG@10)
{es_tt_md}

### Metrics by query type (Elasticsearch)
{mq_es_md}

### Figure — per-query dispersion
{fig_pq}

## 9 Inter-annotator-style agreement (kappa export)
{kappa_md}

## 10 Error analysis
{err_link}

{failure_block}

## 11 Artifact index (paths)
**Analysis:** `outputs/analysis/collection_summary.csv`, `file_type_distribution.csv`, `stopword_analysis.csv`, `corpus_tfidf_stopwords.csv`, `zipf_power_law_fit.csv`, `top20_non_stopwords.csv`, plots `*.png`  
**Eval:** `outputs/eval/aggregate_metrics.csv`, `per_query_metrics.csv`, `metrics_by_query_type.csv`, `paired_t_tests.csv`, `bm25_sensitivity*.csv`/`.png`, `cohen_kappa.csv`  
**Optimization:** `outputs/optimization/optimization_results.csv`  
**Extension:** `outputs/extension/es_*.csv`  
**Charts:** `outputs/charts/*.png`  
**Reports:** `reports/week_*.md`, `reports/error_analysis.md`, `reports/tex/` (LaTeX)

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
