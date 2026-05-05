"""Generate query contribution templates and starter TSV files."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.utils import ensure_dir


def build_student_queries() -> pd.DataFrame:
    """Create a starter set of 15 queries categorized by intent type."""
    rows = [
        ("Q001", "temple university admissions portal", "navigational", "Find official admissions page", "html"),
        ("Q002", "temple financial aid office", "navigational", "Locate aid office page", "html"),
        ("Q003", "temple registrar forms", "navigational", "Find registrar forms", "pdf/html"),
        ("Q004", "temple cs department homepage", "navigational", "Find CS department homepage", "html"),
        ("Q005", "temple library hours", "navigational", "Find official library hours page", "html"),
        ("Q006", "temple application deadlines", "informational", "Learn major deadlines", "html/pdf"),
        ("Q007", "temple tuition and fees", "informational", "Find tuition information", "html/pdf"),
        ("Q008", "temple campus housing options", "informational", "Understand housing choices", "html"),
        ("Q009", "temple scholarship opportunities", "informational", "Discover scholarship information", "html/pdf"),
        ("Q010", "temple transfer student requirements", "informational", "Find transfer requirements", "html/pdf"),
        ("Q011", "temple programs", "broad_ambiguous", "Explore possible degree programs", "html"),
        ("Q012", "temple health services", "broad_ambiguous", "Could refer to many health pages", "html/pdf"),
        ("Q013", "temple student support", "broad_ambiguous", "May include many support units", "html"),
        ("Q014", "temple policies", "broad_ambiguous", "General policy-related need", "pdf/html"),
        ("Q015", "temple calendar", "broad_ambiguous", "Could indicate academic or events calendar", "html"),
    ]
    return pd.DataFrame(
        rows, columns=["qid", "query", "query_type", "intent", "expected_doc_types"]
    )


def main() -> None:
    """Write query template files used by pooling and evaluation steps."""
    out_dir = Path("data/processed")
    ensure_dir(out_dir)
    full = build_student_queries()
    full.to_csv(out_dir / "query_templates.tsv", sep="\t", index=False)
    full[["qid", "query"]].to_csv(out_dir / "queries.tsv", sep="\t", index=False)

    qrels = pd.DataFrame(columns=["qid", "docno", "label"])
    qrels.to_csv(out_dir / "qrels.tsv", sep="\t", index=False)
    print("Query templates and empty qrels file created.")


if __name__ == "__main__":
    main()
