"""BM25 parameter sensitivity experiments over k1 and b values."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import pyterrier as pt

from src.evaluate_models import load_qrels, load_queries
from src.utils import ensure_dir


def run_sensitivity(index_dir: Path, queries_path: Path, qrels_path: Path, out_dir: Path) -> None:
    """Evaluate BM25 across parameter grid and save curves."""
    if not pt.java.started():
        pt.java.init()
    ensure_dir(out_dir)

    index_dir = index_dir.resolve()
    index = pt.IndexFactory.of(str(index_dir / "data.properties"))
    queries = load_queries(queries_path)
    qrels = load_qrels(qrels_path)
    if qrels.empty:
        raise ValueError("Qrels empty; use src.bootstrap_qrels or add labels before sensitivity run.")

    rows: list[dict] = []
    for k1 in [0.6, 0.9, 1.2, 1.5, 1.8]:
        for b in [0.2, 0.4, 0.6, 0.75, 0.9]:
            model = pt.BatchRetrieve(index, wmodel="BM25", controls={"bm25.k_1": k1, "bm25.b": b})
            exp = pt.Experiment(
                [model], queries, qrels, eval_metrics=["ndcg_cut_10"], names=["BM25"], perquery=False
            )
            rows.append({"k1": k1, "b": b, "ndcg@10": float(exp["ndcg_cut_10"].iloc[0])})

    frame = pd.DataFrame(rows)
    frame.to_csv(out_dir / "bm25_sensitivity.csv", index=False)

    plt.figure(figsize=(9, 6))
    for b_value in sorted(frame["b"].unique()):
        subset = frame[frame["b"] == b_value].sort_values("k1")
        plt.plot(subset["k1"], subset["ndcg@10"], marker="o", label=f"b={b_value}")
    plt.title("BM25 Parameter Sensitivity")
    plt.xlabel("k1")
    plt.ylabel("nDCG@10")
    plt.legend()
    plt.tight_layout()
    plt.savefig(out_dir / "bm25_sensitivity_curves.png")
    plt.close()


def main() -> None:
    """CLI wrapper for sensitivity study."""
    parser = argparse.ArgumentParser(description="Run BM25 parameter sensitivity.")
    parser.add_argument("--index-dir", default="index/terrier")
    parser.add_argument("--queries", default="data/processed/queries.tsv")
    parser.add_argument("--qrels", default="data/processed/qrels.tsv")
    parser.add_argument("--out-dir", default="outputs/eval")
    args = parser.parse_args()
    run_sensitivity(Path(args.index_dir), Path(args.queries), Path(args.qrels), Path(args.out_dir))
    print(f"Sensitivity outputs saved to {args.out_dir}")


if __name__ == "__main__":
    main()
