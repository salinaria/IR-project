"""Compare disjunctive and conjunctive retrieval behavior and latency."""

from __future__ import annotations

import argparse
import time
from pathlib import Path

import pandas as pd
import pyterrier as pt

from src.evaluate_models import load_queries
from src.utils import ensure_dir


def timed_transform(model: pt.Transformer, queries: pd.DataFrame) -> tuple[pd.DataFrame, float]:
    """Run retrieval model and measure wall-clock latency in milliseconds."""
    start = time.perf_counter()
    run = model.transform(queries)
    latency_ms = (time.perf_counter() - start) * 1000.0
    return run, latency_ms


def ranking_overlap(run_a: pd.DataFrame, run_b: pd.DataFrame, k: int = 10) -> float:
    """Compute mean overlap@k across query result sets."""
    overlaps: list[float] = []
    for qid in sorted(set(run_a["qid"]).intersection(set(run_b["qid"]))):
        a_docs = set(run_a[run_a["qid"] == qid].nsmallest(k, "rank")["docno"])
        b_docs = set(run_b[run_b["qid"] == qid].nsmallest(k, "rank")["docno"])
        overlaps.append(len(a_docs.intersection(b_docs)) / max(k, 1))
    return sum(overlaps) / max(1, len(overlaps))


def run_optimization(index_dir: Path, queries_path: Path, out_dir: Path) -> None:
    """Run optimization study comparing query operator variants."""
    if not pt.java.started():
        pt.java.init()
    ensure_dir(out_dir)

    index_dir = index_dir.resolve()
    index = pt.IndexFactory.of(str(index_dir / "data.properties"))
    queries = load_queries(queries_path)

    disj_model = pt.BatchRetrieve(index, wmodel="BM25")
    conj_model = pt.BatchRetrieve(index, wmodel="BM25", controls={"parsecontrols": "on", "parseql": "on"})

    disj_run, disj_latency = timed_transform(disj_model, queries)
    conj_queries = queries.copy()
    conj_queries["query"] = conj_queries["query"].apply(lambda q: " #combine(" + q + ")")
    conj_run, conj_latency = timed_transform(conj_model, conj_queries)

    overlap = ranking_overlap(disj_run, conj_run, k=10)
    output = pd.DataFrame(
        [
            {
                "setting": "disjunctive",
                "latency_ms": disj_latency,
                "docs_scored": len(disj_run),
            },
            {
                "setting": "conjunctive",
                "latency_ms": conj_latency,
                "docs_scored": len(conj_run),
            },
            {
                "setting": "overlap_at_10",
                "latency_ms": 0.0,
                "docs_scored": overlap,
            },
        ]
    )
    output.to_csv(out_dir / "optimization_results.csv", index=False)


def main() -> None:
    """CLI for optimization comparison experiment."""
    parser = argparse.ArgumentParser(description="Run optimization experiment.")
    parser.add_argument("--index-dir", default="index/terrier")
    parser.add_argument("--queries", default="data/processed/queries.tsv")
    parser.add_argument("--out-dir", default="outputs/optimization")
    args = parser.parse_args()
    run_optimization(Path(args.index_dir), Path(args.queries), Path(args.out_dir))
    print(f"Optimization results saved to {args.out_dir}")


if __name__ == "__main__":
    main()
