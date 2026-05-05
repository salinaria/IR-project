"""Build a PyTerrier index from collected Temple corpus."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd
import pyterrier as pt

from src.utils import ensure_dir, read_jsonl


def build_index(corpus_path: Path, index_dir: Path) -> int:
    """Create Terrier index for document retrieval experiments."""
    if not pt.java.started():
        pt.java.init()

    docs = read_jsonl(corpus_path)
    frame = pd.DataFrame(docs)
    if frame.empty:
        raise ValueError("Corpus is empty; crawl data before indexing.")

    # Resumed crawls can append rows with reused docnos; Terrier requires unique docno.
    if "docno" in frame.columns:
        before = len(frame)
        frame = frame.drop_duplicates(subset=["docno"], keep="first")
        if len(frame) < before:
            print(f"Dropped {before - len(frame)} duplicate docno rows before indexing.")

    # Use an absolute path: some Terrier builds resolve relative paths under ./var/ and fail if missing.
    index_dir = index_dir.resolve()
    ensure_dir(index_dir)
    # Terrier 5.11 / PyTerrier 1.x: declare indexed text columns on the indexer, not via index(..., fields=).
    max_docno = int(frame["docno"].str.len().max()) if "docno" in frame.columns else 20
    meta_docno_len = max(32, max_docno + 8)
    indexer = pt.IterDictIndexer(
        str(index_dir),
        meta={"docno": meta_docno_len},
        text_attrs=["text"],
        overwrite=True,
    )
    index_ref = indexer.index(frame[["docno", "text"]].to_dict(orient="records"))
    print(f"Index created at {index_ref}")
    return len(frame)


def main() -> None:
    """CLI wrapper for building PyTerrier index."""
    parser = argparse.ArgumentParser(description="Build PyTerrier index.")
    parser.add_argument("--corpus", default="data/raw/corpus.jsonl")
    parser.add_argument("--index-dir", default="index/terrier")
    args = parser.parse_args()
    doc_count = build_index(Path(args.corpus), Path(args.index_dir))
    print(f"Indexed {doc_count} documents.")


if __name__ == "__main__":
    main()
