"""Temple domain crawler to collect text documents for indexing."""

from __future__ import annotations

import argparse
import json
import re
import time
from collections import deque
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from tqdm import tqdm

from src.utils import ensure_dir, write_jsonl


TEXT_PATTERN = re.compile(r"\s+")


def normalize_text(raw_text: str) -> str:
    """Normalize text blocks to reduce whitespace and noise."""
    return TEXT_PATTERN.sub(" ", raw_text).strip()


def extract_links(soup: BeautifulSoup, base_url: str) -> list[str]:
    """Extract and normalize all hyperlinks from a page."""
    links: list[str] = []
    for tag in soup.find_all("a", href=True):
        full_url = urljoin(base_url, tag["href"])
        parsed = urlparse(full_url)
        if parsed.scheme in {"http", "https"}:
            links.append(f"{parsed.scheme}://{parsed.netloc}{parsed.path}")
    return links


def is_temple_url(url: str) -> bool:
    """Validate that URL belongs to the temple.edu domain."""
    host = urlparse(url).netloc.lower()
    return host.endswith("temple.edu")


def scan_resume_state(output_path: Path) -> tuple[int, set[str]]:
    """Scan JSONL on disk without loading all docs into RAM.

    Returns ``(max_docno_suffix, processed_urls)`` where the next document
    should use docno ``DOC-{(max_suffix + 1):06d}`` (assuming sequential ids).
    """
    if not output_path.exists():
        return 0, set()

    max_suffix = 0
    processed_urls: set[str] = set()
    with output_path.open("r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            url = row.get("url")
            if isinstance(url, str):
                processed_urls.add(url)
            docno = row.get("docno")
            if isinstance(docno, str) and docno.startswith("DOC-"):
                try:
                    max_suffix = max(max_suffix, int(docno[4:], 10))
                except ValueError:
                    continue
    return max_suffix, processed_urls


def crawl_domain(
    start_url: str,
    max_docs: int,
    delay: float,
    output_path: Path | None = None,
    checkpoint_every: int = 100,
) -> int:
    """Breadth-first crawl of temple.edu pages and extract visible text.

    If ``output_path`` is provided, documents are streamed to disk during crawl.
    This makes long runs recoverable even if the process is interrupted.

    Scheduling uses two queues: **new** (URLs not yet in the corpus) is drained
    completely before **expand** (URLs already saved, fetched only to discover
    outbound links). That way resumed crawls chase unseen pages first instead
    of re-fetching thousands of known URLs while the progress bar stays flat.

    Returns the numeric suffix of the last assigned ``docno`` (collection size
    if ids are sequential without gaps).
    """
    # URLs we have not yet tried to fetch this session (deduped at pop via ``visited``).
    q_new: deque[str] = deque()
    # URLs already in ``processed_urls``: only fetched when ``q_new`` is empty.
    q_expand: deque[str] = deque()
    visited: set[str] = set()
    processed_urls: set[str] = set()
    next_doc_id = 0
    fetches = 0

    if output_path is not None:
        ensure_dir(output_path.parent)
        next_doc_id, processed_urls = scan_resume_state(output_path)
        if next_doc_id > 0:
            print(
                f"Resuming crawl: highest docno suffix {next_doc_id}, "
                f"{len(processed_urls)} URLs already collected → {output_path}",
                flush=True,
            )

    def schedule_outgoing(link: str) -> None:
        """Put an in-domain link on the appropriate queue if not visited yet."""
        if link in visited:
            return
        if not is_temple_url(link):
            return
        if link in processed_urls:
            q_expand.append(link)
        else:
            q_new.appendleft(link)

    if is_temple_url(start_url):
        if start_url in processed_urls:
            q_expand.append(start_url)
        else:
            q_new.append(start_url)

    with tqdm(total=max_docs, desc="Crawling temple.edu") as progress:
        progress.update(min(next_doc_id, max_docs))
        while (q_new or q_expand) and next_doc_id < max_docs:
            if q_new:
                url = q_new.popleft()
            else:
                url = q_expand.popleft()
            if url in visited:
                continue
            visited.add(url)

            if not is_temple_url(url):
                continue

            try:
                fetches += 1
                if fetches % 500 == 0:
                    progress.set_postfix(
                        fetched=fetches,
                        new_q=len(q_new),
                        expand_q=len(q_expand),
                    )

                response = requests.get(url, timeout=15)
                if response.status_code != 200:
                    continue
                if "text/html" not in response.headers.get("content-type", ""):
                    continue
                soup = BeautifulSoup(response.text, "html.parser")
                text = normalize_text(soup.get_text(separator=" ", strip=True))

                if url not in processed_urls:
                    if len(text) < 200:
                        continue
                    next_doc_id += 1
                    record = {
                        "docno": f"DOC-{next_doc_id:06d}",
                        "url": url,
                        "title": soup.title.get_text(strip=True) if soup.title else "",
                        "text": text,
                        "file_type": "html",
                    }
                    processed_urls.add(url)
                    if output_path is not None:
                        with output_path.open("a", encoding="utf-8") as file:
                            file.write(json.dumps(record, ensure_ascii=False) + "\n")
                        if next_doc_id % checkpoint_every == 0:
                            print(f"Checkpoint: {next_doc_id} docs saved to {output_path}", flush=True)
                    progress.update(1)
                # Pages already in the corpus: still follow links even if visible
                # text is short (hub menus), so we can reach new URLs.

                for link in extract_links(soup, url):
                    schedule_outgoing(link)

                time.sleep(delay)
            except requests.RequestException:
                continue

    return next_doc_id


def main() -> None:
    """Parse args, run crawl, and persist raw corpus JSONL."""
    parser = argparse.ArgumentParser(description="Crawl temple.edu for IR corpus.")
    parser.add_argument("--start-url", default="https://www.temple.edu")
    parser.add_argument("--max-docs", type=int, default=100000)
    parser.add_argument("--delay", type=float, default=0.1)
    parser.add_argument("--output", default="data/raw/corpus.jsonl")
    args = parser.parse_args()

    output_path = Path(args.output)
    ensure_dir(output_path.parent)

    count = crawl_domain(
        start_url=args.start_url,
        max_docs=args.max_docs,
        delay=args.delay,
        output_path=output_path,
        checkpoint_every=100,
    )
    if count == 0 and not output_path.exists():
        write_jsonl(output_path, [])
    print(f"Highest doc index / target: {count} / {args.max_docs} → {output_path}")


if __name__ == "__main__":
    main()
