"""Collection analysis for distribution, Zipf, length, and stopwords."""

from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import nltk
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from wordcloud import WordCloud

from src.utils import ensure_dir, read_jsonl


def tokenize(text: str) -> list[str]:
    """Simple lowercase tokenization that keeps alphanumeric tokens."""
    return [t.lower() for t in nltk.word_tokenize(text) if any(c.isalnum() for c in t)]


def corpus_tfidf_stopwords(
    raw_docs: list[str],
    n_candidates: int,
    nltk_exclude: set[str],
) -> pd.DataFrame:
    """Identify domain boilerplate tokens via low corpus IDF (very common across documents).

    Sklearn TF-IDF IDF(term) decreases as document frequency increases; the lowest-IDF terms
    behave like corpus-specific ``stopwords'' (navigation boilerplate, site-wide phrases).
    """
    n_docs = max(len(raw_docs), 1)
    min_abs = max(5, min(500, int(0.01 * n_docs)))

    vect = TfidfVectorizer(
        lowercase=True,
        token_pattern=r"(?u)\b[a-zA-Z]{2,}\b",
        min_df=min_abs,
        max_df=0.98,
        sublinear_tf=True,
        strip_accents="unicode",
        max_features=100_000,
    )
    vect.fit(raw_docs)
    names = vect.get_feature_names_out()
    idfs = vect.idf_
    order = np.argsort(idfs)
    picked: list[int] = []
    for idx in order:
        term = names[idx]
        if term in nltk_exclude:
            continue
        picked.append(int(idx))
        if len(picked) >= n_candidates:
            break
    rows = [{"term": names[i], "idf_sklearn_default": float(idfs[i])} for i in picked]
    return pd.DataFrame(rows)


def run_analysis(corpus_path: Path, output_dir: Path) -> None:
    """Compute collection-level statistics and save visualizations."""
    nltk.download("punkt", quiet=True)
    nltk.download("punkt_tab", quiet=True)
    nltk.download("stopwords", quiet=True)
    nltk_basic = set(nltk.corpus.stopwords.words("english"))

    docs = read_jsonl(corpus_path)
    ensure_dir(output_dir)

    raw_texts = [str(doc.get("text", "") or "") for doc in docs]
    corpus_stop_df = corpus_tfidf_stopwords(raw_texts, n_candidates=250, nltk_exclude=nltk_basic)
    corpus_stop_terms = set(corpus_stop_df["term"])
    merged_stopwords = nltk_basic | corpus_stop_terms
    corpus_stop_df.to_csv(output_dir / "corpus_tfidf_stopwords.csv", index=False)

    file_types = Counter(doc.get("file_type", "unknown") for doc in docs)
    all_tokens: list[str] = []
    lengths: list[int] = []

    for doc in docs:
        tokens = tokenize(doc.get("text", ""))
        all_tokens.extend(tokens)
        lengths.append(len(tokens))

    token_counter = Counter(all_tokens)
    vocab_size = len(token_counter)
    token_count = len(all_tokens)

    summary = pd.DataFrame(
        {
            "metric": ["documents", "vocabulary_size", "token_count", "avg_doc_length"],
            "value": [len(docs), vocab_size, token_count, sum(lengths) / max(len(lengths), 1)],
        }
    )
    summary.to_csv(output_dir / "collection_summary.csv", index=False)
    pd.DataFrame(file_types.items(), columns=["file_type", "count"]).to_csv(
        output_dir / "file_type_distribution.csv", index=False
    )

    sorted_freqs = sorted(token_counter.values(), reverse=True)
    ranks = list(range(1, len(sorted_freqs) + 1))
    plt.figure(figsize=(8, 5))
    n_plot = min(5000, len(sorted_freqs))
    r_np = np.array(ranks[:n_plot], dtype=float)
    f_np = np.array(sorted_freqs[:n_plot], dtype=float)
    valid = (r_np > 0) & (f_np > 0)
    log_r = np.log(r_np[valid])
    log_f = np.log(f_np[valid])
    slope, intercept = np.polyfit(log_r, log_f, deg=1)
    fit_f = np.exp(intercept + slope * log_r)

    plt.loglog(ranks[:n_plot], sorted_freqs[:n_plot], color="tab:blue", label="Empirical frequencies", lw=1.2)
    plt.plot(
        r_np[valid],
        fit_f,
        "k--",
        linewidth=2,
        label=f"OLS fit log f = {slope:.3f} log r + {intercept:.3f}",
    )
    plt.title("Zipf's Law — Temple Corpus (log-log)")
    plt.xlabel("Rank")
    plt.ylabel("Token frequency")
    plt.legend(fontsize="small")
    plt.tight_layout()
    plt.savefig(output_dir / "zipf_loglog.png", dpi=160)
    plt.close()

    fit_row = pd.DataFrame(
        [
            {
                "n_points_zipf_fit": int(valid.sum()),
                "log_rank_log_freq_slope": float(slope),
                "intercept_log_space": float(intercept),
            }
        ]
    )
    fit_row.to_csv(output_dir / "zipf_power_law_fit.csv", index=False)

    plt.figure(figsize=(8, 5))
    plt.hist(lengths, bins=40)
    plt.title("Document Length Distribution")
    plt.xlabel("Document Length (tokens)")
    plt.ylabel("Count")
    plt.tight_layout()
    plt.savefig(output_dir / "doc_length_distribution.png")
    plt.close()

    non_stop = [t for t in all_tokens if t not in merged_stopwords and t.isalpha()]
    top_20 = Counter(non_stop).most_common(20)
    pd.DataFrame(top_20, columns=["term", "count"]).to_csv(
        output_dir / "top20_non_stopwords.csv", index=False
    )

    cloud = WordCloud(width=1200, height=600, background_color="white").generate(
        " ".join(non_stop[:200000])
    )
    cloud.to_file(str(output_dir / "wordcloud_top_terms.png"))

    nltk_only_frac = sum(1 for t in all_tokens if t in nltk_basic) / max(1, token_count)
    corpus_stop_frac_only = (
        sum(1 for t in all_tokens if t in corpus_stop_terms and t not in nltk_basic) / max(1, token_count),
    )
    merged_frac = sum(1 for t in all_tokens if t in merged_stopwords) / max(1, token_count)

    pd.DataFrame(
        [
            {
                "stopword_fraction_nltk_only": nltk_only_frac,
                "corpus_stopword_fraction_tfidf_only": corpus_stop_frac_only[0],
                "merged_stopword_fraction": merged_frac,
                "non_stopword_fraction_after_merge": 1 - merged_frac,
                "n_corpus_stopwords_tfidf": len(corpus_stop_terms),
                "n_merged_stopwords": len(merged_stopwords),
            }
        ]
    ).to_csv(output_dir / "stopword_analysis.csv", index=False)


def main() -> None:
    """CLI entrypoint for collection analysis."""
    parser = argparse.ArgumentParser(description="Run collection analysis plots and tables.")
    parser.add_argument("--corpus", default="data/raw/corpus.jsonl")
    parser.add_argument("--output-dir", default="outputs/analysis")
    args = parser.parse_args()
    run_analysis(Path(args.corpus), Path(args.output_dir))
    print(f"Analysis written to {args.output_dir}")


if __name__ == "__main__":
    main()
