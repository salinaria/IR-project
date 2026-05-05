# Temple IR Project (10-Week End-to-End Pipeline)

This repository contains a complete implementation pipeline for the Temple domain IR project:

1. Crawl and clean the `temple.edu` corpus
2. Build a PyTerrier index
3. Generate collection analysis outputs
4. Create query templates and run pooling
5. Evaluate baseline retrieval models
6. Run BM25 parameter sensitivity experiments
7. Run optimization experiments
8. Run a modern extension experiment
9. Generate error analysis artifacts
10. Produce week-by-week report drafts

## Quick Start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m src.pipeline --max-docs 100000 --start-url https://www.temple.edu
```

After you have new crawl data, **rebuild everything downstream** (dedupe, index, analysis, pooling, bootstrap qrels, eval, sensitivity, optimization, Markdown reports, and LaTeX):

```bash
make refresh
```

`make refresh` runs `src.refresh_phase_outputs`, which **overwrites** `index/terrier` from `data/raw/corpus_deduped.jsonl` (PyTerrier `overwrite=True`).

## Expected Outputs

- `data/raw/`: crawled pages and metadata (`corpus.jsonl`)
- `data/raw/corpus_deduped.jsonl`: first row per `docno`
- `data/processed/`: queries, pool, qrels files
- `index/`: PyTerrier index
- `outputs/analysis/`: tables and plots (Zipf, doc length, word cloud)
- `outputs/eval/`: model metrics and statistical tests
- `outputs/optimization/`: latency/scoring/ranking comparisons
- `reports/`: weekly Markdown (`week_*.md`), `final_report.md`, `DELIVERABLES.md`, **`HOW_IT_WORKS.md`** (plain-language pipeline + challenges)
- `reports/tex/`: LaTeX sources + `main.pdf` if you run `pdflatex` (see `reports/tex/README.md`)

## Notes

- CUDA is only used if available for optional neural reranking.
- For strict reproducibility, run scripts from project root.
- If crawling is blocked by robots or network policy, swap in a provided class crawl dump.
