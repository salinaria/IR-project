"""Shared utility helpers for the Temple IR pipeline."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable


def ensure_dir(path: Path) -> None:
    """Create a directory path if it does not already exist."""
    path.mkdir(parents=True, exist_ok=True)


def write_jsonl(path: Path, rows: Iterable[dict]) -> None:
    """Write records to a JSONL file using UTF-8 encoding."""
    with path.open("w", encoding="utf-8") as file:
        for row in rows:
            file.write(json.dumps(row, ensure_ascii=False) + "\n")


def read_jsonl(path: Path) -> list[dict]:
    """Read JSONL records into memory for downstream processing."""
    rows: list[dict] = []
    with path.open("r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows
