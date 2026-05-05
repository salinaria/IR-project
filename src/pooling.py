"""Create pooled candidate documents from multiple retrieval models."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd
import pyterrier as pt

from src.evaluate_models import load_queries
from src.utils import ensure_dir


def build_pool(index_dir: Path, queries_path: Path, out_path: Path, depth: int = 10) -> None:
    """Merge top-k runs from BM25, TF-IDF, and Query Likelihood."""
    if not pt.java.started():
        pt.java.init()
    ensure_dir(out_path.parent)

    index_dir = index_dir.resolve()
    index = pt.IndexFactory.of(str(index_dir / "data.properties"))
    queries = load_queries(queries_path)

    models = {
        "BM25": pt.BatchRetrieve(index, wmodel="BM25", num_results=depth),
        "TFIDF": pt.BatchRetrieve(index, wmodel="TF_IDF", num_results=depth),
        "QL": pt.BatchRetrieve(index, wmodel="Hiemstra_LM", num_results=depth),
    }

    pooled: list[pd.DataFrame] = []
    for name, model in models.items():
        run = model.transform(queries)
        run["system"] = name
        pooled.append(run[["qid", "docno", "rank", "score", "system"]])

    merged = pd.concat(pooled, ignore_index=True)
    merged = merged.sort_values(["qid", "docno", "score"], ascending=[True, True, False])
    merged_unique = merged.drop_duplicates(subset=["qid", "docno"])
    merged_unique.to_csv(out_path, sep="\t", index=False)


def main() -> None:
    """CLI entrypoint for pooled-candidate generation."""
    parser = argparse.ArgumentParser(description="Build TREC-style pooled set.")
    parser.add_argument("--index-dir", default="index/terrier")
    parser.add_argument("--queries", default="data/processed/queries.tsv")
    parser.add_argument("--output", default="data/processed/pooled_candidates.tsv")
    parser.add_argument("--depth", type=int, default=10)
    args = parser.parse_args()
    build_pool(Path(args.index_dir), Path(args.queries), Path(args.output), depth=args.depth)
    print(f"Pooled set written to {args.output}")


if __name__ == "__main__":
    main()
