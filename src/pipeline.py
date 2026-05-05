"""End-to-end runner for core Temple IR project stages."""

from __future__ import annotations

import argparse
from pathlib import Path

from src.build_index import build_index
from src.collection_analysis import run_analysis
from src.crawl_temple import crawl_domain
from src.utils import ensure_dir
from src.weekly_reports import generate_reports


def run_pipeline(start_url: str, max_docs: int, delay: float) -> None:
    """Run crawl, index build, analysis, and report scaffolding in sequence."""
    raw_path = Path("data/raw/corpus.jsonl")
    ensure_dir(raw_path.parent)
    crawl_domain(
        start_url=start_url,
        max_docs=max_docs,
        delay=delay,
        output_path=raw_path,
        checkpoint_every=100,
    )

    build_index(raw_path, Path("index/terrier"))
    run_analysis(raw_path, Path("outputs/analysis"))
    generate_reports(Path("reports"))


def main() -> None:
    """CLI entrypoint for one-command pipeline execution."""
    parser = argparse.ArgumentParser(description="Temple IR end-to-end pipeline.")
    parser.add_argument("--start-url", default="https://www.temple.edu")
    parser.add_argument("--max-docs", type=int, default=100000)
    parser.add_argument("--delay", type=float, default=0.1)
    args = parser.parse_args()
    run_pipeline(args.start_url, args.max_docs, args.delay)
    print("Core pipeline completed.")


if __name__ == "__main__":
    main()
