#!/usr/bin/env python3
"""Fetch the exact released PMID set from NCBI without storing credentials."""

from __future__ import annotations

import argparse
import json
import os
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path


EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--email", default="")
    return parser.parse_args()


def read_pmids(path: Path) -> list[str]:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    pmids = [str(row["pmid"]) for row in rows]
    if len(pmids) != 2_000 or len(set(pmids)) != 2_000:
        raise ValueError("Manifest must contain 2,000 unique PMIDs")
    return pmids


def fetch_batch(pmids: list[str], email: str, api_key: str) -> bytes:
    params = {
        "db": "pubmed",
        "id": ",".join(pmids),
        "retmode": "xml",
        "rettype": "abstract",
        "tool": "numerical-distortion-study",
        "email": email,
    }
    if api_key:
        params["api_key"] = api_key
    request = urllib.request.Request(EUTILS, data=urllib.parse.urlencode(params).encode("ascii"))
    for attempt in range(4):
        try:
            with urllib.request.urlopen(request, timeout=90) as response:
                return response.read()
        except Exception:
            if attempt == 3:
                raise
            time.sleep(2 ** attempt)
    raise RuntimeError("Unreachable")


def parse_articles(payload: bytes) -> list[dict]:
    root = ET.fromstring(payload)
    records = []
    for article in root.findall(".//PubmedArticle"):
        pmid = article.findtext(".//PMID")
        title_element = article.find(".//ArticleTitle")
        abstract_elements = article.findall(".//AbstractText")
        if not pmid or title_element is None or not abstract_elements:
            continue
        title = "".join(title_element.itertext()).strip()
        sections = []
        for element in abstract_elements:
            text = "".join(element.itertext()).strip()
            label = element.get("Label")
            sections.append(f"{label}: {text}" if label else text)
        records.append({"pmid": pmid, "title": title, "abstract": " ".join(sections)})
    return records


def main() -> None:
    args = parse_args()
    if args.output.exists():
        raise FileExistsError(f"Refusing to overwrite: {args.output}")
    pmids = read_pmids(args.manifest)
    api_key = os.environ.get("NCBI_API_KEY", "")
    delay = 0.11 if api_key else 0.34
    records = []
    for start in range(0, len(pmids), 100):
        records.extend(parse_articles(fetch_batch(pmids[start:start + 100], args.email, api_key)))
        time.sleep(delay)
    by_pmid = {record["pmid"]: record for record in records}
    missing = [pmid for pmid in pmids if pmid not in by_pmid]
    if missing:
        raise RuntimeError(f"NCBI returned no abstract for {len(missing)} PMIDs; first={missing[:5]}")
    with args.output.open("w", encoding="utf-8") as handle:
        for pmid in pmids:
            handle.write(json.dumps(by_pmid[pmid], ensure_ascii=False, separators=(",", ":")) + "\n")
    print(f"Wrote {len(pmids)} records to {args.output}")


if __name__ == "__main__":
    main()

