"""Emit LaTeX sources under ``reports/tex/`` from corpus stats and CSV artifacts."""

from __future__ import annotations

import argparse
import csv
from collections import Counter
from pathlib import Path


def _latex_escape(text: str) -> str:
    """Escape minimal LaTeX special characters in plain text."""
    return (
        text.replace("\\", r"\textbackslash{}")
        .replace("&", r"\&")
        .replace("%", r"\%")
        .replace("$", r"\$")
        .replace("#", r"\#")
        .replace("_", r"\_")
        .replace("{", r"\{")
        .replace("}", r"\}")
        .replace("~", r"\textasciitilde{}")
        .replace("^", r"\textasciicircum{}")
    )


def _count_jsonl_lines(path: Path) -> int | None:
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as handle:
        return sum(1 for line in handle if line.strip())


def _read_summary_metric_value(path: Path) -> dict[str, str]:
    """Load ``collection_summary.csv`` shaped as ``metric,value`` rows into a dict."""
    out: dict[str, str] = {}
    if not path.exists():
        return out
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            key = row.get("metric") or row.get("Metric")
            val = row.get("value") if "value" in row else row.get("Value")
            if key is not None and val is not None:
                out[str(key).strip()] = str(val).strip()
    return out


def _pct_latex(x: float) -> str:
    """Format a fraction in [0,1] as a LaTeX-safe percent string."""
    return f"{100.0 * x:.2f}\\%"


def _stopwords_summary_paragraph(base: Path) -> str:
    """One short paragraph from ``stopword_analysis.csv`` and collection summary."""
    sw = base / "outputs/analysis/stopword_analysis.csv"
    summary = _read_summary_metric_value(base / "outputs/analysis/collection_summary.csv")
    esc = _latex_escape
    if not sw.exists():
        return r"\textit{Run \texttt{collection\_analysis} to populate stopword metrics.}"
    with sw.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        row = next(reader, None)
    if not row:
        return r"\textit{(Empty stopword analysis file.)}"
    try:
        nltk_f = float(row.get("stopword_fraction_nltk_only", 0))
        tfidf_f = float(row.get("corpus_stopword_fraction_tfidf_only", 0))
        merged_f = float(row.get("merged_stopword_fraction", 0))
        n_sw = int(float(row.get("n_merged_stopwords", 0)))
        n_corp = int(float(row.get("n_corpus_stopwords_tfidf", 0)))
    except (TypeError, ValueError):
        return r"\textit{(Could not parse stopword summary row.)}"
    vocab = summary.get("vocabulary_size", "n/a")
    return (
        rf"Token coverage uses NLTK English stopwords extended with corpus low-IDF terms "
        rf"(\texttt{{corpus\_tfidf\_stopwords.csv}} lists {esc(str(n_corp))} corpus-specific candidates; "
        rf"the merged list has {esc(str(n_sw))} types after union with NLTK). "
        rf"In a sample pass, {_pct_latex(nltk_f)} of tokens matched NLTK-only; "
        rf"{_pct_latex(tfidf_f)} matched the TF--IDF low-IDF list only; "
        rf"after merging, {_pct_latex(merged_f)} of tokens were treated as stopwords "
        rf"(vocabulary size from the summary file: {esc(vocab)} types)."
    )


def _queries_summary_paragraph(base: Path) -> str:
    """Build a short prose summary of ``query_templates.tsv`` (counts per query_type)."""
    qt = base / "data/processed/query_templates.tsv"
    esc = _latex_escape
    if not qt.exists():
        return r"\textit{Query templates not found; expected \texttt{data/processed/query\_templates.tsv}.}"
    with qt.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        rows = list(reader)
    if not rows:
        return r"\textit{(No query rows.)}"
    n = len(rows)
    types = Counter((r.get("query_type") or "?").strip() for r in rows)
    breakdown = ", ".join(f"{esc(k)} ({v})" for k, v in sorted(types.items(), key=lambda x: (-x[1], x[0])))
    return (
        rf"The evaluation set contains {esc(str(n))} annotated queries in "
        rf"\texttt{{data/processed/query\_templates.tsv}} (exported to \texttt{{queries.tsv}} for retrieval). "
        rf"Intent types: {breakdown}. "
        rf"Pooling and \texttt{{qrels.tsv}} judgments are described in the weekly sections; "
        rf"full tables remain under \texttt{{outputs/eval/}} if needed."
    )


