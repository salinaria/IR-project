"""Emit LaTeX sources under ``reports/tex/`` from corpus stats and CSV artifacts."""

from __future__ import annotations

import argparse
import csv
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
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            key = row.get("metric") or row.get("Metric")
            val = row.get("value") if "value" in row else row.get("Value")
            if key is not None and val is not None:
                out[str(key).strip()] = str(val).strip()
    return out


def write_latex_bundle(base: Path) -> Path:
    """Write ``reports/tex/macros.tex``, weekly snippets, system overview, and ``main.tex``."""
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

    weeks: list[tuple[str, str]] = [
        (
            "Week 1: Data collection",
            r"""Crawl \texttt{temple.edu} with politeness delay; stream to \texttt{data/raw/corpus.jsonl}. Resume scans the file once for max \texttt{docno} suffix and known URLs (memory-safe). Deduped count for this snapshot: \textbf{{\DedupDocs}} unique documents (from \textbf{{\RawCorpusLines}} raw lines).""",
        ),
        (
            "Week 2: Indexing and collection analysis",
            r"""Build PyTerrier index under \texttt{index/terrier}. Run collection statistics: file-type table, vocabulary and token counts, Zipf log-log plot, document-length distribution, stopword table, word cloud---all under \texttt{outputs/analysis/}. Crawl is HTML-only; PDF/DOCX would need a separate ingest.""",
        ),
        (
            "Week 3: Collaborative query construction",
            r"""Fifteen structured queries in \texttt{data/processed/query\_templates.tsv} with intent metadata; \texttt{queries.tsv} feeds PyTerrier runs.""",
        ),
        (
            "Week 4: Pooling and relevance",
            r"""TREC-style pool (BM25 + TF-IDF + QL, depth 10) $\rightarrow$ \texttt{pooled\_candidates.tsv}. Official \texttt{qrels.tsv} remains for human labeling; bootstrap qrels exist only to exercise metrics.""",
        ),
        (
            "Week 5: Baseline retrieval",
            r"""BM25, TF-IDF, and Query Likelihood evaluated with bootstrap qrels until human judgments exist. See \texttt{outputs/eval/aggregate\_metrics.csv} and per-query exports.""",
        ),
        (
            "Week 6: BM25 sensitivity",
            r"""Grid over $k_1$ and $b$ with nDCG@10 curves in \texttt{outputs/eval/bm25\_sensitivity\_curves.png}.""",
        ),
        (
            "Week 7: Optimization experiment",
            r"""Compare conjunctive vs disjunctive BM25 variants; record latency, rows returned, and overlap@10 in \texttt{outputs/optimization/optimization\_results.csv}.""",
        ),
        (
            "Week 8: Modern extension",
            r"""Not implemented in-repo (Elasticsearch or LLM rerank). Reserved for future work.""",
        ),
        (
            "Week 9: Error analysis",
            r"""Partial: template in \texttt{src/error\_analysis\_template.md}; use low nDCG@10 rows from \texttt{per\_query\_metrics.csv} with manual pool inspection.""",
        ),
        (
            "Week 10: Final integration",
            r"""Consolidated Markdown report at \texttt{reports/final\_report.md}; rubric checklist at \texttt{reports/DELIVERABLES.md}. This LaTeX bundle mirrors the same timeline.""",
        ),
    ]

    for i, (title, body) in enumerate(weeks, start=1):
        slug = f"week_{i:02d}.tex"
        content = f"\\section{{{_latex_escape(title)}}}\n{body}\n"
        (tex_dir / slug).write_text(content, encoding="utf-8")

    main = r"""\documentclass[11pt,a4paper]{article}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage{lmodern}
\usepackage{geometry}
\usepackage{hyperref}
\usepackage{graphicx}
\usepackage{booktabs}
\geometry{margin=1in}
\hypersetup{colorlinks=true, linkcolor=blue, urlcolor=blue, citecolor=blue}
\input{macros}
\title{Temple University IR Project\\Weekly narrative (auto-generated)}
\date{\today}
\begin{document}
\sloppy
\maketitle
\tableofcontents
\bigskip
\input{00_system}
\input{week_01}
\input{week_02}
\input{week_03}
\input{week_04}
\input{week_05}
\input{week_06}
\input{week_07}
\input{week_08}
\input{week_09}
\input{week_10}
\end{document}
"""
    (tex_dir / "main.tex").write_text(main, encoding="utf-8")

    readme = """# LaTeX weekly bundle

Generated by `python -m src.export_latex_reports` (also invoked at the end of `python -m src.refresh_phase_outputs`).

## Build PDF

```bash
cd reports/tex
pdflatex main.tex
pdflatex main.tex
```

Figures live under `../../outputs/analysis/`; this `main.tex` does not embed them (Markdown reports link to PNG paths). Add `\\includegraphics` in the relevant week file if you want plots in the PDF.
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
