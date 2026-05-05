"""Write a corpus JSONL with unique docno (first occurrence wins)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.utils import ensure_dir


def dedupe_jsonl(input_path: Path, output_path: Path) -> tuple[int, int]:
    """Stream input JSONL and emit first row per ``docno``.

    Returns (lines_read, lines_written).
    """
    ensure_dir(output_path.parent)
    seen: set[str] = set()
    read_count = 0
    write_count = 0
    with input_path.open("r", encoding="utf-8") as infile, output_path.open(
        "w", encoding="utf-8"
    ) as outfile:
        for line in infile:
            line = line.strip()
            if not line:
                continue
            read_count += 1
            row = json.loads(line)
            docno = row.get("docno")
            if not docno or docno in seen:
                continue
            seen.add(docno)
            outfile.write(json.dumps(row, ensure_ascii=False) + "\n")
            write_count += 1
    return read_count, write_count


def main() -> None:
    """CLI for deduplicating corpus JSONL by docno."""
    parser = argparse.ArgumentParser(description="Deduplicate corpus JSONL by docno.")
    parser.add_argument("--input", default="data/raw/corpus.jsonl")
    parser.add_argument("--output", default="data/raw/corpus_deduped.jsonl")
    args = parser.parse_args()
    inp, outp = Path(args.input), Path(args.output)
    read_n, write_n = dedupe_jsonl(inp, outp)
    print(f"Deduped {read_n} lines -> {write_n} unique docs written to {outp}")


if __name__ == "__main__":
    main()