def _optimization_summary_paragraph(base: Path) -> str:
    """Build a prose summary from ``optimization_results.csv``."""
    opt = base / "outputs/optimization/optimization_results.csv"
    esc = _latex_escape
    if not opt.exists():
        return r"\textit{Run \texttt{optimization\_experiment} to fill optimization metrics.}"
    with opt.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        by_setting: dict[str, dict[str, str]] = {r["setting"]: r for r in reader if r.get("setting")}
    dis = by_setting.get("disjunctive")
    conj = by_setting.get("conjunctive")
    ov = by_setting.get("overlap_at_10")
    if not dis or not conj:
        return r"\textit{(Optimization CSV missing disjunctive/conjunctive rows.)}"
    try:
        lat_d = float(dis["latency_ms"])
        lat_c = float(conj["latency_ms"])
        doc_d = float(dis["docs_scored"])
        doc_c = float(conj["docs_scored"])
    except (KeyError, ValueError):
        return r"\textit{(Could not parse latency/docs from optimization CSV.)}"
    ov_txt = ""
    if ov:
        try:
            ov_val = float(ov.get("docs_scored", "nan"))
            if ov_val == ov_val:
                ov_txt = f" Overlap at rank 10 between the two rankings was approximately {esc(f'{ov_val:.3f}')}."
        except ValueError:
            pass
    return (
        rf"The optimization step compared \textbf{{disjunctive}} vs \textbf{{conjunctive}} BM25 query evaluation. "
        rf"Mean batch latency was about {esc(f'{lat_d:.0f}')}~ms (disjunctive) vs "
        rf"{esc(f'{lat_c:.0f}')}~ms (conjunctive); documents scored were "
        rf"{esc(f'{doc_d:.0f}')} vs {esc(f'{doc_c:.0f}')}.{ov_txt}"
    )


def _tests_one_liner(base: Path) -> str:
    """One line pointing to formal tests without pasting whole tables."""
    py = base / "outputs/eval/paired_t_tests.csv"
    es = base / "outputs/extension/es_vs_pyterrier_ttest.csv"
    bits: list[str] = []
    if py.exists():
        bits.append(r"PyTerrier paired comparisons: \texttt{\detokenize{outputs/eval/paired_t_tests.csv}}.")
    if es.exists():
        bits.append(r"Elasticsearch vs BM25: \texttt{\detokenize{outputs/extension/es_vs_pyterrier_ttest.csv}}.")
    if not bits:
        return r"\textit{No paired-test exports found.}"
    return " ".join(bits)


def _aggregate_metrics_table_tex(base: Path) -> str:
    """Single floating table: PyTerrier baselines plus Elasticsearch row when available."""
    esc = _latex_escape
    ag = base / "outputs/eval/aggregate_metrics.csv"
    es_path = base / "outputs/extension/es_aggregate_metrics.csv"
    if not ag.exists():
        return r"\textit{Missing \texttt{outputs/eval/aggregate\_metrics.csv}; run \texttt{evaluate\_models}.}"
    with ag.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        header = list(reader.fieldnames or [])
        py_rows = list(reader)
    extra: list[dict[str, str]] = []
    if es_path.exists():
        with es_path.open(newline="", encoding="utf-8") as handle:
            extra = list(csv.DictReader(handle))
    # Align ES columns when header matches aggregate export convention.
    for row in extra:
        missing = [h for h in header if h not in row]
        for hm in missing:
            row[hm] = ""
    all_rows = py_rows + extra
    if not all_rows or not header:
        return r"\textit{(No metric rows to print.)}"
    colspec = "l" + " r" * (len(header) - 1)
    lines_tex = [
        r"\begin{table}[htbp]",
        r"\centering",
        r"\footnotesize",
        r"\caption{Aggregate retrieval metrics (graded qrels as in the eval run). PyTerrier baselines; optional Elasticsearch BM25 row when the extension was executed.}",
        r"\resizebox{\textwidth}{!}{%",
        rf"\begin{{tabular}}{{{colspec}}}",
        r"\toprule",
        " & ".join(esc(str(h)) for h in header) + r" \\",
        r"\midrule",
    ]
    for row in all_rows:
        cells = [esc(str(row.get(h, ""))) for h in header]
        lines_tex.append(" & ".join(cells) + r" \\")
    lines_tex.extend(
        [
            r"\bottomrule",
            r"\end{tabular}",
            r"}",
            r"\vspace{4pt}",
            r"\textit{\footnotesize{Sensitivity grids, per-query scores, and query-type splits are on disk under \texttt{outputs/eval/}; charts under \texttt{outputs/charts/}.}}",
            r"\end{table}",
        ]
    )
    return "\n".join(lines_tex) + "\n"


