"""Create minimal qrels from BM25 rank-1 for pipeline smoke tests only.

Human relevance judgments from Phase 4 must replace this file for real
evaluation; this exists so metrics scripts run end-to-end before labeling.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd
import pyterrier as pt

from src.evaluate_models import load_queries
from src.utils import ensure_dir


def make_bootstrap_qrels(index_dir: Path, queries_path: Path, out_path: Path) -> int:
    """Label BM25 top-1 document per query as relevant (label=2)."""
    if not pt.java.started():
        pt.java.init()
    ensure_dir(out_path.parent)
    index_dir = index_dir.resolve()
    index = pt.IndexFactory.of(str(index_dir / "data.properties"))
    queries = load_queries(queries_path)
    model = pt.BatchRetrieve(index, wmodel="BM25", num_results=1)
    run = model.transform(queries)
    # One hit per query at rank 0 (or smallest rank).
    run = run.sort_values(["qid", "rank"])
    top = run.groupby("qid", as_index=False).first()
    qrels = top[["qid", "docno"]].copy()
    qrels["label"] = 2
    qrels.to_csv(out_path, sep="\t", index=False)
    return len(qrels)


def main() -> None:
    """CLI entrypoint for bootstrap qrels generation."""
    parser = argparse.ArgumentParser(description="Bootstrap qrels from BM25 top-1.")
    parser.add_argument("--index-dir", default="index/terrier")
    parser.add_argument("--queries", default="data/processed/queries.tsv")
    parser.add_argument("--output", default="data/processed/qrels_bootstrap.tsv")
    args = parser.parse_args()
    count = make_bootstrap_qrels(Path(args.index_dir), Path(args.queries), Path(args.output))
    print(f"Wrote {count} bootstrap qrels rows to {args.output}")


if __name__ == "__main__":
    main()
