"""Collection analysis for distribution, Zipf, length, and stopwords."""

from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path

import matplotlib.pyplot as plt
import nltk
import pandas as pd
from wordcloud import WordCloud

from src.utils import ensure_dir, read_jsonl


def tokenize(text: str) -> list[str]:
    """Simple lowercase tokenization that keeps alphanumeric tokens."""
    return [t.lower() for t in nltk.word_tokenize(text) if any(c.isalnum() for c in t)]


def run_analysis(corpus_path: Path, output_dir: Path) -> None:
    """Compute collection-level statistics and save visualizations."""
    nltk.download("punkt", quiet=True)
    nltk.download("punkt_tab", quiet=True)
    nltk.download("stopwords", quiet=True)
    stopwords = set(nltk.corpus.stopwords.words("english"))

    docs = read_jsonl(corpus_path)
    ensure_dir(output_dir)

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
    plt.loglog(ranks[:5000], sorted_freqs[:5000])
    plt.title("Zipf's Law (Temple Corpus)")
    plt.xlabel("Rank (log)")
    plt.ylabel("Frequency (log)")
    plt.tight_layout()
    plt.savefig(output_dir / "zipf_loglog.png")
    plt.close()

    plt.figure(figsize=(8, 5))
    plt.hist(lengths, bins=40)
    plt.title("Document Length Distribution")
    plt.xlabel("Document Length (tokens)")
    plt.ylabel("Count")
    plt.tight_layout()
    plt.savefig(output_dir / "doc_length_distribution.png")
    plt.close()

    non_stop = [t for t in all_tokens if t not in stopwords and t.isalpha()]
    top_20 = Counter(non_stop).most_common(20)
    pd.DataFrame(top_20, columns=["term", "count"]).to_csv(
        output_dir / "top20_non_stopwords.csv", index=False
    )

    cloud = WordCloud(width=1200, height=600, background_color="white").generate(
        " ".join(non_stop[:200000])
    )
    cloud.to_file(str(output_dir / "wordcloud_top_terms.png"))

    stopword_fraction = (sum(1 for t in all_tokens if t in stopwords) / max(1, token_count),)
    pd.DataFrame(
        [{"stopword_fraction": stopword_fraction[0], "non_stopword_fraction": 1 - stopword_fraction[0]}]
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
