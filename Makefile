PY := .venv/bin/python3

.PHONY: setup crawl index analyze reports pool eval sensitivity optimize all

setup:
	python3 -m venv .venv
	.venv/bin/pip install -r requirements.txt

crawl:
	$(PY) -m src.crawl_temple --start-url https://www.temple.edu --max-docs 100000

index:
	$(PY) -m src.build_index --corpus data/raw/corpus_deduped.jsonl --index-dir index/terrier

analyze:
	$(PY) -m src.collection_analysis --corpus data/raw/corpus_deduped.jsonl --output-dir outputs/analysis

reports:
	$(PY) -m src.weekly_reports
	$(PY) -m src.generate_query_templates

pool:
	$(PY) -m src.pooling --index-dir index/terrier --queries data/processed/queries.tsv

eval:
	$(PY) -m src.evaluate_models --index-dir index/terrier --queries data/processed/queries.tsv --qrels data/processed/qrels.tsv

sensitivity:
	$(PY) -m src.bm25_sensitivity --index-dir index/terrier --queries data/processed/queries.tsv --qrels data/processed/qrels.tsv

optimize:
	$(PY) -m src.optimization_experiment --index-dir index/terrier --queries data/processed/queries.tsv

all:
	$(PY) -m src.pipeline --max-docs 100000 --start-url https://www.temple.edu

refresh:
	$(PY) -m src.refresh_phase_outputs
