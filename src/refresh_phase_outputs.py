"""Regenerate analysis, pooling, bootstrap qrels, eval, sensitivity, optimization, and reports."""

from __future__ import annotations

import argparse
from pathlib import Path

from src.bootstrap_qrels import make_bootstrap_qrels
from src.bm25_sensitivity import run_sensitivity
from src.build_index import build_index
from src.collection_analysis import run_analysis
from src.dedupe_corpus import dedupe_jsonl
from src.evaluate_models import run_eval
from src.export_latex_reports import write_latex_bundle
from src.elasticsearch_experiment import run_elasticsearch_extension
from src.error_analysis import build_error_analysis
from src.optimization_experiment import run_optimization
from src.plot_results import (
    plot_aggregate,
    plot_per_query_distribution,
    plot_query_type,
)
from src.pooling import build_pool
from src.update_reports import write_all_reports


def main() -> None:
    """Run all automated post-crawl steps with sensible defaults."""
    parser = argparse.ArgumentParser(description="Refresh IR outputs after crawl/index.")
    parser.add_argument("--raw-corpus", default="data/raw/corpus.jsonl")
    parser.add_argument("--deduped-corpus", default="data/raw/corpus_deduped.jsonl")
    parser.add_argument("--index-dir", default="index/terrier")
    parser.add_argument("--queries", default="data/processed/queries.tsv")
    parser.add_argument("--bootstrap-qrels", default="data/processed/qrels_bootstrap.tsv")
    args = parser.parse_args()

    raw = Path(args.raw_corpus)
    deduped = Path(args.deduped_corpus)
    read_n, write_n = dedupe_jsonl(raw, deduped)
    print(f"Dedupe: {read_n} -> {write_n} docs -> {deduped}")

    index_dir = Path(args.index_dir)
    build_index(deduped, index_dir)
    print(f"Index rebuilt at {index_dir.resolve()}")

    run_analysis(deduped, Path("outputs/analysis"))
    print("Collection analysis done.")

    build_pool(index_dir, Path(args.queries), Path("data/processed/pooled_candidates.tsv"))
    print("Pooling done.")

    bootstrap_path = Path(args.bootstrap_qrels)
    make_bootstrap_qrels(index_dir, Path(args.queries), bootstrap_path)
    print("Bootstrap qrels done (not a substitute for human judgments).")

    official_qrels = Path("data/processed/qrels.tsv")
    if official_qrels.exists() and official_qrels.read_text(encoding="utf-8").strip().count("\n") > 0:
        eval_qrels = official_qrels
    else:
        eval_qrels = bootstrap_path
    print(f"Evaluating models with qrels → {eval_qrels}")

    run_eval(
        index_dir,
        Path(args.queries),
        eval_qrels,
        Path("outputs/eval"),
    )
    print("Baseline evaluation done.")

    run_sensitivity(
        index_dir,
        Path(args.queries),
        eval_qrels,
        Path("outputs/eval"),
    )
    print("BM25 sensitivity done.")

    run_optimization(index_dir, Path(args.queries), Path("outputs/optimization"))
    print("Optimization experiment done.")

    try:
        run_elasticsearch_extension(
            corpus_path=deduped,
            queries_path=Path(args.queries),
            qrels_path=Path("data/processed/qrels.tsv"),
            out_dir=Path("outputs/extension"),
        )
        print("Elasticsearch extension experiment done.")
    except Exception as exc:
        print(f"Elasticsearch extension skipped/failed: {exc}")

    charts_dir = Path("outputs/charts")
    charts_dir.mkdir(parents=True, exist_ok=True)
    plot_aggregate(
        Path("outputs/eval/aggregate_metrics.csv"),
        Path("outputs/extension/es_aggregate_metrics.csv"),
        charts_dir / "aggregate_model_comparison.png",
    )
    plot_query_type(
        Path("outputs/eval/metrics_by_query_type.csv"),
        Path("outputs/extension/es_metrics_by_query_type.csv"),
        charts_dir / "ndcg_by_query_type.png",
    )
    plot_per_query_distribution(
        Path("outputs/eval/per_query_metrics.csv"),
        Path("outputs/extension/es_per_query_metrics.csv"),
        charts_dir / "per_query_ndcg_distribution.png",
    )
    print("Result charts generated.")

    build_error_analysis(
        queries_path=Path(args.queries),
        templates_path=Path("data/processed/query_templates.tsv"),
        perq_path=Path("outputs/eval/per_query_metrics.csv"),
        es_perq_path=Path("outputs/extension/es_per_query_metrics.csv"),
        pool_path=Path("data/processed/pooled_candidates.tsv"),
        qrels_path=Path("data/processed/qrels.tsv"),
        out_path=Path("reports/error_analysis.md"),
        n_cases=5,
    )
    print("Error analysis report generated.")

    readme = Path("outputs/README_BOOTSTRAP_QRELS.md")
    readme.write_text(
        """# Bootstrap qrels (automation only)

`data/processed/qrels_bootstrap.tsv` labels the **BM25 rank-1** document per query as relevant.

This is **not** a TREC-style judgment set. For the course deliverable, replace it with pooled
human labels in `data/processed/qrels.tsv` and re-run:

- `src.evaluate_models`
- `src.bm25_sensitivity`
""",
        encoding="utf-8",
    )

    write_all_reports(Path("."))
    print("Reports updated.")

    write_latex_bundle(Path("."))
    print("LaTeX bundle written to reports/tex/ (see reports/tex/README.md).")

    print(readme)


if __name__ == "__main__":
    main()
