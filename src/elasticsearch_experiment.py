"""Elasticsearch extension experiment (Phase 8)."""

from __future__ import annotations

import argparse
import math
from pathlib import Path

import pandas as pd
import requests
from scipy.stats import ttest_rel

from src.utils import ensure_dir, read_jsonl


def _dcg_at_k(labels: list[float], k: int) -> float:
    """Compute DCG@k for graded relevance labels."""
    score = 0.0
    for i, rel in enumerate(labels[:k], start=1):
        score += (2**rel - 1) / math.log2(i + 1)
    return score


def _ndcg_at_k(rels: list[float], ideal_rels: list[float], k: int) -> float:
    """Compute nDCG@k given ranked and ideal labels."""
    dcg = _dcg_at_k(rels, k)
    idcg = _dcg_at_k(sorted(ideal_rels, reverse=True), k)
    return float(dcg / idcg) if idcg > 0 else 0.0


def _average_precision(rels: list[float]) -> float:
    """Compute AP treating labels > 0 as relevant."""
    relevant = 0
    precision_sum = 0.0
    for i, rel in enumerate(rels, start=1):
        if rel > 0:
            relevant += 1
            precision_sum += relevant / i
    return float(precision_sum / relevant) if relevant > 0 else 0.0


def _metrics_for_query(run_docnos: list[str], qrels_for_qid: pd.DataFrame) -> dict[str, float]:
    """Compute P@5, Recall@10, MAP, and nDCG@10 for one query."""
    label_map = dict(zip(qrels_for_qid["docno"], qrels_for_qid["label"]))
    ranked_labels = [float(label_map.get(docno, 0)) for docno in run_docnos]
    relevant_total = int((qrels_for_qid["label"] > 0).sum())
    p5 = sum(1 for rel in ranked_labels[:5] if rel > 0) / 5.0
    rel10 = sum(1 for rel in ranked_labels[:10] if rel > 0)
    recall10 = float(rel10 / relevant_total) if relevant_total > 0 else 0.0
    ap = _average_precision(ranked_labels)
    ndcg10 = _ndcg_at_k(ranked_labels, qrels_for_qid["label"].astype(float).tolist(), 10)
    return {"P_5": p5, "recall_10": recall10, "map": ap, "ndcg_cut_10": ndcg10}


def _es_request(base_url: str, method: str, endpoint: str, body: dict | None = None) -> requests.Response:
    """Issue a JSON request to Elasticsearch and raise on HTTP error."""
    url = f"{base_url.rstrip('/')}/{endpoint.lstrip('/')}"
    response = requests.request(method, url, json=body, timeout=60)
    response.raise_for_status()
    return response


