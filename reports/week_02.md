# Week 2: Indexing and Collection Analysis

## Deliverables
- [x] PyTerrier index (`index/terrier`).
- [x] Summary table: documents, file types, vocabulary, tokens.
- [x] Zipf (log-log), doc length hist, stopword stats, word cloud.

## Results (deduped corpus)
| metric | value |
| --- | --- |
| documents | 42217.0 |
| vocabulary_size | 214003.0 |
| token_count | 37491119.0 |
| avg_doc_length | 888.0573939408296 |


### Artifacts
- `outputs/analysis/file_type_distribution.csv`
- `outputs/analysis/zipf_loglog.png` (empirical rank–frequency + **dashed** log–log OLS fit)
- `outputs/analysis/zipf_power_law_fit.csv`
- `outputs/analysis/doc_length_distribution.png`
- `outputs/analysis/stopword_analysis.csv` (NLTK + corpus TF–IDF low-IDF stoplist mix)
- `outputs/analysis/corpus_tfidf_stopwords.csv` (lowest-IDF terms used as corpus stopwords)
- `outputs/analysis/wordcloud_top_terms.png`

### Corpus-specific stopwords (TF–IDF)
Low document-level IDF ≈ globally frequent boilerplate across `temple.edu` pages. Those terms are merged with NLTK English stopwords before top-20/word-cloud analysis (see CSVs above).

### Rubric gap
- Crawl pipeline records **HTML only** (`file_type=html`). For Word/PDF counts from live site, add download + text extraction (e.g. `pdfplumber`, `python-docx`) in a follow-up ingest script.
