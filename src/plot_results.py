"""Create summary charts for baseline and extension results."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

from src.utils import ensure_dir


def plot_aggregate(aggregate_path: Path, es_aggregate_path: Path, out_path: Path) -> None:
    """Plot aggregate metric comparison across retrieval systems."""
    base = pd.read_csv(aggregate_path)
    es = pd.read_csv(es_aggregate_path) if es_aggregate_path.exists() else pd.DataFrame()
    all_rows = pd.concat([base, es], ignore_index=True, sort=False)
    melted = all_rows.melt(
        id_vars=["name"],
        value_vars=["map", "P_5", "recall_10", "ndcg_cut_10"],
        var_name="metric",
        value_name="value",
    )
    plt.figure(figsize=(10, 5))
    sns.barplot(data=melted, x="metric", y="value", hue="name")
    plt.ylim(0, 1.05)
    plt.title("Aggregate retrieval metrics by model")
    plt.tight_layout()
    plt.savefig(out_path, dpi=180)
    plt.close()


def plot_query_type(eval_by_type_path: Path, es_by_type_path: Path, out_path: Path) -> None:
    """Plot nDCG@10 by query type for available systems."""
    base = pd.read_csv(eval_by_type_path)
    base = base[["name", "query_type", "ndcg_cut_10"]].copy()
    es = pd.read_csv(es_by_type_path) if es_by_type_path.exists() else pd.DataFrame()
    if not es.empty:
        es["name"] = "ElasticsearchBM25"
        es = es[["name", "query_type", "ndcg_cut_10"]]
        frame = pd.concat([base, es], ignore_index=True)
    else:
        frame = base
    plt.figure(figsize=(10, 5))
    sns.barplot(data=frame, x="query_type", y="ndcg_cut_10", hue="name")
    plt.ylim(0, 1.05)
    plt.title("nDCG@10 by query type")
    plt.xticks(rotation=20, ha="right")
    plt.tight_layout()
    plt.savefig(out_path, dpi=180)
    plt.close()


def plot_per_query_distribution(perq_path: Path, es_perq_path: Path, out_path: Path) -> None:
    """Plot per-query nDCG@10 distribution by system."""
    perq = pd.read_csv(perq_path)[["name", "qid", "ndcg_cut_10"]].copy()
    es = pd.read_csv(es_perq_path) if es_perq_path.exists() else pd.DataFrame()
    if not es.empty:
        es["name"] = "ElasticsearchBM25"
        es = es[["name", "qid", "ndcg_cut_10"]]
        frame = pd.concat([perq, es], ignore_index=True)
    else:
        frame = perq
    plt.figure(figsize=(10, 5))
    sns.boxplot(data=frame, x="name", y="ndcg_cut_10")
    plt.ylim(0, 1.05)
    plt.title("Per-query nDCG@10 distribution")
    plt.tight_layout()
    plt.savefig(out_path, dpi=180)
    plt.close()


def main() -> None:
    """CLI entrypoint for chart generation."""
    parser = argparse.ArgumentParser(description="Generate project result charts.")
    parser.add_argument("--eval-aggregate", default="outputs/eval/aggregate_metrics.csv")
    parser.add_argument("--eval-by-type", default="outputs/eval/metrics_by_query_type.csv")
    parser.add_argument("--per-query", default="outputs/eval/per_query_metrics.csv")
    parser.add_argument("--es-aggregate", default="outputs/extension/es_aggregate_metrics.csv")
    parser.add_argument("--es-by-type", default="outputs/extension/es_metrics_by_query_type.csv")
    parser.add_argument("--es-per-query", default="outputs/extension/es_per_query_metrics.csv")
    parser.add_argument("--out-dir", default="outputs/charts")
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    ensure_dir(out_dir)
    plot_aggregate(Path(args.eval_aggregate), Path(args.es_aggregate), out_dir / "aggregate_model_comparison.png")
    plot_query_type(Path(args.eval_by_type), Path(args.es_by_type), out_dir / "ndcg_by_query_type.png")
    plot_per_query_distribution(
        Path(args.per_query), Path(args.es_per_query), out_dir / "per_query_ndcg_distribution.png"
    )
    print(f"Wrote charts to {out_dir}")


if __name__ == "__main__":
    main()
