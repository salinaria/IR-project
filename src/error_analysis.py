"""Generate concrete error analysis cases from current evaluation outputs."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from src.utils import ensure_dir


def _reason_and_fix(query_type: str, delta_es_bm25: float) -> tuple[str, str]:
    """Map query behavior to a plausible failure reason and non-implemented fix."""
    qt = (query_type or "").lower()
    if "broad" in qt:
        return (
            "Query ambiguity and intent drift (broad requests match many loosely related pages).",
            "Add intent-aware query reformulation and reranking features (entity focus, field boosts, diversification).",
        )
    if delta_es_bm25 > 0.05:
        return (
            "BM25 lexical mismatch; ES retrieves alternative term variants that BM25 misses.",
            "Add synonym expansion and domain vocabulary normalization before retrieval.",
        )
    if delta_es_bm25 < -0.05:
        return (
            "Length/term-frequency bias in alternate ranking introduces off-target but term-heavy pages.",
            "Tune field-length normalization and add a reranker with relevance features.",
        )
    return (
        "Near-tie ranking among partially relevant pages; top ranks include mixed-intent pages.",
        "Use a lightweight second-stage reranker on top-50 and calibrate thresholds by query type.",
    )


def build_error_analysis(
    queries_path: Path,
    templates_path: Path,
    perq_path: Path,
    es_perq_path: Path,
    pool_path: Path,
    qrels_path: Path,
    out_path: Path,
    n_cases: int = 5,
) -> None:
    """Write a filled error analysis markdown with at least ``n_cases``."""
    queries = pd.read_csv(queries_path, sep="\t")
    templates = pd.read_csv(templates_path, sep="\t")
    perq = pd.read_csv(perq_path)
    es_perq = pd.read_csv(es_perq_path) if es_perq_path.exists() else pd.DataFrame()
    pool = pd.read_csv(pool_path, sep="\t")
    qrels = pd.read_csv(qrels_path, sep="\t")

    bm25 = perq[perq["name"] == "BM25"][["qid", "P_5", "map", "ndcg_cut_10", "recall_10"]].copy()
    bm25 = bm25.rename(
        columns={
            "P_5": "bm25_P_5",
            "map": "bm25_map",
            "ndcg_cut_10": "bm25_ndcg",
            "recall_10": "bm25_recall10",
        }
    )
    merged = bm25.merge(queries, on="qid", how="left").merge(
        templates[["qid", "query_type", "intent"]], on="qid", how="left"
    )

    if not es_perq.empty:
        es = es_perq[["qid", "ndcg_cut_10"]].rename(columns={"ndcg_cut_10": "es_ndcg"})
        merged = merged.merge(es, on="qid", how="left")
        merged["delta_es_bm25_ndcg"] = merged["es_ndcg"].fillna(0.0) - merged["bm25_ndcg"]
    else:
        merged["es_ndcg"] = float("nan")
        merged["delta_es_bm25_ndcg"] = 0.0

    # Pick weakest BM25 nDCG queries.
    candidates = merged.sort_values("bm25_ndcg", ascending=True).head(n_cases).copy()

    lines: list[str] = ["# Error Analysis (auto-generated)", ""]
    for i, row in enumerate(candidates.itertuples(index=False), start=1):
        qid = str(row.qid)
        qtext = str(row.query)
        qtype = str(getattr(row, "query_type", "unknown"))
        intent = str(getattr(row, "intent", "")).strip() or "N/A"
        bm25_ndcg = float(row.bm25_ndcg)
        es_ndcg = float(row.es_ndcg) if pd.notna(row.es_ndcg) else None
        delta = float(row.delta_es_bm25_ndcg)

        pool_q = pool[(pool["qid"].astype(str) == qid) & (pool["system"] == "BM25")].copy()
        labels_q = qrels[qrels["qid"].astype(str) == qid][["docno", "label"]]
        pool_q = pool_q.merge(labels_q, on="docno", how="left")
        pool_q["label"] = pool_q["label"].fillna(0)
        nonrel = pool_q.sort_values("rank")
        nonrel = nonrel[nonrel["label"] <= 0].head(3)
        nonrel_docs = ", ".join(nonrel["docno"].astype(str).tolist()) if not nonrel.empty else "N/A"

        reason, fix = _reason_and_fix(qtype, delta)
        evidence = (
            f"BM25 nDCG@10={bm25_ndcg:.4f}, BM25 P@5={float(row.bm25_P_5):.4f}, "
            f"Recall@10={float(row.bm25_recall10):.4f}"
        )
        if es_ndcg is not None:
            evidence += f"; ES nDCG@10={es_ndcg:.4f} (delta={delta:+.4f})"

        lines.extend(
            [
                f"## Case {i}",
                f"- Query ID: `{qid}`",
                f"- Query: `{qtext}`",
                f"- Query type: `{qtype}`",
                f"- Expected relevant documents: {intent}",
                f"- Top-ranked non-relevant results: {nonrel_docs}",
                f"- Failure reason: {reason}",
                f"- Evidence: {evidence}",
                f"- Proposed fix (do not implement): {fix}",
                "",
            ]
        )

    ensure_dir(out_path.parent)
    out_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    """CLI entrypoint for auto-generating error analysis markdown."""
    parser = argparse.ArgumentParser(description="Create error analysis report from current outputs.")
    parser.add_argument("--queries", default="data/processed/queries.tsv")
    parser.add_argument("--templates", default="data/processed/query_templates.tsv")
    parser.add_argument("--per-query", default="outputs/eval/per_query_metrics.csv")
    parser.add_argument("--es-per-query", default="outputs/extension/es_per_query_metrics.csv")
    parser.add_argument("--pool", default="data/processed/pooled_candidates.tsv")
    parser.add_argument("--qrels", default="data/processed/qrels.tsv")
    parser.add_argument("--out", default="reports/error_analysis.md")
    parser.add_argument("--cases", type=int, default=5)
    args = parser.parse_args()

    build_error_analysis(
        queries_path=Path(args.queries),
        templates_path=Path(args.templates),
        perq_path=Path(args.per_query),
        es_perq_path=Path(args.es_per_query),
        pool_path=Path(args.pool),
        qrels_path=Path(args.qrels),
        out_path=Path(args.out),
        n_cases=args.cases,
    )
    print(f"Wrote error analysis report to {args.out}")


if __name__ == "__main__":
    main()
