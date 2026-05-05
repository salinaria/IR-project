"""Generate query template TSV files from the class query CSV."""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

from src.utils import ensure_dir


def normalize_query_text(text: str) -> str:
    """Normalize query text to parser-safe punctuation and whitespace."""
    mapped = (
        text.replace("\u2018", "'")
        .replace("\u2019", "'")
        .replace("\u201c", '"')
        .replace("\u201d", '"')
        .replace("\u2013", "-")
        .replace("\u2014", "-")
    )
    ascii_safe = mapped.encode("ascii", "ignore").decode("ascii")
    # Terrier's MatchOp parser can fail on quotes/apostrophes in some modes.
    ascii_safe = ascii_safe.replace("'", " ").replace('"', " ")
    ascii_safe = re.sub(r"[^A-Za-z0-9\-\s]", " ", ascii_safe)
    return re.sub(r"\s+", " ", ascii_safe).strip()


def normalize_query_type(value: str) -> str:
    """Normalize free-form query type labels to consistent snake_case values."""
    cleaned = (value or "").strip().lower().replace("/", "_").replace(" ", "_")
    if cleaned in {"navigational", "informational", "transactional", "broad"}:
        return cleaned
    if cleaned in {"broad_ambiguous", "broad_/_ambiguous"}:
        return "broad_ambiguous"
    return "unknown"


def build_student_queries(query_list_path: Path) -> pd.DataFrame:
    """Load `Query_List.csv` and emit cleaned query templates with generated QIDs."""
    try:
        frame = pd.read_csv(query_list_path, encoding="utf-8")
    except UnicodeDecodeError:
        # Class-contributed CSV files are often exported in cp1252 from Excel.
        frame = pd.read_csv(query_list_path, encoding="cp1252")
    frame = frame.rename(
        columns={
            "query_text": "query",
            "query_type": "query_type",
            "intent_description": "intent",
            "expected_doc_types": "expected_doc_types",
        }
    )
    for col in ["query", "query_type", "intent", "expected_doc_types"]:
        if col not in frame.columns:
            frame[col] = ""

    frame["query"] = (
        frame["query"].fillna("").astype(str).map(normalize_query_text)
    )
    frame = frame[frame["query"] != ""].copy()
    frame = frame.drop_duplicates(subset=["query"], keep="first").reset_index(drop=True)
    frame["query_type"] = frame["query_type"].fillna("").astype(str).map(normalize_query_type)
    frame["intent"] = frame["intent"].fillna("").astype(str).str.strip()
    frame["expected_doc_types"] = frame["expected_doc_types"].fillna("").astype(str).str.strip()
    frame["qid"] = [f"Q{i:03d}" for i in range(1, len(frame) + 1)]
    return frame[["qid", "query", "query_type", "intent", "expected_doc_types"]]


def main() -> None:
    """Write query template files used by pooling and evaluation steps."""
    out_dir = Path("data/processed")
    ensure_dir(out_dir)
    query_list_path = Path("Query_List.csv")
    if not query_list_path.exists():
        raise FileNotFoundError(
            "Query_List.csv not found at project root. Add it and re-run."
        )

    full = build_student_queries(query_list_path)
    full.to_csv(out_dir / "query_templates.tsv", sep="\t", index=False)
    full[["qid", "query"]].to_csv(out_dir / "queries.tsv", sep="\t", index=False)

    qrels = pd.DataFrame(columns=["qid", "docno", "label"])
    qrels.to_csv(out_dir / "qrels.tsv", sep="\t", index=False)
    print(f"Query templates and empty qrels file created ({len(full)} queries).")


if __name__ == "__main__":
    main()