def _appendix_summary_block(base: Path) -> str:
    """Narrative summaries (stopwords, queries, optimization, metrics) with one table only."""
    blocks = [
        r"\subsection*{Summary: stopwords}",
        _stopwords_summary_paragraph(base),
        r"\subsection*{Summary: queries}",
        _queries_summary_paragraph(base),
        r"\subsection*{Summary: optimization}",
        _optimization_summary_paragraph(base),
        r"\subsection*{Metrics and models}",
        (
            r"The figures above summarize sensitivity, query-type effects, and dispersion of per-query scores. "
            r"The table below gives aggregate MAP, P@5, recall@10, and nDCG@10 for each run model. "
            r"Use the exported per-query CSV for head-to-head contrasts beyond these totals."
        ),
        _aggregate_metrics_table_tex(base),
        r"\subsection*{Formal hypothesis tests}",
        _tests_one_liner(base),
    ]
    return "\n\n".join(blocks)


def _figure_block(tex_rel_path_from_tex_dir: str, caption: str) -> str:
    """Float with includegraphics via detokenize (safe underscores in filenames)."""
    esc_cap = _latex_escape(caption)
    return "\n".join(
        [
            r"\begin{figure}[htbp]",
            r"\centering",
            rf"\includegraphics[width=\linewidth,keepaspectratio]{{\detokenize{{{tex_rel_path_from_tex_dir}}}}}",
            rf"\caption{{{esc_cap}}}",
            r"\end{figure}",
            "",
        ]
    )


def write_latex_bundle(base: Path) -> Path:
    """Write ``reports/tex/macros.tex``, system overview, results section, and ``main.tex``.

    The generated PDF is paper-style (not weekly logs): collection → indexing → analysis → experiments → results.
    """
    base = base.resolve()
    tex_dir = base / "reports" / "tex"
    tex_dir.mkdir(parents=True, exist_ok=True)

    raw_lines = _count_jsonl_lines(base / "data/raw/corpus.jsonl")
    dedup_lines = _count_jsonl_lines(base / "data/raw/corpus_deduped.jsonl")
    summary = _read_summary_metric_value(base / "outputs/analysis/collection_summary.csv")
    eval_path = base / "outputs/eval/aggregate_metrics.csv"

    def metric(name: str, default: str = "n/a") -> str:
        v = summary.get(name, "")
        return v if v else default

    bm25_ndcg = "n/a"
    if eval_path.exists():
        with eval_path.open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("name") == "BM25":
                    bm25_ndcg = row.get("ndcg_cut_10", "n/a") or "n/a"
                    break

    raw_s = str(raw_lines if raw_lines is not None else "n/a")
    ded_s = str(dedup_lines if dedup_lines is not None else "n/a")

    macro_lines = [
        rf"\providecommand{{\RawCorpusLines}}{{{_latex_escape(raw_s)}}}",
        rf"\providecommand{{\DedupDocs}}{{{_latex_escape(ded_s)}}}",
        rf"\providecommand{{\SummaryDocs}}{{{_latex_escape(metric('documents'))}}}",
        rf"\providecommand{{\SummaryVocab}}{{{_latex_escape(metric('vocabulary_size'))}}}",
        rf"\providecommand{{\SummaryTokens}}{{{_latex_escape(metric('token_count'))}}}",
        rf"\providecommand{{\SummaryAvgLen}}{{{_latex_escape(metric('avg_doc_length'))}}}",
        rf"\providecommand{{\BMNDCGTen}}{{{_latex_escape(str(bm25_ndcg))}}}",
    ]
    (tex_dir / "macros.tex").write_text("\n".join(macro_lines), encoding="utf-8")

    system = r"""% How the pipeline works and what broke along the way
\section*{System overview and challenges}
\subsection*{End-to-end flow}
\begin{enumerate}
  \item \textbf{Crawl} (\texttt{src/crawl\_temple.py}): BFS on \texttt{temple.edu}, stream-append JSONL, resume by scanning existing \texttt{docno} and URLs. Two queues prefer unseen URLs before re-fetching known pages (expansion-only).
  \item \textbf{Dedupe} (\texttt{src/dedupe\_corpus.py}): first row per \texttt{docno} $\rightarrow$ \texttt{data/raw/corpus\_deduped.jsonl}.
  \item \textbf{Index} (\texttt{src/build\_index.py}): PyTerrier \texttt{IterDictIndexer}, meta \texttt{docno}, text field \texttt{text}.
  \item \textbf{Analysis} (\texttt{src/collection\_analysis.py}): vocabulary, Zipf, lengths, stopwords, word cloud $\rightarrow$ \texttt{outputs/analysis/}.
  \item \textbf{Queries / pooling}: templates and \texttt{queries.tsv}; pool from BM25, TF-IDF, QL.
  \item \textbf{Bootstrap qrels}: rank-1 BM25 labeled relevant (temporary metrics only).
  \item \textbf{Eval, sensitivity, optimization}: PyTerrier experiments $\rightarrow$ \texttt{outputs/eval/}, \texttt{outputs/optimization/}.
  \item \textbf{Reports}: \texttt{src/update\_reports.py} refreshes Markdown; \texttt{src/export\_latex\_reports.py} emits this PDF bundle.
\end{enumerate}

\subsection*{Snapshot numbers (from this export)}
\begin{itemize}
  \item Raw JSONL lines: \textbf{{\RawCorpusLines}} (includes duplicate lines from restarts).
  \item Deduped documents: \textbf{{\DedupDocs}}.
  \item Collection summary (first CSV row): docs {\SummaryDocs}, vocab {\SummaryVocab}, tokens {\SummaryTokens}, avg length {\SummaryAvgLen}.
  \item BM25 nDCG@10 (aggregate file, bootstrap qrels): \textbf{{\BMNDCGTen}}.
\end{itemize}

\subsection*{Main challenges encountered}
\begin{itemize}
  \item \textbf{Resume and duplicates:} repeated crawl runs appended lines; some URLs mapped to multiple \texttt{docno} values over time. Dedupe-by-\texttt{docno} plus index-time \texttt{drop\_duplicates} kept Terrier stable.
  \item \textbf{Frontier / scheduling:} treating ``already saved'' URLs as non-expandable starved BFS; fixed by always enqueueing unvisited links and then splitting \emph{new} vs \emph{expand} queues so new URLs are tried first.
  \item \textbf{Scale vs site reality:} many hosts return HTTP 403 to datacenter or script clients; tqdm only moves on \emph{new} docs so long runs looked idle while HTTP work continued---postfix counters (\texttt{fetched}, queue sizes) were added for visibility.
  \item \textbf{PyTerrier/Java:} JVM init, absolute index paths, \texttt{text\_attrs}, unique \texttt{docno} constraints required several integration passes.
  \item \textbf{Evaluation wiring:} PyTerrier \texttt{Experiment} metric tables differ in wide vs aggregate layouts; bootstrap qrels are not a substitute for human \texttt{qrels.tsv}.
\end{itemize}
"""
    (tex_dir / "00_system.tex").write_text(system, encoding="utf-8")

    results: list[str] = [
        r"\section{Results}",
        r"\subsection{Plots}",
        "",
    ]
    figure_specs = [
        ("../../outputs/analysis/zipf_loglog.png", "Zipf distribution (log--log) with dashed OLS fit."),
        ("../../outputs/analysis/doc_length_distribution.png", "Histogram of tokenized document lengths."),
        ("../../outputs/analysis/wordcloud_top_terms.png", "Word cloud of frequent non-stopwords."),
        ("../../outputs/eval/bm25_sensitivity_curves.png", "BM25 parameter sensitivity (nDCG@10 contours / curves)."),
        ("../../outputs/charts/aggregate_model_comparison.png", "Aggregate retrieval metrics comparison."),
        ("../../outputs/charts/ndcg_by_query_type.png", "nDCG@10 broken down by query type."),
        ("../../outputs/charts/per_query_ndcg_distribution.png", "Dispersion of per-query nDCG@10."),
    ]
    for rel_tex, caption in figure_specs:
        resolved = (tex_dir / rel_tex).resolve()
        if resolved.exists():
            results.append(_figure_block(rel_tex, caption))
        else:
            results.append(f"% (missing PNG) {_latex_escape(rel_tex)}\n")

    results.extend(["", r"\subsection{Stopwords, queries, and optimization}", _appendix_summary_block(base)])

    (tex_dir / "results_section.tex").write_text("\n".join(results), encoding="utf-8")

    main = r"""\documentclass[11pt,a4paper]{article}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage{lmodern}
\usepackage{geometry}
\usepackage{hyperref}
\usepackage{graphicx}
\usepackage{booktabs}
\usepackage{url}
\geometry{margin=1in}
\hypersetup{colorlinks=true, linkcolor=blue, urlcolor=blue, citecolor=blue}
\input{macros}
\title{Temple University IR Project\\Information Retrieval System Report}
\author{Auto-export from project artifacts (\texttt{export\_latex\_reports.py}).}
\date{\today}
\begin{document}
\sloppy
\maketitle
\tableofcontents
\bigskip
\section{Abstract}
We built an end-to-end IR pipeline over a Temple University web crawl: crawl, deduplicate, index, analyze the collection, construct annotated queries, pool candidates, and evaluate baseline retrieval models. This PDF summarizes the final artifacts and key results.

\section{Introduction}
Our goal was to build a reproducible retrieval system and quantify how standard models behave on a real web-derived collection. The dataset is a domain-specific crawl (primarily HTML pages) and the evaluation uses graded judgments where available.

\section{Data collection and normalization}
\begin{itemize}
  \item Raw crawl JSONL lines: \textbf{\RawCorpusLines} (\texttt{data/raw/corpus.jsonl}).
  \item Deduplicated documents: \textbf{\DedupDocs} (\texttt{data/raw/corpus\_deduped.jsonl}).
\end{itemize}
We deduplicated by keeping the first occurrence per \texttt{docno} and ensured stable identifiers for indexing.

\section{Indexing}
We indexed the deduplicated corpus into PyTerrier/Terrier (\texttt{index/terrier}) with \texttt{docno} metadata and a tokenized text field. The resulting collection summary for this snapshot is: docs \textbf{\SummaryDocs}, vocab \textbf{\SummaryVocab}, tokens \textbf{\SummaryTokens}, avg length \textbf{\SummaryAvgLen}.

\section{Experimental setup}
We evaluated standard bag-of-words baselines (BM25, TF--IDF, and Query Likelihood) using graded qrels when present. We also ran a BM25 sensitivity sweep over $(k_1, b)$ and a small optimization experiment comparing conjunctive vs disjunctive evaluation.

\section{Challenges and implementation notes}
\input{00_system}

\input{results_section}

\section{Reproducibility}
To regenerate outputs and this PDF:
\begin{verbatim}
.venv/bin/python3 -m src.refresh_phase_outputs
cd reports/tex && pdflatex main.tex && pdflatex main.tex
\end{verbatim}
\end{document}
"""
    (tex_dir / "main.tex").write_text(main, encoding="utf-8")

    readme = """# LaTeX paper bundle

Generated by `python -m src.export_latex_reports` (also invoked at the end of `python -m src.refresh_phase_outputs`).

`results_section.tex`: key plots plus short prose summaries (stopwords, queries, optimization); one aggregate-metrics table only. Full CSVs stay under `outputs/`.

## Build PDF

```bash
cd reports/tex
pdflatex main.tex
pdflatex main.tex
```

Produce `main.pdf` (paper-style narrative + results section with plots and one metrics table).

```bash
cd reports/tex && pdflatex -interaction=nonstopmode main.tex && pdflatex -interaction=nonstopmode main.tex
```
"""
    (tex_dir / "README.md").write_text(readme, encoding="utf-8")
    return tex_dir / "main.tex"


def main() -> None:
    """CLI entrypoint for LaTeX export."""
    parser = argparse.ArgumentParser(description="Write reports/tex/*.tex from project artifacts.")
    parser.add_argument("--base", type=Path, default=Path("."))
    args = parser.parse_args()
    path = write_latex_bundle(args.base.resolve())
    print(f"Wrote LaTeX bundle under {path.parent}")


if __name__ == "__main__":
    main()
