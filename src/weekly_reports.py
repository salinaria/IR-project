"""Generate week-by-week markdown report drafts."""

from __future__ import annotations

from pathlib import Path

from src.utils import ensure_dir


WEEK_SECTIONS = {
    1: "Data Collection",
    2: "Indexing and Collection Analysis",
    3: "Collaborative Query Construction",
    4: "Pooling and Relevance Judgments",
    5: "Baseline Retrieval Models",
    6: "Parameter Sensitivity",
    7: "Optimization Experiment",
    8: "Modern Extension",
    9: "Error Analysis",
    10: "Final Integration and Presentation",
}


def render_week(week: int, title: str) -> str:
    """Create a consistent markdown template for each project week."""
    return f"""# Week {week}: {title}

## Objectives
- Document goals for this phase.
- Record implementation details and execution steps.

## Work Completed
- Add completed tasks here.

## Commands and Reproducibility
```bash
# Add exact commands run this week
```

## Results
- Include metrics, plots, and observations.

## Problems and Fixes
- Explain errors, root causes, and corrective actions.

## Next Steps
- List action items for upcoming week.
"""


def generate_reports(reports_dir: Path) -> None:
    """Create all weekly report markdown files and a final report shell."""
    ensure_dir(reports_dir)
    for week, title in WEEK_SECTIONS.items():
        (reports_dir / f"week_{week:02d}.md").write_text(render_week(week, title), encoding="utf-8")

    final_text = """# Final Project Report

## Introduction
Describe project goals, scope, and motivation.

## System Design
Explain architecture, crawling, indexing, and retrieval pipeline.

## Experiments
- Baseline models
- Parameter sensitivity
- Optimization
- Modern extension

## Error Analysis
Provide at least 5 failure cases with root-cause analysis.

## Reproducibility
Provide complete step-by-step commands to run the system.

## References
List papers, datasets, and software libraries.
"""
    (reports_dir / "final_report.md").write_text(final_text, encoding="utf-8")


if __name__ == "__main__":
    generate_reports(Path("reports"))
    print("Weekly report templates created.")
