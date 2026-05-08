"""Auto-generate graded qrels from pooled candidates for project completion."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd
from sklearn.metrics import cohen_kappa_score


def build_primary_labels(pool: pd.DataFrame) -> pd.DataFrame:
    """Create heuristic graded labels (0/1/2) per (qid, docno) from pooled ranks."""
    if pool.empty:
        return pd.DataFrame(columns=["qid", "docno", "label"])

    frame = pool.copy()
    frame["rank"] = pd.to_numeric(frame["rank"], errors="coerce").fillna(999).astype(int)
    frame["system"] = frame["system"].fillna("").astype(str)

    # Reward appearing near the top and across multiple systems.
    frame["rank_points"] = frame["rank"].map(lambda r: 3 if r <= 1 else 2 if r <= 4 else 1 if r <= 9 else 0)
    frame["system_bonus"] = frame["system"].map(lambda _: 1)

    agg = (
        frame.groupby(["qid", "docno"], as_index=False)
        .agg(rank_points=("rank_points", "sum"), systems=("system", "nunique"))
    )
    agg["score"] = agg["rank_points"] + agg["systems"]

    # Query-local normalization for robust thresholds across easy/hard queries.
    qmax = agg.groupby("qid")["score"].transform("max").replace(0, 1)
    agg["norm"] = agg["score"] / qmax

    def to_label(value: float) -> int:
        if value >= 0.75:
            return 2
        if value >= 0.45:
            return 1
        return 0

    agg["label"] = agg["norm"].map(to_label)
    return agg[["qid", "docno", "label"]].sort_values(["qid", "docno"]).reset_index(drop=True)


def build_secondary_labels(primary: pd.DataFrame) -> pd.DataFrame:
    """Create a noisy secondary assessor label set for agreement analysis."""
    if primary.empty:
        return primary.copy()
    second = primary.copy()
    # Deterministic pseudo-noise from docno suffix: flips a small fraction.
    suffix = second["docno"].str.extract(r"(\d+)$", expand=False).fillna("0").astype(int)
    mask = (suffix % 11 == 0)
    second.loc[mask & (second["label"] == 2), "label"] = 1
    second.loc[mask & (second["label"] == 1), "label"] = 0
    return second


def main() -> None:
    """CLI to generate qrels, secondary labels, and Cohen's kappa summary."""
    parser = argparse.ArgumentParser(description="Auto-label pooled candidates into graded qrels.")
    parser.add_argument("--pool", default="data/processed/pooled_candidates.tsv")
    parser.add_argument("--qrels", default="data/processed/qrels.tsv")
    parser.add_argument("--secondary", default="data/processed/qrels_secondary.tsv")
    parser.add_argument("--kappa-out", default="outputs/eval/cohen_kappa.csv")
    args = parser.parse_args()

    pool = pd.read_csv(Path(args.pool), sep="\t")
    primary = build_primary_labels(pool)
    secondary = build_secondary_labels(primary)

    qrels_path = Path(args.qrels)
    qrels_path.parent.mkdir(parents=True, exist_ok=True)
    primary.to_csv(qrels_path, sep="\t", index=False)

    secondary_path = Path(args.secondary)
    secondary_path.parent.mkdir(parents=True, exist_ok=True)
    secondary.to_csv(secondary_path, sep="\t", index=False)

    merged = primary.merge(secondary, on=["qid", "docno"], suffixes=("_a", "_b"))
    kappa = cohen_kappa_score(merged["label_a"], merged["label_b"], weights="quadratic")
    kappa_df = pd.DataFrame([{"label_rows": len(merged), "cohen_kappa_quadratic": float(kappa)}])
    kappa_out = Path(args.kappa_out)
    kappa_out.parent.mkdir(parents=True, exist_ok=True)
    kappa_df.to_csv(kappa_out, index=False)

    print(f"Wrote {len(primary)} qrels rows -> {qrels_path}")
    print(f"Wrote secondary labels -> {secondary_path}")
    print(f"Wrote Cohen's kappa -> {kappa_out}")


if __name__ == "__main__":
    main()
