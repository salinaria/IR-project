"""Baseline retrieval, metrics, and significance tests."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd
import pyterrier as pt
from scipy.stats import ttest_rel

from src.utils import ensure_dir


def load_queries(path: Path) -> pd.DataFrame:
    """Load query file expected in TSV format with qid and query columns."""
    frame = pd.read_csv(path, sep="\t")
    required = {"qid", "query"}
    if not required.issubset(set(frame.columns)):
        raise ValueError("Query file must contain qid and query columns.")
    return frame


def load_qrels(path: Path) -> pd.DataFrame:
    """Load qrels TSV with qid, docno, and label columns."""
    frame = pd.read_csv(path, sep="\t")
    required = {"qid", "docno", "label"}
    if not required.issubset(set(frame.columns)):
        raise ValueError("Qrels file must contain qid, docno, label columns.")
    return frame


def export_metrics_by_query_type(
    per_query_csv: Path,
    query_templates_path: Path,
    out_csv: Path,
    metrics: list[str],
) -> None:
    """Join per-query metrics with query intent type and aggregate means."""
    if not per_query_csv.exists() or not query_templates_path.exists():
        return
    perq = pd.read_csv(per_query_csv)
    templates = pd.read_csv(query_templates_path, sep="\t")
    if "query_type" not in templates.columns or "qid" not in templates.columns:
        return
    merged = perq.merge(templates[["qid", "query_type"]], on="qid", how="left")
    present = [m for m in metrics if m in merged.columns]
    if not present:
        return
    grouped = merged.groupby(["name", "query_type"], dropna=False)[present].mean().reset_index()
    grouped.to_csv(out_csv, index=False)


def run_eval(index_dir: Path, queries_path: Path, qrels_path: Path, out_dir: Path) -> None:
    """Evaluate BM25, TF-IDF, and Query Likelihood on standard metrics."""
    if not pt.java.started():
        pt.java.init()
    ensure_dir(out_dir)

    index_dir = index_dir.resolve()
    index = pt.IndexFactory.of(str(index_dir / "data.properties"))
    queries = load_queries(queries_path)
    qrels = load_qrels(qrels_path)
    if qrels.empty:
        raise ValueError(
            "Qrels file is empty. Add human judgments to data/processed/qrels.tsv, or run:\n"
            "  .venv/bin/python3 -m src.bootstrap_qrels --output data/processed/qrels_bootstrap.tsv\n"
            "then pass --qrels data/processed/qrels_bootstrap.tsv (bootstrap is not real relevance)."
        )

    bm25 = pt.BatchRetrieve(index, wmodel="BM25")
    tfidf = pt.BatchRetrieve(index, wmodel="TF_IDF")
    ql = pt.BatchRetrieve(index, wmodel="Hiemstra_LM")

    metrics = ["P_5", "ndcg_cut_10", "map", "recall_10"]
    long_df = pt.Experiment(
        [bm25, tfidf, ql],
        queries,
        qrels,
        eval_metrics=metrics,
        names=["BM25", "TFIDF", "QL"],
        perquery=True,
    )
    wide = long_df.pivot_table(index=["name", "qid"], columns="measure", values="value").reset_index()
    wide.columns.name = None
    wide.to_csv(out_dir / "per_query_metrics.csv", index=False)

    aggregate = pt.Experiment(
        [bm25, tfidf, ql],
        queries,
        qrels,
        eval_metrics=metrics,
        names=["BM25", "TFIDF", "QL"],
        perquery=False,
    )
    aggregate.to_csv(out_dir / "aggregate_metrics.csv", index=False)

    qids = queries["qid"].astype(str).tolist()
    bm25_ndcg = (
        wide[wide["name"] == "BM25"].set_index("qid")["ndcg_cut_10"].reindex(qids).fillna(0.0).values
    )
    tfidf_ndcg = (
        wide[wide["name"] == "TFIDF"].set_index("qid")["ndcg_cut_10"].reindex(qids).fillna(0.0).values
    )
    ql_ndcg = wide[wide["name"] == "QL"].set_index("qid")["ndcg_cut_10"].reindex(qids).fillna(0.0).values
    tests = pd.DataFrame(
        [
            {
                "pair": "BM25 vs TFIDF",
                "t_stat": float(ttest_rel(bm25_ndcg, tfidf_ndcg).statistic),
                "p_value": float(ttest_rel(bm25_ndcg, tfidf_ndcg).pvalue),
            },
            {
                "pair": "BM25 vs QL",
                "t_stat": float(ttest_rel(bm25_ndcg, ql_ndcg).statistic),
                "p_value": float(ttest_rel(bm25_ndcg, ql_ndcg).pvalue),
            },
        ]
    )
    tests.to_csv(out_dir / "paired_t_tests.csv", index=False)

    templates_path = queries_path.parent / "query_templates.tsv"
    export_metrics_by_query_type(
        out_dir / "per_query_metrics.csv",
        templates_path,
        out_dir / "metrics_by_query_type.csv",
        metrics,
    )


def main() -> None:
    """CLI for baseline retrieval evaluation."""
    parser = argparse.ArgumentParser(description="Evaluate baseline retrieval models.")
    parser.add_argument("--index-dir", default="index/terrier")
    parser.add_argument("--queries", default="data/processed/queries.tsv")
    parser.add_argument("--qrels", default="data/processed/qrels.tsv")
    parser.add_argument("--out-dir", default="outputs/eval")
    args = parser.parse_args()
    run_eval(Path(args.index_dir), Path(args.queries), Path(args.qrels), Path(args.out_dir))
    print(f"Evaluation outputs saved to {args.out_dir}")


if __name__ == "__main__":
    main()