def run_elasticsearch_extension(
    corpus_path: Path,
    queries_path: Path,
    qrels_path: Path,
    out_dir: Path,
    index_name: str = "temple_ir",
    base_url: str = "http://localhost:9200",
    top_k: int = 100,
) -> None:
    """Index deduped corpus into Elasticsearch and evaluate BM25 results."""
    ensure_dir(out_dir)

    ping = requests.get(base_url, timeout=10)
    ping.raise_for_status()

    # Reset index.
    requests.delete(f"{base_url.rstrip('/')}/{index_name}", timeout=60)
    _es_request(
        base_url,
        "PUT",
        index_name,
        {
            "settings": {"index": {"number_of_shards": 1, "number_of_replicas": 0}},
            "mappings": {"properties": {"docno": {"type": "keyword"}, "text": {"type": "text"}}},
        },
    )

    docs = read_jsonl(corpus_path)
    bulk_lines: list[str] = []

    def flush_bulk(lines: list[str]) -> None:
        """Send one NDJSON bulk batch to Elasticsearch."""
        if not lines:
            return
        payload = "\n".join(lines) + "\n"
        headers = {"Content-Type": "application/x-ndjson"}
        bulk_resp = requests.post(
            f"{base_url.rstrip('/')}/_bulk",
            data=payload.encode("utf-8"),
            headers=headers,
            timeout=600,
        )
        bulk_resp.raise_for_status()
        body = bulk_resp.json()
        if body.get("errors"):
            raise RuntimeError("Elasticsearch bulk indexing reported per-item errors.")

    for row in docs:
        docno = row.get("docno")
        text = row.get("text", "")
        if not isinstance(docno, str):
            continue
        bulk_lines.append(f'{{"index": {{"_index": "{index_name}", "_id": "{docno}"}}}}')
        bulk_lines.append(pd.Series({"docno": docno, "text": text}).to_json(force_ascii=False))
        if len(bulk_lines) >= 2000:
            flush_bulk(bulk_lines)
            bulk_lines = []

    flush_bulk(bulk_lines)
    _es_request(base_url, "POST", f"{index_name}/_refresh")

    queries = pd.read_csv(queries_path, sep="\t")
    qrels = pd.read_csv(qrels_path, sep="\t")
    templates_path = queries_path.parent / "query_templates.tsv"
    templates = pd.read_csv(templates_path, sep="\t") if templates_path.exists() else pd.DataFrame()

    per_rows: list[dict] = []
    for _, q in queries.iterrows():
        qid = str(q["qid"])
        query_text = str(q["query"])
        search_resp = _es_request(
            base_url,
            "POST",
            f"{index_name}/_search",
            {"size": top_k, "query": {"match": {"text": {"query": query_text}}}},
        ).json()
        hits = search_resp.get("hits", {}).get("hits", [])
        run_docnos = [str(hit.get("_id", "")) for hit in hits]
        qrel_q = qrels[qrels["qid"].astype(str) == qid]
        if qrel_q.empty:
            metrics = {"P_5": 0.0, "recall_10": 0.0, "map": 0.0, "ndcg_cut_10": 0.0}
        else:
            metrics = _metrics_for_query(run_docnos, qrel_q)
        per_rows.append({"name": "ElasticsearchBM25", "qid": qid, **metrics})

    perq = pd.DataFrame(per_rows)
    perq.to_csv(out_dir / "es_per_query_metrics.csv", index=False)

    aggregate = pd.DataFrame(
        [
            {
                "name": "ElasticsearchBM25",
                "map": float(perq["map"].mean()),
                "P_5": float(perq["P_5"].mean()),
                "recall_10": float(perq["recall_10"].mean()),
                "ndcg_cut_10": float(perq["ndcg_cut_10"].mean()),
            }
        ]
    )
    aggregate.to_csv(out_dir / "es_aggregate_metrics.csv", index=False)

    if not templates.empty and {"qid", "query_type"}.issubset(templates.columns):
        merged = perq.merge(templates[["qid", "query_type"]], on="qid", how="left")
        by_type = (
            merged.groupby("query_type", dropna=False)[["map", "P_5", "recall_10", "ndcg_cut_10"]]
            .mean()
            .reset_index()
        )
        by_type.to_csv(out_dir / "es_metrics_by_query_type.csv", index=False)

    bm25_perq_path = Path("outputs/eval/per_query_metrics.csv")
    if bm25_perq_path.exists():
        bm25 = pd.read_csv(bm25_perq_path)
        bm25 = bm25[bm25["name"] == "BM25"][["qid", "ndcg_cut_10"]].rename(columns={"ndcg_cut_10": "bm25_ndcg"})
        joined = perq[["qid", "ndcg_cut_10"]].rename(columns={"ndcg_cut_10": "es_ndcg"}).merge(bm25, on="qid")
        if not joined.empty:
            t = ttest_rel(joined["es_ndcg"], joined["bm25_ndcg"])
            pd.DataFrame(
                [
                    {
                        "pair": "ElasticsearchBM25 vs PyTerrier BM25",
                        "t_stat": float(t.statistic),
                        "p_value": float(t.pvalue),
                    }
                ]
            ).to_csv(out_dir / "es_vs_pyterrier_ttest.csv", index=False)


def main() -> None:
    """CLI entrypoint for Elasticsearch extension experiment."""
    parser = argparse.ArgumentParser(description="Run Elasticsearch comparison experiment.")
    parser.add_argument("--corpus", default="data/raw/corpus_deduped.jsonl")
    parser.add_argument("--queries", default="data/processed/queries.tsv")
    parser.add_argument("--qrels", default="data/processed/qrels.tsv")
    parser.add_argument("--out-dir", default="outputs/extension")
    parser.add_argument("--index-name", default="temple_ir")
    parser.add_argument("--base-url", default="http://localhost:9200")
    parser.add_argument("--top-k", type=int, default=100)
    args = parser.parse_args()

    run_elasticsearch_extension(
        corpus_path=Path(args.corpus),
        queries_path=Path(args.queries),
        qrels_path=Path(args.qrels),
        out_dir=Path(args.out_dir),
        index_name=args.index_name,
        base_url=args.base_url,
        top_k=args.top_k,
    )
    print(f"Elasticsearch extension outputs saved to {args.out_dir}")


if __name__ == "__main__":
    main()
